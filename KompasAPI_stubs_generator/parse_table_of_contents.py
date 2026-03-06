"""

Выполняет парсинг оглавления Справки SDK Компас
по js-файлу `js/hmcontent.js`.

"""

from . import logging_system
logger = logging_system.get_logger(__name__)

import typing

import traceback
import os
import sys
import json

from bs4 import BeautifulSoup, Tag, Comment
from bs4.element import NavigableString, PageElement


from .utils import json_utils
from .utils import js_to_json
from .utils import utils

from .classes import TOCEntry

from . import const




def read_toc_json(hmcontent_js_filepath: str) -> list[dict]:
    """
    Выполняет парсинг оглавления из файла `hmcontent_js_filepath`
    (обычно это файл `'js/hmcontent.js'`).

    Выяснилось, что оглавление в `js/hmcontent.js` правильнее\\*.
    Так, например, на странице у "Интерфейс ICircularCentres" неверна ссылка на страницу
    с методами (вместо неё - повторная ссылка на раздел со свойствами (props),
    но сама страница с методами есть и видна в оглавлении).

    \\* правильнее, чем ссылки внутри `<p class="p_Z_LOC_TOC"></p>`
    в html-содержимом страниц справки.
    """

    with open(hmcontent_js_filepath, "r", encoding="utf-8") as f:
        data = f.read()

    ### извлечение JS-кода объекта (содержимое внутри {} )
    ### и преобразование JS-кода в JSON

    try:
        data = utils.fix_js_object_to_json(data)
    except Exception as e:
        logger.error(f"read_toc_json(): Ошибка: в fix_js_object_to_json()", exc_info=True)
        # logger.error(utils.indent_lines(traceback.format_exc()), end="")
        return []

    ### парсинг JSON

    try:
        d = json.loads(data, )
    except Exception as e:
        logger.error(f"read_toc_json(): Ошибка: в json.loads()", exc_info=True)
        # logger.error(utils.indent_lines(traceback.format_exc()), end="")
        return []

    items = d["items"]
    logger.info(f"Извлечены записи оглавления из '{hmcontent_js_filepath}'.")
    logger.info(f"На корневом уровне {len(items)} записей.")
    return items


def parse_toc_entry(
        d: dict,
        debug_print_indent_level: int = 0,
        ) -> TOCEntry:
    toc_entry = TOCEntry()
    toc_entry.title = d["cp"].strip()
    toc_entry.href = d["hf"].strip()
    logger.debug(f"{'  '*debug_print_indent_level}'{toc_entry.title}' ('{toc_entry.href}')")
    for child_d in d["items"]:
        if isinstance(child_d, dict):
            toc_entry.children.append(parse_toc_entry(child_d, debug_print_indent_level + 1))
        else:
            logger.debug(f"parse_toc_entry(): Ошибка: ожидается словарь: {repr(child_d)}")
    return toc_entry


def main(
        sdk_base_dir: str,
        ) -> None:
    help_hmcontent_js_filepath: str = const.get_hmcontent_js_filepath(sdk_base_dir)
    toc_filepath: str = const.toc_filepath

    logger.info(f"Чтение JS/JSON из файла '{help_hmcontent_js_filepath}'...")

    toc_items_json: list[dict] = read_toc_json(help_hmcontent_js_filepath)

    logger.info(f"Создание объектов класса TOC_Entry...")

    items: list[TOCEntry] = []

    for toc_dict in toc_items_json:
        items.append(parse_toc_entry(toc_dict))

    logger.info(f"Сохранение объектов в '{toc_filepath}'...")

    json_utils.save_json(toc_filepath, items)

    logger.info(f"Сохранено в '{toc_filepath}'.")


def load_root_toc_entries(
        toc_filepath: str = const.toc_filepath,
        ) -> list[TOCEntry]:
    toc_entries: list[TOCEntry] = json_utils.load_json_with_classes(toc_filepath, [TOCEntry])
    logger.info(f"Загружено оглавление из '{toc_filepath}'. Корневых записей: {len(toc_entries)}.")
    return toc_entries


def get_topic_hrefs_from_toc_entry(
        toc_entry: TOCEntry,
        max_depth: int = 10**9,
        ) -> list[str]:
    hrefs: list[str] = [toc_entry.href]
    if max_depth > 0:
        for child in toc_entry.children:
            hrefs.extend(get_topic_hrefs_from_toc_entry(child, max_depth - 1))
    return hrefs


def get_toc_entry_from_href(
        toc_entry_href: str,
        toc_entries: list[TOCEntry],
        max_depth_to_search: int = 3,
        raise_error_if_not_found: bool = True,
        ) -> TOCEntry|None:
    for toc_entry in toc_entries:
        if toc_entry.href == toc_entry_href:
            return toc_entry

    if max_depth_to_search > 0:
        for toc_entry in toc_entries:
            t = get_toc_entry_from_href(toc_entry_href, toc_entry.children, max_depth_to_search - 1, False)
            if t is not None:
                return t

    if raise_error_if_not_found:
        raise Exception(f"Не найдена toc_entry {repr(toc_entry_href)}")

    return None


def get_toc_entries_list(
        toc_entry: TOCEntry,
        max_depth: int = 10**9,
        ) -> list[TOCEntry]:

    list_of_toc_entries: list[TOCEntry] = [toc_entry]

    if max_depth > 0:
        for child in toc_entry.children:
            list_of_toc_entries.extend(get_toc_entries_list(child))

    return list_of_toc_entries



if __name__ == "__main__":

#     if len(sys.argv) < 2:
#         print(f"""\
# Usage:
#     {sys.argv[0]} help_sdk_base_dir
# """)
#         sys.exit(1)

#     sdk_base_dir = sys.argv[1]

#     main(sdk_base_dir)

    pass
