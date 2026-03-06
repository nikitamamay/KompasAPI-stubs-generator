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
from . import classes
from .classes import HelpPageType, Topic
from .classes import CLASS_NAME_IDispatch


from .utils.utils import PYTHON_TAB



def generate_hierarchy(interfaces: typing.Iterable[Topic]) -> dict[str, list[str]]:
    KompasAPIclassesHierarchy: dict[str, list[str]] = {
        CLASS_NAME_IDispatch: [],
    }
    logger.info(f"Генерация иерархии (перечня прямых родителей)...")

    for topic in interfaces:
        cn: str = topic.own_name
        logger.debug(f"{cn}")

        if cn == "":
            logger.error(f"generate_hierarchy(): Ошибка: Пустое own_name у {topic}")
            continue

        if cn in KompasAPIclassesHierarchy:
            logger.warning(f"generate_hierarchy(): Предупреждение: пропуск, так как уже есть в KompasAPIclassesHierarchy, для '{cn}'")
            continue

        # assert len(topic.hierarchy) > 1, f"Ошибка: Пустая иерархия у {topic}: {repr(topic.hierarchy)}"
        base_classes: list[str] = topic.hierarchy[0]

        KompasAPIclassesHierarchy[cn] = base_classes.copy()

    logger.info(f"Сформирована иерархия (перечень прямых родителей) для {len(KompasAPIclassesHierarchy)} классов.")
    return KompasAPIclassesHierarchy


def write_hierarchy(filepath: str, KompasAPIclassesHierarchy: dict[str, list[str]]) -> None:
    content: str = ""
    content += f"KompasAPIclassesHierarchy: dict[str, list[str]] = {{\n"

    max_width: int = max(map(len, KompasAPIclassesHierarchy.keys())) + 2  # +2, потому что кавычки

    for key, value in KompasAPIclassesHierarchy.items():
        content += f'{PYTHON_TAB}{repr(key).ljust(max_width)}: {repr(value)},\n'

    content += f"}}\n"

    size = utils.write_python_module(filepath, content)

    logger.info(f"Иерархия классов записана в '{filepath}' ({size} bytes).")


def generate_and_write_hierarchy(
        jstopics: list[Topic],
        KompasAPIclassesHierarchy_file: str,
        ) -> None:

    interfaces: list[Topic] = list(classes.filter_by_type(jstopics, HelpPageType.Interface).values())
    logger.info(f"Загружено {len(interfaces)} классов интерфейсов.")

    KompasAPIclassesHierarchy = generate_hierarchy(interfaces)
    write_hierarchy(KompasAPIclassesHierarchy_file, KompasAPIclassesHierarchy)


def load_hierarchy_python(
        KompasAPIclassesHierarchy_file: str,
        ) -> dict[str,list[str]]:
    KompasAPIclassesHierarchy: dict[str,list[str]] = utils.import_python_module_by_filepath(
        KompasAPIclassesHierarchy_file
        ).KompasAPIclassesHierarchy
    logger.info(f"Загружена иерархия для {len(KompasAPIclassesHierarchy)} классов КомпасAPI из файла '{KompasAPIclassesHierarchy_file}'.")
    return KompasAPIclassesHierarchy


def main(
        # do_k5: bool = True,
        # do_k7: bool = True,
        ) -> None:
    topics: list[Topic] = []
    topics.extend(parse_topics.load_topics(const.get_topics_filepath()))

    generate_and_write_hierarchy(topics, const.get_KompasAPIclassesHierarchy_file())





if __name__ == "__main__":

    main()
