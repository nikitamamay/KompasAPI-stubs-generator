
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
from .utils.utils import PYTHON_TAB, indent, render_docstring

from . import parse_module
from . import parse_topics
from . import parse_table_of_contents
from . import classes
from .classes import HelpPageType, Topic, TOCEntry, \
    PythonEntry, PythonClass, PythonFunction, PythonVariable, PythonProperty
from .classes import sort_py_entries



def generate_pyi_general(py_entry: PythonEntry) -> str:
    output: str = ""

    if isinstance(py_entry, PythonClass):
        output += generate_pyi_class(py_entry) + "\n"

    elif isinstance(py_entry, PythonFunction):
        output += generate_pyi_function(py_entry) + "\n"

    elif isinstance(py_entry, PythonProperty):  # эта проверка должна быть раньше, чем на PythonVariable
        output += generate_pyi_property(py_entry) + "\n"

    elif isinstance(py_entry, PythonVariable):
        output += generate_pyi_simple_value(py_entry) + "\n"

    else:
        logger.error(f"generate_pyi_general(): Ошибка: неподдерживаемый тип ({type(py_entry)}): {repr(py_entry)}")
        output += generate_pyi_unknown_entry(py_entry) + "\n"

    return output


def generate_pyi_unknown_entry(py_entry: PythonEntry) -> str:
    s_doc: str = ""
    s_href: str = ""

    if py_entry.doc != "":
        s_doc = f"{render_docstring(py_entry.doc)}\n"

    s_href = utils.render_hrefs(py_entry.hrefs, True)

    return f"{py_entry.name} = ...{s_href}\n{s_doc}"


def generate_pyi_simple_value(py_entry: PythonVariable) -> str:
    s_doc: str = ""
    s_type: str = ""
    s_href: str = ""

    if py_entry.value_type != "":
        s_type = f": {py_entry.value_type}"

    if py_entry.doc != "":
        s_doc = f"{render_docstring(py_entry.doc)}\n"

    s_href = utils.render_hrefs(py_entry.hrefs, True)

    return f"{py_entry.name}{s_type} = {py_entry.value}{s_href}\n{s_doc}"


def generate_pyi_property(py_entry: PythonProperty) -> str:
    if not py_entry.has_getter:
        logger.debug(f"generate_pyi_property(): Предупреждение: отсутствует getter у {py_entry}")
        # но getter всё равно будет создан, потому что так устроен декоратор @property в Python.

    output: str = ""

    s_doc: str = ""
    s_type_getter: str = ""
    s_type_setter: str = ""
    s_href: str = ""

    if py_entry.value_type != "":
        s_type_setter = f": {py_entry.value_type}"
        s_type_getter = f" -> {py_entry.value_type}" if py_entry.has_getter else f" -> typing.NoReturn"

    if py_entry.doc != "":
        s_doc = f"{render_docstring(py_entry.doc)}\n"

    s_href = utils.render_hrefs(py_entry.hrefs, True)

    # getter
    output += f"@property\ndef {py_entry.name}(self){s_type_getter}:{s_href}\n{indent(s_doc)}{indent('...')}\n"

    # setter
    if py_entry.has_setter:
        output += f"@{py_entry.name}.setter\ndef {py_entry.name}(self, value{s_type_setter}): ...\n"

    return output


def generate_pyi_function(py_entry: PythonFunction) -> str:
    s_name: str = py_entry.name
    s_params: str = ""
    s_return_type: str = ""
    s_doc: str = ""
    s_href: str = ""

    if py_entry.return_type != "":
        s_return_type = f" -> {py_entry.return_type}"

    s_params = ", ".join(py_entry.parameters)

    if py_entry.doc != "":
        s_doc = f"{render_docstring(py_entry.doc)}\n"

    s_href = utils.render_hrefs(py_entry.hrefs, True)

    return f"def {s_name}({s_params}){s_return_type}:{s_href}\n{indent(s_doc)}{indent('...')}\n"


def generate_pyi_class(py_entry: PythonClass) -> str:
    def _get_sort_key(e: PythonEntry) -> int:
        return {
            PythonClass: 0,
            PythonVariable: 10,
            PythonProperty: 20,
            PythonFunction: 30,
            PythonEntry: 999,
        }[e.__class__]

    output: str = ""
    s_doc: str = ""
    s_href: str = ""

    s_base_classes = ", ".join(py_entry.base_classes)

    if py_entry.doc != "":
        s_doc = f"{render_docstring(py_entry.doc)}\n\n"

    for child in sorted(py_entry.children, key=_get_sort_key):
        output += generate_pyi_general(child)

    if output == "":  # когда нет ни одного дочернего элемента в классе, например, IBreakAngleDimension
        output = "..."

    s_href = utils.render_hrefs(py_entry.hrefs, True)

    return f"class {py_entry.name}({s_base_classes}):{s_href}\n{indent(s_doc)}{indent(output)}\n"


def generate_pyi_module(
        pylib_filepath: str,
        pyi_filepath: str,
        recommended_order: list[str] = []
        ) -> None:
    output: str = \
        "import typing\n" \
        "\n" \
        "from win32com.client import DispatchBaseClass as IDispatch\n" \
        "\n" \
        "\n" \

    py_entries: list[PythonEntry] = parse_module.load_pylib(pylib_filepath)

    py_entries = sort_py_entries(py_entries, recommended_order)

    for py_entry in py_entries:
        output += generate_pyi_general(py_entry) + "\n"

    size: int = utils.write_python_module(pyi_filepath, output)

def main(
        do_k5: bool = True,
        do_k7: bool = True,
        ) -> None:
    root_toc_entries: list[TOCEntry] = parse_table_of_contents.load_root_toc_entries(const.get_toc_filepath())
    topics: list[Topic] = parse_topics.load_topics(const.get_topics_filepath())

    if do_k7:
        root_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api7_root_topic_href, root_toc_entries)
        assert root_entry is not None
        toc_entries_list: list[TOCEntry] = parse_table_of_contents.get_toc_entries_list(root_entry)

        classes_order = [  # в конечном счете сортировка выполняется по `str.lower()`. См. `sort_py_entries()`
            topic.own_name
            for topic in parse_topics.sort_topics_by_toc(
                toc_entries_list,
                classes.filter_by_type(topics, HelpPageType.Interface)
            )
        ]

        generate_pyi_module(const.get_pylib_KAPI7_filepath_updated(), const.get_pyi_KAPI7_filepath(), classes_order)

    if do_k5:
        root_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api5_root_topic_href, root_toc_entries)
        assert root_entry is not None
        toc_entries_list: list[TOCEntry] = parse_table_of_contents.get_toc_entries_list(root_entry)

        classes_order = [  # в конечном счете сортировка выполняется по `str.lower()`. См. `sort_py_entries()`
            topic.own_name
            for topic in parse_topics.sort_topics_by_toc(
                toc_entries_list,
                classes.filter_by_type(topics, HelpPageType.Interface)
            )
        ]

        generate_pyi_module(const.get_pylib_K6API5_filepath_updated(), const.get_pyi_K6API5_filepath(), classes_order)



if __name__ == "__main__":

#     if len(sys.argv) < 2:
#         print(f"""\
# Usage:
#     {sys.argv[0]} what_to_do

# what_to_do:
#     1 - KompasAPI 5
#     2 - KompasAPI 7
#     3 - both
# """)
#         sys.exit(1)

#     what_to_do = int(sys.argv[1])
#     do_k5 = bool(what_to_do & 0b0001)
#     do_k7 = bool(what_to_do & 0b0010)

    ### main

    # main(do_k5, do_k7)
    main()
