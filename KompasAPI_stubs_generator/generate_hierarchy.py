"""
Формирует и генерирует файл python-кода с информацией об иерархии классов
КомпасAPI в виде словаря.

В словаре в ключах (`str`) указаны исходные классы,
в значениях (`list[str]`) - их прямые классы-родители.
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

from .utils import utils


from . import parse_topics
from . import parse_module

from . import classes
from .classes import HelpPageType, Topic, TOCEntry, \
    PythonEntry, PythonClass, PythonFunction, PythonVariable, PythonProperty
from .classes import CLASS_NAME_IDISPATCH


from .utils.utils import PYTHON_TAB


HIERARCHY_VARIABLE_NAME = "KompasAPIclassesHierarchy"
HIERARCHY_VARIABLE_TYPE: typing.TypeAlias = dict[str, list[str]]
HIERARCHY_DOCSTRING = utils.render_docstring("""
Указывает информацию о **прямых** родителях для каждого класса интерфейса КомпасAPI:
```
{
    "derived_class_name": ["base_class1_name", "base_class2_name", ...],
    ...
}
```

Как правило, в Компас API для каждого класса не более одного прямого родителя.
""") + "\n"

HIERARCHY_MODULE_DOC = utils.render_docstring("""
Информация о наследовании классов интерфейсов Компас API друг от друга.
""", True)

CLASS_NAME_IDISPATCH_VARIABLE_NAME = "CLASS_NAME_IDISPATCH"



def generate_hierarchy(interfaces: typing.Iterable[PythonClass]) -> str:
    content: str = ""

    logger.info(f"Генерация иерархии (перечня прямых родителей)...")

    name_max_width: int = 0
    value_max_width: int = 0

    hierarchy_dict: dict[str, tuple[str, str]]
    """ Словарь: `{ class_name: ( base_classes, s_href ), ... }` """
    hierarchy_dict = {
        CLASS_NAME_IDISPATCH: ("[]", ""),
    }

    for py_entry in interfaces:
        if py_entry.name in hierarchy_dict:
            logger.warning(f"generate_hierarchy(): Предупреждение: пропуск, так как уже есть в KompasAPIclassesHierarchy: '{py_entry.name}'")
            continue

        logger.debug(f"generate_hierarchy(): Иерархия для '{py_entry.name}': {py_entry.base_classes}")

        base_classes: list[str] = py_entry.base_classes.copy()
        s_classes: str = repr(base_classes)
        s_href: str = utils.render_hrefs(py_entry.hrefs, True)

        hierarchy_dict[py_entry.name] = (s_classes, s_href)
        name_max_width = max(name_max_width, len(py_entry.name))
        value_max_width = max(value_max_width, len(s_classes))

    logger.info(f"Сформирована иерархия (перечень прямых родителей) для {len(hierarchy_dict)} классов.")

    name_max_width += 2  # +2, потому что кавычки
    value_max_width += 1  # +1, потому что запятая

    for name, value in hierarchy_dict.items():
        s_classes, s_href = value
        s_classes += ","
        content += f'{PYTHON_TAB}{repr(name).ljust(name_max_width)}: {s_classes.ljust(value_max_width)}{s_href}\n'

    content = f"{HIERARCHY_VARIABLE_NAME}: {str(HIERARCHY_VARIABLE_TYPE)}\n{HIERARCHY_DOCSTRING}\n{HIERARCHY_VARIABLE_NAME} = {{\n{content}}}\n"

    content = f"{CLASS_NAME_IDISPATCH_VARIABLE_NAME} = {repr(CLASS_NAME_IDISPATCH)}\n{utils.render_docstring('Имя класса, базового для всех классов интерфейсов Компас API.')}\n\n\n{content}"

    return content


def generate_and_write_hierarchy(
        py_entries: list[PythonEntry],
        KompasAPIclassesHierarchy_file: str,
        ) -> None:

    interfaces: list[PythonClass] = list(filter(
        lambda e: isinstance(e, PythonClass),
        py_entries,
    ))  # type: ignore
    logger.info(f"Загружено {len(interfaces)} классов интерфейсов.")

    content: str = generate_hierarchy(interfaces)

    size = utils.write_python_module(KompasAPIclassesHierarchy_file, content, HIERARCHY_MODULE_DOC)
    logger.info(f"Иерархия классов записана в '{KompasAPIclassesHierarchy_file}' ({size} bytes).")


def load_hierarchy_python(
        KompasAPIclassesHierarchy_file: str,
        ) -> HIERARCHY_VARIABLE_TYPE:
    KompasAPIclassesHierarchy: HIERARCHY_VARIABLE_TYPE = getattr(
        utils.import_python_module_by_filepath(KompasAPIclassesHierarchy_file),
        HIERARCHY_VARIABLE_NAME,
    )
    logger.info(f"Загружена иерархия для {len(KompasAPIclassesHierarchy)} классов КомпасAPI из файла '{KompasAPIclassesHierarchy_file}'.")
    return KompasAPIclassesHierarchy


def main(
        do_k5: bool = True,
        do_k7: bool = True,
        ) -> None:
    # topics: list[Topic] = []
    # topics.extend(parse_topics.load_topics(const.get_topics_filepath()))

    py_entries: list[PythonEntry] = []

    if do_k5:
        py_entries.extend(parse_module.load_pylib(const.get_pylib_K6API5_filepath_updated()))
    if do_k7:
        py_entries.extend(parse_module.load_pylib(const.get_pylib_KAPI7_filepath_updated()))

    generate_and_write_hierarchy(py_entries, const.get_KompasAPIclassesHierarchy_file())





if __name__ == "__main__":

    main()
