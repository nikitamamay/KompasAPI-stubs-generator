


import typing

import traceback
import os
import sys
import json

import re

from . import const

from .utils import utils
from .utils import json_utils

from . import parse_topics
from . import classes
from .classes import HelpPageType, Topic
from .classes import ENUM_UNNAMED

from .utils.utils import indent, render_docstring


def render_enum(topic: Topic) -> str:
    output: str = ""

    max_name_width: int = max([
        len(enum_member[0])
        for enum_member in topic.enum_members])

    for enum_member in topic.enum_members:
        name, value, member_docstring = enum_member
        s_doc = render_docstring(member_docstring) + "\n" if member_docstring != "" else ""
        output += f"{name.ljust(max_name_width)} = {value}\n{s_doc}"

    s_href = f"  # {utils.ensure_ext(topic.own_href, '.html')}" if topic.own_href != "" else ""

    if topic.own_name != ENUM_UNNAMED:
        s_doc = render_docstring(topic.docstring) + "\n" if topic.docstring != "" else ""
        output = f"class {topic.own_name}:{s_href}\n{indent(s_doc)}{indent(output)}\n"
    else:
        output = f"{s_href.lstrip()}\n{output}\n"

    return output


def generate_constants(jstopics: list[Topic]) -> str:
    enum_topics = list(filter(lambda topic: topic.page_type == HelpPageType.Enum, jstopics))

    print(f"Генерации подлежат {len(enum_topics)} перечислений и групп констант.")
    output: str = ""

    for topic in enum_topics:
        print(f"{topic}")
        output += render_enum(topic)

    return output


def write_constants(filepath: str, content: str) -> None:
    size = utils.write_python_module(filepath, content)
    print(f"Константы и перечисления записаны в '{filepath}' ({size} bytes).")


def main():
    jstopics: list[Topic] = []
    jstopics.extend(parse_topics.load_topics(const.topics_filepath))

    content = generate_constants(jstopics)
    write_constants(const.KompasAPIconstants_file, content)




if __name__ == "__main__":

    # raise Exception("Сделать из pylib_*.json, а не из jstopics! Или необязательно?")

    ### main

    main()
