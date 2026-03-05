"""

"""
import typing

import traceback
import os
import sys
import json

import re

from . import const


from .utils import json_utils
from .utils import utils

from . import classes
from .classes import HelpPageType, Topic, TOCEntry, \
    PythonEntry, PythonClass, PythonFunction, PythonVariable, PythonProperty
from .classes import CLASS_NAME_IDispatch

from . import parse_module
from . import parse_topics



KNOWN_TYPES_NAMES: list[str] = [c.__name__ for c in parse_module.KNOWN_TYPES]



def update_property_or_method(
        py_entry: PythonEntry,
        topic: Topic,
        ) -> None:
    py_entry.doc = topic.docstring
    py_entry.href = utils.ensure_ext(topic.own_href, ".html")
    if isinstance(py_entry, PythonFunction):  # метод
        pass

    elif isinstance(py_entry, PythonProperty):  # свойство
        pass

    else:
        print(f"update_property_or_method(): Ошибка: неожиданный тип py_entry ({type(py_entry)}) для {topic}", file=sys.stderr)


def update_class(
        py_entry: PythonClass,
        topic: Topic,
        entries_to_remove: typing.Container[str],
        ) -> None:
    py_entry.doc = topic.docstring
    py_entry.href = utils.ensure_ext(topic.own_href, ".html")

    has_dispatch = CLASS_NAME_IDispatch in py_entry.base_classes
    py_entry.base_classes = topic.hierarchy[0].copy()
    if len(py_entry.base_classes) == 0 and has_dispatch:
        py_entry.base_classes.append(CLASS_NAME_IDispatch)

    # TODO удалить свойства, которые уже были объявлены в base_classes
    i = 0
    while i < len(py_entry.children):
        e: PythonEntry = py_entry.children[i]
        if e.name in entries_to_remove:
            py_entry.children.pop(i)
            continue
        i += 1



def update_pylibs_from_topics(
        pylib_raw_filepath: str,
        pylib_updated_filepath: str,
        jstopics: list[Topic],
        ) -> None:
    contents: list[PythonEntry] = parse_module.load_pylib(pylib_raw_filepath)
    pylib_entries: dict[str, PythonEntry] = parse_module.get_entries(contents)

    class_entry_topics = classes.filter_by_type(jstopics, HelpPageType.PropertyOrMethod)
    interface_topics = classes.filter_by_type(jstopics, HelpPageType.Interface)
    enum_topics = classes.filter_by_type(jstopics, HelpPageType.Enum)

    print(f"Количество объектов class_entry_topics: {len(class_entry_topics)}")
    print(f"Количество объектов   interface_topics: {len(interface_topics)}")
    print(f"Количество объектов        enum_topics: {len(enum_topics)}")


    ### получение перечней свойств и методов, которые принадлежат родительским классам

    print(f"Получение перечней свойств/методов в родительских классах...")
    classes_children: dict[str, list[str]] = {
        CLASS_NAME_IDispatch: [],
    }
    for name, py_class in pylib_entries.items():
        if isinstance(py_class, PythonClass):
            classes_children[name] = [e.name for e in py_class.children]

    print(f"Получены перечни свойств и методов для {len(classes_children)} классов.")

    class_names: set[str] = set(classes_children.keys())  # для обновления возвращаемых значений методов и свойств
    enum_names: set[str] = set(enum_topics.keys())  # для обновления возвращаемых значений методов и свойств

    ### обновление class_entries (свойства/методы)
    # Сначала нужно обновить class_entries (свойства/методы),
    # чтобы потом при обновлении классов можно было удалить те class_entries,
    # которые уже объявлены в base_classes

    print(f"Обновление свойств/методов...")
    count: int = 0

    for name, topic in class_entry_topics.items():
        print(f"{name} для '{topic.own_name}'")
        if not name in pylib_entries:
            print(f"update_pylibs_from_topics(): Предупреждение: не найдено имя среди pylib_entries: '{name}' у {topic}", file=sys.stderr)
            continue

        py_entry: PythonEntry = pylib_entries[name]

        update_property_or_method(py_entry, topic)


        ### определение типа возвращаемого значения метода или типа свойства

        if "return" in topic.value_types and topic.value_types["return"] != "":
            return_type: str = ""

            def _filter_return_types(return_types: typing.Iterable[str]):
                filtered_types: list[str] = []

                for return_type in return_types:
                    return_type_to_search = return_type.lower() if classes.DO_USE_LOWERCASE_NAMES else return_type

                    if return_type_to_search in KNOWN_TYPES_NAMES:
                        filtered_types.append(return_type)
                        continue

                    if return_type_to_search in class_names:
                        filtered_types.append(return_type)
                        continue
                        # py_entry = pylib_entries.get(return_type_to_search, None)
                        # if py_entry is not None:  # такая конструкция нужна для того, чтобы название типа происходило из pylib, а не из topics. Проблема в IMultiLine (вместо )

                    if return_type_to_search in enum_names:
                        filtered_types.append("int")
                        continue

                    if return_type_to_search == parse_topics.ANY_TYPE_NAME:
                        filtered_types.append("typing.Any")
                        continue

                    if return_type_to_search.startswith("list[") and return_type_to_search.endswith("]"):
                        filtered_types.append(return_type)
                        continue

                    # попытка исправления типа возврата путем дописывания 'I'

                    return_type_to_add = "I" + return_type
                    return_type_to_search = return_type_to_add.lower() if classes.DO_USE_LOWERCASE_NAMES else return_type_to_add

                    if return_type_to_search in class_names:
                        filtered_types.append(return_type_to_add)
                        print(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue

                    # попытка исправления типа возврата путем дописывания 'ks'

                    return_type_to_add = "ks" + return_type
                    return_type_to_search = return_type_to_add.lower() if classes.DO_USE_LOWERCASE_NAMES else return_type_to_add

                    if return_type_to_search in class_names:
                        filtered_types.append(return_type_to_add)
                        print(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue
                    if return_type_to_search in enum_names:
                        return_type_to_add = "int"
                        filtered_types.append(return_type_to_add)
                        print(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue

                    print(f"_filter_return_types(): Предупреждение: сомнительный тип возврата: {repr(return_type)} среди {return_types} у {topic}", file=sys.stderr)
                return filtered_types
            return_type = "|".join(_filter_return_types(topic.value_types["return"].split("|")))

            if return_type != "":
                print(f"\tвозвращаемое значение: {return_type}")
                if isinstance(py_entry, PythonFunction):
                    py_entry.return_type = return_type
                if isinstance(py_entry, PythonVariable):
                    py_entry.value_type = return_type

        count += 1

    print(f"Обновлены {count} свойств/методов.")


    ### обновление interfaces

    print(f"Обновление классов...")
    count: int = 0

    for name, topic in interface_topics.items():
        print(f"{name} для '{topic.own_name}'")
        if not name in pylib_entries:
            print(f"update_pylibs_from_topics(): Ошибка: не найдено имя среди pylib_entries: '{name}' у {topic}", file=sys.stderr)
            continue

        py_class = pylib_entries[name]
        if not isinstance(py_class, PythonClass):
            print(f"update_pylibs_from_topics(): Ошибка: объект '{name}' не является объектом класса PythonClass у {topic}", file=sys.stderr)
            continue

        entries_to_remove: set[str] = set()
        for cls_name in topic.hierarchy[0]:
            cls_name = classes.get_py_entry_full_name(cls_name, None)
            if not cls_name in classes_children:
                print(f"update_pylibs_from_topics(): Ошибка: не найдено имя среди classes_children '{cls_name}' у класса '{name}' у {topic}", file=sys.stderr)
                continue
            entries_to_remove.update(classes_children[cls_name])

        update_class(py_class, topic, entries_to_remove)
        count += 1

    print(f"Обновлены {count} классов.")

    ### обновление enums




    ### запись

    parse_module.write_pylib_update(pylib_updated_filepath, contents)


    ### проверка (сообщение об) py_entries без документации

    # undocumented_entries: list[PythonEntry] = []

    for name, py_entry in pylib_entries.items():
        if py_entry.doc == "":
            print(f"update_pylibs_from_topics(): Предупреждение: Объект py_entry без документации: {repr(name)} для {repr(py_entry.name)}, href='{py_entry.href}'", file=sys.stderr)


def main(
        do_k5: bool = True,
        do_k7: bool = True,
        ) -> None:
    jstopics: list[Topic] = []
    jstopics.extend(parse_topics.load_topics(const.topics_filepath))

    if do_k7:
        update_pylibs_from_topics(const.pylib_KAPI7_filepath_raw, const.pylib_KAPI7_filepath_updated, jstopics)

    if do_k5:
        update_pylibs_from_topics(const.pylib_K6API5_filepath_raw, const.pylib_K6API5_filepath_updated, jstopics)




if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"""\
Usage:
    {sys.argv[0]} what_to_do

what_to_do:
    1  - KompasAPI 5
    2  - KompasAPI 7
    3 - both
""")
        sys.exit(1)

    what_to_do = int(sys.argv[1])
    do_k5 = bool(what_to_do & 0b0001)
    do_k7 = bool(what_to_do & 0b0010)

    ### main

    main(do_k5, do_k7)

