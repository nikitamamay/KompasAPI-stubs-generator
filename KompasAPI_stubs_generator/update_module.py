"""

"""

from . import logging_system
logger = logging_system.get_logger(__name__)

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
from .classes import CLASS_NAME_IDISPATCH

from . import parse_module
from . import parse_topics



KNOWN_TYPES_NAMES: list[str] = [c.__name__ for c in parse_module.KNOWN_TYPES] + ["None"]


def update_python_entry(
        py_entry: PythonEntry,
        topic: Topic,
        ) -> None:
    py_entry.doc = topic.docstring
    py_entry.hrefs = topic.own_hrefs.copy()


def update_property_or_method(
        py_entry: PythonEntry,
        topic: Topic,
        ) -> None:
    update_python_entry(py_entry, topic)
    if isinstance(py_entry, PythonFunction):  # метод
        pass

    elif isinstance(py_entry, PythonProperty):  # свойство
        pass

    else:
        logger.error(f"update_property_or_method(): Ошибка: неожиданный тип py_entry ({type(py_entry)}) для {topic}")


def update_class(
        py_entry: PythonClass,
        topic: Topic,
        entries_to_remove: typing.Container[str],
        ) -> None:
    update_python_entry(py_entry, topic)

    # обновление иерархии (родительского класса):
    # если иерархия в topic пустая, то остается то, что было получено в parse_module()
    if len(topic.hierarchy[0]) > 0:
        py_entry.base_classes = topic.hierarchy[0].copy()

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

    class_entry_topics = classes.filter_by_type_as_dict(jstopics, HelpPageType.PropertyOrMethod)
    interface_topics = classes.filter_by_type_as_dict(jstopics, HelpPageType.Interface)
    enum_topics = classes.filter_by_type_as_dict(jstopics, HelpPageType.Enum)

    logger.info(f"Количество объектов class_entry_topics: {len(class_entry_topics)}")
    logger.info(f"Количество объектов   interface_topics: {len(interface_topics)}")
    logger.info(f"Количество объектов        enum_topics: {len(enum_topics)}")


    ### получение перечней свойств и методов, которые принадлежат родительским классам

    logger.info(f"Получение перечней свойств/методов в родительских классах...")
    classes_children: dict[str, list[str]] = {
        classes.get_py_entry_full_name(CLASS_NAME_IDISPATCH, None): [],
    }
    for name, py_class in pylib_entries.items():
        if isinstance(py_class, PythonClass):
            classes_children[name] = [e.name for e in py_class.children]

    logger.info(f"Получены перечни свойств и методов для {len(classes_children)} классов.")

    class_names: set[str] = set(classes_children.keys())  # для обновления возвращаемых значений методов и свойств
    enum_names: set[str] = set(enum_topics.keys())  # для обновления возвращаемых значений методов и свойств

    ### обновление class_entries (свойства/методы)
    # Сначала нужно обновить class_entries (свойства/методы),
    # чтобы потом при обновлении классов можно было удалить те class_entries,
    # которые уже объявлены в base_classes

    logger.info(f"Обновление свойств/методов...")
    count: int = 0

    for name, topic in class_entry_topics.items():
        py_entry: PythonEntry|None = pylib_entries.get(name, None)
        if py_entry is None:
            # # не надо писать, потому что среди topics есть PythonEntries вообще всего подряд (и KAPI5, и KAPI7, и constants)
            # logger.warning(f"update_pylibs_from_topics(): Предупреждение: не найдено имя среди pylib_entries: '{name}' у {topic}")
            continue

        logger.debug(f"update_pylibs_from_topics(): Обновление свойства/метода '{name}', topic={topic}")

        update_property_or_method(py_entry, topic)

        ### определение типа возвращаемого значения метода или типа свойства

        if "return" in topic.value_types and topic.value_types["return"] != "":
            return_type: str = ""

            def _filter_return_types(return_types: typing.Iterable[str]):
                filtered_types: list[str] = []
                any_type_name = parse_topics.ANY_TYPE_NAME.lower() if classes.DO_USE_LOWERCASE_NAMES else parse_topics.ANY_TYPE_NAME

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

                    if return_type_to_search == any_type_name:
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
                        logger.debug(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue

                    # попытка исправления типа возврата путем дописывания 'ks'

                    return_type_to_add = "ks" + return_type
                    return_type_to_search = return_type_to_add.lower() if classes.DO_USE_LOWERCASE_NAMES else return_type_to_add

                    if return_type_to_search in class_names:
                        filtered_types.append(return_type_to_add)
                        logger.debug(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue
                    if return_type_to_search in enum_names:
                        return_type_to_add = "int"
                        filtered_types.append(return_type_to_add)
                        logger.debug(f"_filter_return_types(): тип возврата исправлен на {repr(return_type_to_add)} из {repr(return_type)} среди {return_types} у {topic}")
                        continue

                    logger.warning(f"_filter_return_types(): Предупреждение: сомнительный тип возврата: {repr(return_type)} среди {return_types} у {topic}")
                return filtered_types
            return_type = "|".join(_filter_return_types(topic.value_types["return"].split("|")))

            if return_type != "":
                logger.debug(f"update_pylibs_from_topics(): возвращаемое значение: '{return_type}' у '{name}'")
                if isinstance(py_entry, PythonFunction):
                    py_entry.return_type = return_type
                if isinstance(py_entry, PythonVariable):
                    py_entry.value_type = return_type

        count += 1

    logger.info(f"Обновлены {count} свойств/методов.")


    ### обновление interfaces

    logger.info(f"Обновление классов...")
    count: int = 0

    for name, topic in interface_topics.items():
        logger.debug(f"update_pylibs_from_topics(): Обновление класса '{name}' для '{topic.own_name}'")
        if not name in pylib_entries:
            # # не надо писать, потому что среди topics есть PythonEntries вообще всего подряд (и KAPI5, и KAPI7, и constants)
            # logger.error(f"update_pylibs_from_topics(): Ошибка: не найдено имя среди pylib_entries: '{name}' у {topic}")
            continue

        py_class = pylib_entries[name]
        if not isinstance(py_class, PythonClass):
            logger.error(f"update_pylibs_from_topics(): Ошибка: объект '{name}' не является объектом класса PythonClass")
            continue

        # формирование перечня методов/свойств, которые уже есть в родительских классах - на удаление в текущем классе
        entries_to_remove: set[str] = set()
        for cls_name in topic.hierarchy[0]:
            cls_name = classes.get_py_entry_full_name(cls_name, None)
            if not cls_name in classes_children:
                logger.error(f"update_pylibs_from_topics(): Ошибка: не найдено имя среди classes_children '{cls_name}' у класса '{name}' у {topic}")
                continue
            entries_to_remove.update(classes_children[cls_name])

        update_class(py_class, topic, entries_to_remove)
        count += 1

    logger.info(f"Обновлены {count} классов.")

    ### запись

    parse_module.write_pylib_update(pylib_updated_filepath, contents)


    ### вывод перечня py_entries без документации

    # список формируется заново, так как выше были удалены entries (методы/свойства, принадлежащие родительским классам) у классов
    pylib_entries: dict[str, PythonEntry] = parse_module.get_entries(contents)

    undocumented_count: int = 0
    for name, py_entry in pylib_entries.items():
        if py_entry.doc == "":
            logger.warning(f"update_pylibs_from_topics(): Предупреждение: Объект py_entry без документации: {repr(name)} для {repr(py_entry.name)}, href='{py_entry.hrefs}'")
            undocumented_count += 1
    logger.info(f"Количество объектов py_entry без документации: {undocumented_count}")



def main(
        do_k5: bool = True,
        do_k7: bool = True,
        ) -> None:
    jstopics: list[Topic] = []
    jstopics.extend(parse_topics.load_topics(const.get_topics_filepath()))

    if do_k7:
        update_pylibs_from_topics(const.get_pylib_KAPI7_filepath_raw(), const.get_pylib_KAPI7_filepath_updated(), jstopics)

    if do_k5:
        update_pylibs_from_topics(const.get_pylib_K6API5_filepath_raw(), const.get_pylib_K6API5_filepath_updated(), jstopics)




if __name__ == "__main__":

#     if len(sys.argv) < 2:
#         print(f"""\
# Usage:
#     {sys.argv[0]} what_to_do

# what_to_do:
#     1  - KompasAPI 5
#     2  - KompasAPI 7
#     3 - both
# """)
#         sys.exit(1)

#     what_to_do = int(sys.argv[1])
#     do_k5 = bool(what_to_do & 0b0001)
#     do_k7 = bool(what_to_do & 0b0010)

#     ### main

#     main(do_k5, do_k7)

    main()

