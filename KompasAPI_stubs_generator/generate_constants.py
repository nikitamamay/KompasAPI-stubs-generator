

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
from .utils import statistics

from . import parse_topics
from . import classes
from .classes import HelpPageType, Topic
from .classes import ENUM_UNNAMED

from .utils.utils import indent, render_docstring


CONSTANTS_MODULE_DOC = utils.render_docstring("""
Константы и перечисления (enums) Компас API.
""", True)


def render_enum(topic: Topic) -> str:
    output: str = ""

    max_name_width: int = max([
        len(enum_member[0])
        for enum_member in topic.enum_members])

    for enum_member in topic.enum_members:
        name, value, member_docstring = enum_member
        s_doc = render_docstring(member_docstring) + "\n" if member_docstring != "" else ""
        output += f"{name.ljust(max_name_width)} = {value}\n{s_doc}"

    s_href = utils.render_hrefs(topic.own_hrefs, True)

    if topic.own_name != ENUM_UNNAMED:
        s_doc = render_docstring(topic.docstring) + "\n" if topic.docstring != "" else ""
        output = f"class {topic.own_name}:{s_href}\n{indent(s_doc)}{indent(output)}\n"
    else:
        output = f"{s_href.lstrip()}\n{output}\n"

    return output


def generate_and_write_constants(jstopics: list[Topic], filepath: str) -> None:
    enum_topics = list(filter(lambda topic: topic.page_type == HelpPageType.Enum, jstopics))

    logger.info(f"Генерации подлежат {len(enum_topics)} перечислений и групп констант.")
    output: str = ""

    for topic in enum_topics:
        logger.debug(f"generate_constants(): Рендеринг перечисления {topic}")
        output += render_enum(topic) + "\n"

    size = utils.write_python_module(filepath, output, CONSTANTS_MODULE_DOC)
    logger.info(f"Константы и перечисления записаны в '{filepath}' ({statistics.render_file_size(size)}).")


def main():
    jstopics: list[Topic] = []
    jstopics.extend(parse_topics.load_topics(const.get_topics_filepath()))

    generate_and_write_constants(jstopics, const.get_KompasAPIconstants_file())




if __name__ == "__main__":

    main()
