"""
Выполняет парсинг python-модуля КомпасAPI (`KompasAPI7.py` и `Kompas6API5.py`).

Именно эти python-модули, а не страницы Справки SDK Компас, являются
первоисточниками для будущих stub-файлов. Использование модулей позволяет:

* уточнить понятия свойств и методов: дело в том, что в Справке SDK Компас
    свойствами называется нечто таинственное, что может быть неотличимо
    от методов. В рамках этого проекта подразумеваются следующие определения:
    * свойства - это те, доступ к которым выполняется через точку без круглых скобок,
        типа `obj.property`.
        Они объявлены в полях классов `_prop_map_get_` и `_prop_map_put_`.
    * методы - это те, которые вызываются оператором круглых скобок,
        типа `obj.method()`;

* получить действительный перечень классов, их свойств и методов.
    Полагаться в данном случае на Справку тоже нельзя, вот почему:
    * имеют место быть несовпадения наименований, например, "IMultiLine" (заглавная L)
        в Справке вместо "IMultiline" в python-модулях;
    * некоторые методы/свойства есть в Справке, а в модулях нет; может быть и наоборот;
    * скрипт, проводящий парсинг Справки, может не обнаружить соответствия тому,
        что есть в python-модулях, поэтому класс/метод/свойство будет объявленным,
        но останется без строки документации `__doc__`.

"""

import typing

import traceback
import os
import sys
import json

import re

import types

from .utils import utils
from .utils import json_utils

from . import classes
from .classes import PythonEntry, PythonClass, PythonFunction, PythonVariable, PythonProperty
from .classes import CLASS_NAME_IDispatch

from . import const

from . import kompas_api_modules


import pythoncom
PYTHONCOM_MISSING = pythoncom.Missing
PYTHONCOM_EMPTY = pythoncom.Empty


LITERAL_TYPES = (int, float, str, bool, types.NoneType)
""" Простые типы, объекты которых вставляются в текст pyi-файла функцией `repr()` """

KNOWN_TYPES = LITERAL_TYPES + (dict, list)
""" Известные простые типы (помимо `LITERAL_TYPES`) """



def is_module_key_ignored(key: str) -> bool:
    # if key.startswith("_"):  # Нельзя игнорировать. Например, есть класс `_Nurbs`
    #     pass

    if key.startswith("__"):
        return True

    if "_vtables_" in key:
        return True

    if key in (
            "makepy_version",
            "python_version",
            "win32com",
            "pywintypes",
            "Dispatch",
            "CLSID",
            "pythoncom",
            "IID",
            "DispatchBaseClass",
            "CoClassBaseClass",
            "defaultNamedOptArg",
            "defaultNamedNotOptArg",
            "defaultUnnamedArg",
        ):
        return True

    return False


def is_class_key_ignored(key: str) -> bool:
    if key.startswith("_"):
        return True

    if key.startswith("__"):
        return True

    if key in ("_prop_map_get_", "_prop_map_put_", "_public_methods_", "_dispid_to_func_"):
        return True

    if key in ("CLSID", "coclass_clsid", "CLSID_Sink"):
        return True

    return False


def parse_general(key: str, value: typing.Any, is_class_entry: bool = False) -> PythonEntry:
    value_type = type(value)

    if value_type == type:
        return parse_class(value)

    elif value_type == types.FunctionType:
        return repr_function(value, is_class_entry)

    elif value_type in KNOWN_TYPES:
        return repr_simple_value(key, value, is_class_entry)

    return repr_simple_value(key, value, is_class_entry)


def repr_simple_value(key: str, value: typing.Any, is_class_entry: bool = False) -> PythonVariable:
    py_var = PythonVariable()
    py_var.name = key
    if value is None:
        py_var.value_type = ""
        py_var.value = "None"
    else:
        s_type = type(value).__name__
        py_var.value_type = s_type
        if type(value) in LITERAL_TYPES:
            py_var.value = repr(value)
    return py_var


def repr_function(func: types.FunctionType, is_class_entry: bool = False):
    py_func = PythonFunction()
    py_func.name = func.__name__

    params = func.__code__.co_varnames[:func.__code__.co_argcount]

    defaults = list(func.__defaults__) if func.__defaults__ is not None else []
    if len(params) > 0 and params[0] in ("self", "Self"):
        defaults.insert(0, PYTHONCOM_EMPTY)

    for i, param in enumerate(params):
        if i < len(defaults):
            if defaults[i] == PYTHONCOM_MISSING:  # аргумент не требуется
                continue

        py_func.parameters.append(param)

    return py_func


def parse_class(cls_: type) -> PythonClass:
    py_class = PythonClass()
    py_class.name = cls_.__name__

    if cls_.__base__ is not None and cls_.__base__.__name__ == "DispatchBaseClass":
        py_class.base_classes.append(CLASS_NAME_IDispatch)

    cls_vars = vars(cls_)
    properties: dict[str, PythonProperty] = {}

    if "_prop_map_get_" in cls_vars:
        for prop_name in cls_vars["_prop_map_get_"].keys():
            if not prop_name in properties:
                properties[prop_name] = PythonProperty()
                properties[prop_name].name = prop_name
            properties[prop_name].has_getter = True

    if "_prop_map_put_" in cls_vars:
        for prop_name in cls_vars["_prop_map_put_"].keys():
            if not prop_name in properties:
                properties[prop_name] = PythonProperty()
                properties[prop_name].name = prop_name
            properties[prop_name].has_setter = True

    py_class.children.extend(properties.values())

    for key, value in cls_vars.items():
        if is_class_key_ignored(key):
            continue
        py_class.children.append(parse_general(key, value, is_class_entry=True))

    return py_class


def parse_module(module: types.ModuleType) -> list[PythonEntry]:
    module_objects = vars(module)
    print(f"Загружен модуль '{module.__name__}' ({len(module_objects)} объектов) из файла '{module.__file__}'")

    contents: list[PythonEntry] = []

    for key, value in module_objects.items():
        if is_module_key_ignored(key):
            continue

        if type(value) == type:
            if "CoClassBaseClass" in [c.__name__ for c in value.__bases__]:
                continue

        contents.append(parse_general(key, value))

    print(f"Извлечено {len(contents)} корневых объектов PythonEntry из модуля '{module.__file__}'")
    return contents


def get_entries(pylib_contents: list[PythonEntry]) -> dict[str, PythonEntry]:
    """
    Рекурсивно обходит `pylib_contents` (включая `PythonClass.children`)
    и формирует вспомогательный словарь `{ entry_name: entry, ... }`, где
    * `entry_name` - имя объекта PythonEntry с учетом его пространства имён
        (например, для свойств класса будет `IAxis3D.MathCurve`);
    * `entry` - объект

    Примечание. Так как в Python объекты передаются по ссылкам, а не по значению,
    объекты `entry` - те же самые, что и в исходном объекте `pylib_contents`.

    То есть функция предназначена для того, чтобы присвоить альтернативные имена
    рекурсивно вложенным объекты (например, `PythonClass.children`). Эти имена -
    ключи словаря, который возвращает эта функция.

    (!) ВНИМАНИЕ (!) Ключи словаря формируются функцией `classes.get_py_entry_full_name()`
    и могут быть переведены в нижний регистр. Это делается специально, чтобы исключить
    несоответствие регистра символов строк между python-модулем (первоисточником)
    и страницами справки (где написано непонятно что --- особенно в разделе K6API5).
    """
    entries = {}
    for entry in pylib_contents:
        if entry.name == "":
            print(f"get_entries(): Ошибка: пустое имя у PythonEntry {repr(entry)}", file=sys.stderr)
            continue

        entries[classes.get_py_entry_full_name(entry, None)] = entry
        if isinstance(entry, PythonClass):
            for child_name, child in get_entries(entry.children).items():
                child_name = classes.get_py_entry_full_name(child_name, entry)
                entries[child_name] = child

    return entries



def write_pylib(pylib_filepath: str, contents: list[PythonEntry]) -> None:
    json_utils.save_json(pylib_filepath, contents)
    print(f"Сохранено в '{pylib_filepath}'")


def write_pylib_update(pylib_filepath: str, contents: list[PythonEntry]) -> None:
    json_utils.save_json(pylib_filepath, contents)
    print(f"Сохранено в '{pylib_filepath}'")


def load_pylib(pylib_filepath: str) -> list[PythonEntry]:
    l = json_utils.load_json_with_classes(pylib_filepath, [
        PythonEntry, PythonClass, PythonFunction, PythonVariable, PythonProperty,
    ])
    print(f"Загружено {len(l)} объектов PythonEntry из файла '{pylib_filepath}'")
    return l


def main(
        do_k5: bool = True,
        do_k7: bool = True,
        ) -> None:
    if do_k5:
        contents = parse_module(kompas_api_modules.Kompas6API5)
        write_pylib(const.pylib_K6API5_filepath_raw, contents)

    if do_k7:
        contents = parse_module(kompas_api_modules.KompasAPI7)
        write_pylib(const.pylib_KAPI7_filepath_raw, contents)



if __name__ == "__main__":

    # def _my_repr(obj):
    #     for name in dir(obj):
    #         if name != "__builtins__":
    #             print(f"{repr(name)}:\t{repr(getattr(obj, name))}")

    # def _test_function(a1, a2: str, *args, is_ok: bool = True, is_kw1 = None, **kwargs) -> str:
    #     """
    #     Use `dir()`, `getattr()`. Don't use `vars()`, since it doesn't work.
    #     """
    #     number = 40 + 2
    #     hello = f"my name is {number}"
    #     return "something"

    # _my_repr(_test_function)
    # print()
    # _my_repr(_test_function.__code__)


    if len(sys.argv) < 2:
        print(f"""\
Usage:
    {sys.argv[0]} what_to_do

what_to_do:
    1 - KompasAPI 5
    2 - KompasAPI 7
    3 - both
""")
        sys.exit(1)

    what_to_do = int(sys.argv[1])
    do_k5 = bool(what_to_do & 0b0001)
    do_k7 = bool(what_to_do & 0b0010)

    ### main

    main(do_k5, do_k7)


