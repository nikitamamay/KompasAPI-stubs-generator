"""

Выполняет парсинг страниц справки SDK Компас
по js-файлам.

"""

from . import logging_system
logger = logging_system.get_logger(__name__)


import typing

import traceback
import os
import sys
import json

import re

from bs4 import BeautifulSoup, Tag, Comment
from bs4.element import NavigableString, PageElement

from . import const

from . import parser_injections
from . import parse_table_of_contents

from .utils import json_utils
from .utils import js_to_json
from .utils import utils
from .utils.utils import render_pretty_single_line

from . import classes
from .classes import HelpPageType, DescriptionSection, Topic, TOCEntry
from .classes import ANY_TYPE_NAME, ENUM_UNNAMED
from .classes import CLASS_NAME_IDispatch


# re_identifier = re.compile(r"\b[^\s\/\.]+\b")  # do not use!
re_identifier_with_cyrillic = re.compile(r"\b(?!NURBS-)[A-Za-z_][A-Za-z0-9_КЕНХОРАВСМТехорас]*\b", )  # ложное срабатывание на некоторых методах с текстом "NURBS-кривые" и "NURBS-поверхности"  # не_ставить re.IGNORECASE !
re_identifier_with_cyrillic_only = re.compile(r"^[A-Z_][A-Z0-9_КЕНХОРАВСМТехорас]*\b$", re.IGNORECASE)

re_page_title_interface = re.compile(r"Интерфейс?ы? *-? *(\S+\b)")

re_heading_interface     = re.compile(r"Интерфейс ?\.{0,3}$")
re_heading_example       = re.compile(r"Пример ?\.{0,3}$")
re_heading_events        = re.compile(r"Интерфейс событий ?\.{0,3}$")
re_heading_description   = re.compile(r"Описание ?(|:|\.)$")
re_heading_hierarchy     = re.compile(r"Иерархия ?(|:|\.)$")
re_heading_notes         = re.compile(r"П?римечани[яе] ?(|:|\.)$")  # нет буквы П в 'itextline_level.js"
re_heading_syntax_auto   = re.compile(r"(Синтаксис Automation ?(|:|\.)|Синтаксис ?:)$")
re_heading_syntax_com    = re.compile(r"Синтаксис (C|С)OM ?(|:|\.)$")
re_heading_input_params  = re.compile(r"((В?ходные |)пара?метры|Входной параметр|Входные данные) ?(|:|\.)$", re.IGNORECASE)
re_heading_output_params = re.compile(r"(Выходн(ые|ой) параметры?) ?(|:|\.)$", re.IGNORECASE)
re_heading_return_value  = re.compile(r"(Возвращаемое значение) ?(|:|\.)$", re.IGNORECASE)

re_starts_in_brackets = re.compile(r"(\(\s*(\*+)\s*\))")  # удаление строки с двумя звёздочками (типа "Получить свойство (**)")

re_property_type = re.compile(r"^Тип данных ?: ?([^\n]+)", re.MULTILINE)
re_bool_type     = re.compile(r"\b(BOOL|TRUE|FALSE)\b", re.IGNORECASE | re.MULTILINE)
re_str_type      = re.compile(r"\b(BSTR|строка)\b", )
re_int_type      = re.compile(r"\b(long|int|short)\b", re.IGNORECASE)
re_float_type    = re.compile(r"\b(float|double)\b", re.IGNORECASE)
re_any_type      = re.compile(r"\bVARIANT\b", re.IGNORECASE)
re_None_type     = re.compile(r"\bNULL\b", re.IGNORECASE)

# re_safearray = re.compile(r"\bSafeArray\b", re.IGNORECASE)
re_vt_type       = re.compile(r"\bVT_[A-Z0-9]\b", re.IGNORECASE)
re_vt_array_type = re.compile(r"\bVT_ARRAY *\|? *(VT_[A-Z0-9]+)\b", re.IGNORECASE)

re_integer_only = re.compile(r"^([\+-]?\d+|0[xX]\d+)$")  # под 'only имеется в виду, что вся строка (все содержимое ячейки таблицы) будет соответствовать этому RegExp.  # спасает от случаев ложных срабатываний на строках типа "90 градусов".


VT_TYPES = {
    "VT_EMPTY": "typing.Any",
    "VT_NULL": "None",
    "VT_I2": "int",
    "VT_I4": "int",
    "VT_R4": "float",
    "VT_R8": "float",
    # "VT_CY": ,
    # "VT_DATE": ,
    "VT_BSTR": "str",
    "VT_DISPATCH": CLASS_NAME_IDispatch,
    # "VT_ERROR": ,
    "VT_BOOL": "bool",
    "VT_VARIANT": "typing.Any",
    "VT_UNKNOWN": "IUnknown",
    # "VT_DECIMAL": ,
    "VT_I1": "int",  # char; int_1byte
    "VT_UI1": "int",  # unsigned int_1byte
    "VT_UI2": "int",
    "VT_UI4": "int",
    "VT_I8": "int",
    "VT_UI8": "int",
    "VT_INT": "int",
    "VT_UINT": "int",
    "VT_VOID": "int",
    "VT_HRESULT": "int",  # HRESULT, то есть код ошибки. int_4bytes
    # "VT_PTR": ,
    "VT_SAFEARRAY": "list",
    "VT_CARRAY": "list",
    # "VT_USERDEFINED": ,
    "VT_LPSTR": "str",
    "VT_LPWSTR": "str",
    # "VT_RECORD": ,
    # "VT_INT_PTR": ,
    # "VT_UINT_PTR": ,
    # "VT_FILETIME": ,
    # "VT_BLOB": ,
    # "VT_STREAM": ,
    # "VT_STORAGE": ,
    # "VT_STREAMED_OBJECT": ,
    # "VT_STORED_OBJECT": ,
    # "VT_BLOB_OBJECT": ,
    # "VT_CF": ,
    # "VT_CLSID": ,
    # "VT_VERSIONED_STREAM": ,
    # "VT_BSTR_BLOB": ,
    "VT_VECTOR": "list",
    "VT_ARRAY": "list",
    # "VT_BYREF": ,
    # "VT_RESERVED": ,
    # "VT_ILLEGAL": ,
    # "VT_ILLEGALMASKED": ,
    # "VT_TYPEMASK": ,
}


class DescriptionData():
    def __init__(self):
        self.docstring: str = ""
        self.parent_interface_href: str = ""
        self.example_href: str = ""
        self.input_parameters: dict[str, str] = {}
        self.return_type: str = ""


def get_VT_type(s_vt: str) -> str:
    return VT_TYPES.get(s_vt.upper(), "typing.Any")


def search_identifier(text: str, do_match: bool = False) -> str:
    if do_match:
        m = re_identifier_with_cyrillic_only.match(text)
    else:
        m = re_identifier_with_cyrillic.search(text)
    if m is None:
        return ""
    return utils.ensure_latin(m.group(0))


def extract_subsections_hrefs(soup: Tag) -> None:
    toc_title_tags = soup.find_all("p", attrs={"class": "p_Z_LOC_TOC_Title"})
    for toc_title_tag in toc_title_tags:
        toc_title_tag.extract()

    toc_entry_tags = soup.find_all("p", attrs={"class": "p_Z_LOC_TOC"})
    for toc_entry_tag in toc_entry_tags:
        toc_entry_tag = toc_entry_tag.extract()


def parse_tag_text_to_single_line(tag: Tag) -> str:
    return render_pretty_single_line(tag.get_text().replace("\n", " "))


def has_bold_text(tag: PageElement) -> bool:
    if isinstance(tag, Tag):
        span = tag.find("span", attrs={"class": "f_bodytext"})
        if isinstance(span, Tag):
            return "bold" in span.attrs.get("style", "")
    return False


def _vertical_borders_comments():
    yield ""
    yield "  # "
    while True:
        yield "   "

def _vertical_borders():
    while True:
        yield " | "


def render_table(
        tag_table: Tag,
        do_render_horizontal_border: bool = True,
        vertical_borders: typing.Callable[[], typing.Iterable[str]] = lambda: _vertical_borders(),
        do_strip_row_lines: bool = True,
        ) -> str:
    table: list[list[str]] = []

    ### парсинг тегов таблицы и расчет размеров контента

    max_column_count = 0

    row_tags = tag_table.find_all("tr")  # TODO добавить поддержку tbody, caption и др.
    for i, row_tag in enumerate(row_tags):
        assert isinstance(row_tag, Tag)
        row = []
        table.append(row)
        cell_tags = row_tag.find_all(recursive=False)  # TODO добавить поддержку tr, th; TODO добавить поддержку rowspan, colspan
        for j, cell_tag in enumerate(cell_tags):
            cell_content = render_pretty_single_line(cell_tag.get_text())  # TODO добавить поддержку многостроковых ячеек
            row.append(cell_content)
        max_column_count = max(max_column_count, len(cell_tags))

    column_widths: list[int] = [0 for i in range(max_column_count)]

    for row in table:
        for j, cell in enumerate(row):
            for line in cell.splitlines(False):
                column_widths[j] = max(column_widths[j], len(line))

    ### отрисовка таблицы

    string: str = ""
    s_horizontal_border: str = ""

    if do_render_horizontal_border:
        borders = vertical_borders().__iter__()
        s_table_length: int = len(next(borders))
        for i in column_widths:
            s_table_length += i + len(next(borders))
        s_horizontal_border = f" +{'-' * (s_table_length - 4)}+ \n"  # -2 потому что плюсы, и еще -2 потому что вокруг плюсов пробелы заменены на минусы

    string += s_horizontal_border

    for row in table:
        s_row = ""
        borders = vertical_borders().__iter__()
        s_row += next(borders)
        for j, cell in enumerate(row):
            s_row += cell.ljust(column_widths[j]) + next(borders)

        string += s_row + "\n" + s_horizontal_border

    if do_strip_row_lines:
        string = "".join([
            line.strip() + "\n"
            for line in string.splitlines()
        ])

    return string


def parse_description_table(
        table_tag: Tag,
        section: str,
        description_data: DescriptionData,
        is_enum: bool,
        ) -> str:
    output: str = ""

    if section in (DescriptionSection.SyntaxAutomation, DescriptionSection.SyntaxCOM):
        # для таблиц о синтаксисе [свойства объекта класса] содержимое вписывается просто в виде текста.
        # Если во второй ячейки строки найдены "**" (второй вариант синтаксиса для языков без свойства
        # - а в Python годится первый), то строка пропускается целиком.

        to_extract: list[Tag] = []
        for tr_tag in table_tag.find_all("tr"):
            m = re_starts_in_brackets.search(tr_tag.get_text())
            if m is not None:
                if m.group(2) == "**":
                    to_extract.append(tr_tag)
        for tag in to_extract:
            tag.extract()

        output += render_table(table_tag, False, lambda: _vertical_borders_comments())
        output = re_starts_in_brackets.subn("", output)[0]

    else:
        output += render_table(table_tag) + "\n"

    return output


def parse_description_section(
        section: str,
        tags: list[Tag],
        description_data: DescriptionData,
        topic: Topic,
        ) -> str:
    section_output: str = ""

    # вывод содержания раздела (по тегам)
    for tag in tags:
        if tag.name == "p":
            section_output += parse_tag_text_to_single_line(tag) + "\n\n"

        elif tag.name == "table":
            string = parse_description_table(tag, section, description_data, False)
            section_output += string

        else:
            logger.warning(f"parse_description_section(): Предупреждение: неизвестный тег: '{tag.name}' у {topic}")

    if section_output != "":
        # оборачивание кода раздела "Синтаксис" в кавычки-апострофы
        if section in (DescriptionSection.SyntaxAutomation, DescriptionSection.SyntaxCOM):
            section_output = section_output.replace("\n\n", "\n")
            section_output = f"```\n{section_output}```\n\n"

        # вывод заголовка раздела
        if not section in (DescriptionSection.PlainDescription, DescriptionSection.Notes):
            section_output = f"### {section}\n\n" + section_output


    ### определение типа свойства или возвращаемого значения метода
    def _try_to_update_value_types():
        match_of_re: list[re.Match] = [None] # type: ignore
        def _assign_match(o) -> bool:
            match_of_re[0] = o
            return o

        if description_data.return_type == "" \
                and section in (DescriptionSection.PlainDescription, DescriptionSection.ReturnValue):
            obtained_return_type: str = ""
            text_to_search_in: str = section_output

            # сужение области поиска до строки (если она есть) с текстом "Тип данных:"
            if _assign_match(re_property_type.search(section_output)):
                text_to_search_in = match_of_re[0].group(1)

            # найденные типы
            if re_bool_type.search(text_to_search_in):
                obtained_return_type = "bool"

            elif re_str_type.search(text_to_search_in):
                obtained_return_type = "str"

            elif re_int_type.search(text_to_search_in):
                obtained_return_type = "int"

            elif re_float_type.search(text_to_search_in):
                obtained_return_type = "float"

            # elif re_safearray.search(text_to_search_in):
            #     obtained_return_type = "list"

            elif _assign_match(re_vt_array_type.search(text_to_search_in)):
                obtained_return_type = f"list[{get_VT_type(match_of_re[0].group(1))}]"

            elif _assign_match(re_vt_type.search(text_to_search_in)):
                obtained_return_type = f"{get_VT_type(match_of_re[0].group(1))}"

            elif re_any_type.search(text_to_search_in):
                obtained_return_type = ANY_TYPE_NAME

            elif re_None_type.search(text_to_search_in):
                obtained_return_type = "None"

            else:
                obtained_types: list[str] = []
                for s in re_identifier_with_cyrillic.finditer(text_to_search_in):
                    t = utils.ensure_latin(s.group(0))
                    if t.isascii():
                        obtained_types.append(t)

                obtained_return_type = "|".join(obtained_types)

            if obtained_return_type != "":
                logger.debug(f"\t_try_to_update_value_types(): найденный тип данных = '{obtained_return_type}' у '{topic.own_href}'")
                if description_data.return_type != "":
                    description_data.return_type += "|" + obtained_return_type
                else:
                    description_data.return_type += obtained_return_type

    _try_to_update_value_types()

    return section_output

def parse_description(tag_help_body: Tag, topic: Topic) -> DescriptionData:
    """
    Выполняет парсинг тела страницы
    и в конечном счете формирует python docstring (`__doc__`) - описание объекта
    (интерфейса, свойства, метода или др.).
    """
    own_href = topic.own_href
    description_data = DescriptionData()

    ### этап 1: разложение тегов по разделам

    sections: dict[str, list[Tag]] = {
        DescriptionSection.PlainDescription: [],
    }
    current_section: str = DescriptionSection.PlainDescription

    tags = tag_help_body.find_all(recursive=False)
    for tag in tags:
        if not isinstance(tag, Tag):
            assert isinstance(tag, (NavigableString, str))
            ns: NavigableString|str = tag
            ns = ns.strip()
            if ns != "":
                logger.error(f"parse_description(): Ошибка: контент вне тега body: {repr(ns)} у '{topic}'")
            continue

        if tag.name == "p":
            tag_has_bold_text: bool = has_bold_text(tag)
            tag_class: str = " ".join(tag.get_attribute_list("class"))

            # пропуск ссылок на подразделы и пропуск тегов иерархии
            if tag_class in ("p_Z_LOC_TOC_Title", "p_Z_LOC_TOC") \
                    or tag_class.startswith("p_Hier_"):
                continue

            tag_text = render_pretty_single_line(tag.get_text().replace("\n", " "))

            if tag_text == "":  # пропуск параграфа, в котором нет текста --- в том числе первого параграфа, где ссылка без текста, но с id
                continue

            # Примечание: match() с паттерном без $ на конце - это аналог startswith().

            if re_heading_interface.match(tag_text):
                tag_a = tag.find(attrs={"href": True})
                if tag_a is not None:
                    assert isinstance(tag_a, Tag)
                    description_data.parent_interface_href = str(tag_a.attrs["href"])
                    if description_data.parent_interface_href != "":
                        description_data.parent_interface_href = utils.ensure_ext(description_data.parent_interface_href, ".js")
                        description_data.parent_interface_href = parser_injections.fix_parent_interface_href(description_data.parent_interface_href, own_href)
                continue

            if re_heading_example.match(tag_text):
                tag_a = tag.find(attrs={"href": True})
                if tag_a is not None:
                    assert isinstance(tag_a, Tag)
                    description_data.example_href = str(tag_a.attrs["href"])
                continue

            if re_heading_events.match(tag_text):
                tag_a = tag.find(attrs={"href": True})
                # if tag_a is not None:
                    # assert isinstance(tag_a, Tag)
                    # description_data.??? = str(tag_a.attrs["href"])
                continue

            if re_heading_description.match(tag_text):
                current_section = DescriptionSection.PlainDescription
                continue

            if re_heading_hierarchy.match(tag_text):
                current_section = DescriptionSection.Hierarchy
                continue

            if re_heading_notes.match(tag_text):
                current_section = DescriptionSection.Notes
                continue

            if re_heading_syntax_auto.match(tag_text):
                # Просто "Синтаксис:" - в ('ikompasdocument3d_enableundo.js', 'ikompasdocument3d_undocontainer.js')
                current_section = DescriptionSection.SyntaxAutomation
                continue

            if re_heading_syntax_com.match(tag_text):
                current_section = DescriptionSection.SyntaxCOM
                continue

            if re_heading_input_params.match(tag_text):
                current_section = DescriptionSection.InputParameters
                continue

            if re_heading_output_params.match(tag_text):
                current_section = DescriptionSection.OutputParameters
                continue

            if re_heading_return_value.match(tag_text):
                current_section = DescriptionSection.ReturnValue
                continue


            if tag_has_bold_text:
                if current_section == DescriptionSection.PlainDescription and len(sections[DescriptionSection.PlainDescription]) == 0:  # для первого абзаца (краткого описания) на странице
                    pass
                else:
                    fixed_current_section = parser_injections.fix_description_section_heading(tag_text, own_href)
                    if fixed_current_section is not None:
                        current_section = fixed_current_section
                    else:
                        # для следующих известных заголовков это предупреждение будет, но это нормально.
                        # if re.match(r"Значени[яе] свойства ?(|:|\.)$$", tag_text):
                        # if tag_text == ("Пример:", "Термины:", "События:"):
                        #
                        # но есть много страниц, где жирным выделено краткое описание в самом начале страницы;
                        # а иногда оно не в самом начале, а после ссылки на другую страницу (типа "События...");
                        # поэтому, чтобы не править много страниц, пусть эти все жирные тексты будут просто
                        # помещены по-умолчанию в раздел общего описания и всё, пусть и с предупреждением.
                        #
                        logger.debug(f"parse_description(): Предупреждение: помещен в раздел общего описания текст с жирным текстом '{tag_text}' у {topic}")
                        current_section = DescriptionSection.PlainDescription
                        # continue здесь не надо. Подразумевается, что это не заголовок, а часть раздела общего описания

        elif tag.name == "div":
            child: Tag|None = tag.find(lambda tagname: True)
            if child is None:
                logger.warning(f"parse_description(): Предупреждение: Пустой div у {topic}")
                continue

            if child.name != "table":
                logger.warning(f"parse_description(): Предупреждение: Не найдена таблица внутри div: {tag} у {topic}")
                continue

            tag = child

        else:
            logger.error(f"parse_description(): Ошибка: неизвестный тег: '{tag.name}' у {topic}")
            # tag_text = pretty_text(tag.get_text().replace("\n", " "))
            # continue

        if not current_section in sections:
            sections[current_section] = []
        sections[current_section].append(tag)

    return_type = parser_injections.fix_function_return_type(own_href)
    if return_type is not None:
        description_data.return_type = return_type

    ### этап 2: сборка текста (генерация docstring)

    # заголовок
    description_data.docstring = f"## {utils.render_pretty_single_line(topic.hmTitle)}\n\n"

    # # хлебные крошки
    # if topic.hmBreadCrumbs != "":
    #     description_data.docstring += f"Путь в Справке: {topic.hmBreadCrumbs}.\nФайл в Справке: `{utils.ensure_ext(topic.own_href, ".html")}`.\n\n"

    # ссылка на страницу Справки с примером
    if description_data.example_href != "":
        description_data.docstring += f"Пример в Справке: `{description_data.example_href}`\n\n"

    # содержимое разделов страницы Справки
    for section in (  # порядок секций
            DescriptionSection.PlainDescription,
            DescriptionSection.Notes,  # не в конце, а сразу после описания.
            # DescriptionSection.Hierarchy,  # не показывается
            DescriptionSection.SyntaxAutomation,
            # DescriptionSection.SyntaxCOM,  # не показывается
            DescriptionSection.InputParameters,
            DescriptionSection.OutputParameters,
            DescriptionSection.ReturnValue,
            ):
        if section in sections:
            description_data.docstring += parse_description_section(section, sections[section], description_data, topic)

    description_data.docstring = description_data.docstring

    return description_data



def parse_description_for_enum(body_tag: Tag, topic: Topic) -> bool:
    """ Возвращает `True`, если парсинг выполнен успешно. """
    own_href = topic.own_href

    description_data = DescriptionData()

    name_cell_index: int = -1
    value_cell_index: int = -1
    name_cell_index, value_cell_index = parser_injections.fix_enum_table_cell_indexes(own_href)

    table_tags = [
        table_tag.extract()
        for table_tag in body_tag.find_all("table")
    ]  # FIXME разрешается ли несколько таблиц?
    if len(table_tags) != 1:
        logger.error(f"parse_description_for_enum(): Ошибка: Неверное количество таблиц ({len(table_tags)} шт.) у {topic}")
        return False

    table_tag: Tag = table_tags[0]

    ### исправление таблицы
    # удаление строк, в которых есть colspan или rowspan
    tags_to_remove: list[Tag] = []
    for tr_tag in table_tag.find_all("tr"):
        if tr_tag.find(attrs={ "colspan": True }) or tr_tag.find(attrs={ "rowspan": True }):
            tags_to_remove.append(tr_tag)

    if len(tags_to_remove) > 0:
        logger.warning(f"parse_description_for_enum(): Предупреждение: таблица содержит некорректные строки (colspan, rowspan) у {topic}")
        for tag in tags_to_remove:
            tag.extract()


    ### понимание того, что где в каком столбце:
    # сначала ищется столбец с идентификатором - это имена (enum members);
    # затем - столбец с цифрами - это значения (enum values);
    # остальные столбцы - это комментарии

    if name_cell_index == -1 or value_cell_index == -1:
        row_tag = table_tag.find("tr")
        if row_tag is None:
            logger.error(f"parse_description_for_enum(): Ошибка: не найдена строка таблицы у {topic}")
            return False

        td_tags = row_tag.find_all("td")

        for i, td_tag in enumerate(td_tags):
            if search_identifier(td_tag.get_text().strip(), do_match = True) != "":
                name_cell_index = i

        if name_cell_index == -1:
            logger.error(f"parse_description_for_enum(): Ошибка: не определен индекс столбца с идентификатором enum у {topic}")
            return False

        for i, td_tag in enumerate(td_tags):
            if i == name_cell_index: continue
            if re_integer_only.match(td_tag.get_text().strip()) is not None:
                value_cell_index = i

        if value_cell_index == -1:
            logger.error(f"parse_description_for_enum(): Ошибка: не определен индекс столбца с идентификатором enum у {topic}")
            return False

        logger.debug(f"parse_description_for_enum(): индексы столбцов у enum: name={name_cell_index}, value={value_cell_index} у {topic}")  # не надо в stderr

    ### парсинг

    # к этому моменту из body_tag извлечены таблицы с enum members, поэтому они не попадут в docstring.
    docstring = parse_description(body_tag, topic).docstring

    enum_members: list[list[str]] = []

    for row_tag in table_tag.find_all("tr"):
        name: str = ""
        value: str = ""
        other: list[str] = []

        for i, td_tag in enumerate(row_tag.find_all("td", recursive=False)):
            td_text = render_pretty_single_line(td_tag.get_text())
            if i == name_cell_index:
                name = td_text
            elif i == value_cell_index:
                value = td_text
            else:
                other.append(td_text)

        if name == "" or value == "":
            logger.error(f"parse_description_for_enum(): Ошибка: не извлечены имя и/или значение в строке таблицы еnum: name={repr(name)}, value={repr(value)} у {topic}")
            continue

        if not search_identifier(name, True):
            logger.error(f"parse_description_for_enum(): Ошибка: некорректный идентификатор (enum member name) в строке таблицы: name={repr(name)}, value={repr(value)} у {topic}")
            continue

        member_docstring = "\n\n".join(other)
        enum_members.append([name, value, member_docstring])

    ### применение свойств

    topic.docstring = docstring
    topic.enum_members = enum_members

    return True


def parse_hierarchy(soup: Tag, interface_class_name: str, own_href: str) -> list[list[str]]:
    hierarchy = parser_injections.fix_class_hierarchy(own_href)
    if hierarchy is not None:
        return hierarchy

    hierarchy_classes: list[str] = []
    hierarchy_add: list[str] = []

    tags = soup.find_all(attrs={
        "class": lambda s: s is not None and "p_Hier_" in s,
    })

    for tag in tags:
        assert isinstance(tag, Tag)

        class_name = " ".join(tag.get_attribute_list("class"))
        if "p_Hier_ADD" in class_name:
            # continue
            name = parser_injections.fix_interface_name(render_pretty_single_line(tag.get_text()))
            if name != "":
                hierarchy_add.append(name)
        else:
            name = parser_injections.fix_interface_name(render_pretty_single_line(tag.get_text()))
            if name != "":
                hierarchy_classes.append(name)

    direct_base_classes = []
    if len(hierarchy_classes) > 0:
        try:
            i = hierarchy_classes.index(interface_class_name)
            if i > 0:
                direct_base_classes = [hierarchy_classes[i - 1]]
            else:
                logger.warning(f"parse_hierarchy(): Предупреждение: не найден родитель у '{interface_class_name}'. hierarchy_classes={hierarchy_classes}; в файле '{own_href}'")
        except ValueError:
            logger.warning(f"parse_hierarchy(): Предупреждение: не найдено собственное имя интерфейса у '{interface_class_name}'. hierarchy_classes={hierarchy_classes}; в файле '{own_href}'")


    hierarchy = [direct_base_classes, hierarchy_add]
    return hierarchy




def parse_single_jstopic(
        filepath: str,
        own_href: str|None = None
        ) -> Topic|None:
    """
    Выполняет парсинг одной страницы Справки.

    Возвращает `None`, если страница бесполезна или при парсинге произошла ошибка.
    """

    jstopic = Topic()
    if own_href is None:
        jstopic.own_href = os.path.split(filepath)[1]
    else:
        jstopic.own_href = own_href

    if parser_injections.is_useless_page(jstopic.own_href):
        logger.debug(f"\tизвестно, что эта страница бесполезна.")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = f.read()

    ### извлечение JS-кода объекта jstopic

    try:
        data = utils.fix_js_object_to_json(data)
    except Exception as e:
        logger.error(f"parse_single_jstopic(): Ошибка: utils.fix_js_object_to_json() c файлом '{filepath}'", exc_info=True)
        return None

    ### парсинг JSON

    try:
        d = json.loads(data, )
    except Exception as e:
        logger.error(f"parse_single_jstopic(): Ошибка: json.loads() c файлом '{filepath}'", exc_info=True)
        return None

    jstopic.from_json_base(d)

    ### парсинг html-контента объекта jstopic
    try:
        # breadcrumps
        bc_soup = BeautifulSoup(jstopic.hmBreadCrumbs, "lxml")
        jstopic.hmBreadCrumbs = render_pretty_single_line(bc_soup.get_text())

        # body
        soup = BeautifulSoup(jstopic.hmBody, "lxml")
        body: Tag = soup.find("body") # type: ignore
        assert isinstance(body, Tag)

        # исправление косяков справки для некоторых известных страниц
        parser_injections.fix_body(body, jstopic.own_href)

        # удаление комментариев
        for tag in body.find_all(string=lambda text: isinstance(text, Comment)):
            tag.extract()

        ### здесь body готов для парсинга человекочитаемого description

        def _parse_description() -> bool:
            """ Возвращает `True`, если текст описания непустой """
            description_data: DescriptionData = parse_description(body, jstopic)
            jstopic.docstring = description_data.docstring
            jstopic.parent_interface_href = description_data.parent_interface_href
            jstopic.example_href = description_data.example_href
            jstopic.value_types["return"] = description_data.return_type
            jstopic.value_types.update(description_data.input_parameters)
            return jstopic.docstring != ""

        ### назначение типа страницы

        def _is_interface_page():
            is_interface_page: bool|None = parser_injections.is_interface_page(jstopic.own_href)
            if is_interface_page is None:
                return "Интерфей" in jstopic.hmTitle
            return is_interface_page

        def _print_empty_own_name():
            logger.error(f"parse_single_jstopic(): Ошибка: не извлечено own_name из hmTitle={repr(jstopic.hmTitle)} у {jstopic}")

        # страница перечня ссылок на свойства, методы, события
        if jstopic.own_href.endswith("_props.js") \
                or jstopic.own_href.endswith("_methods.js") \
                or jstopic.own_href.endswith("_propers.js") \
                or jstopic.own_href.endswith("_events.js") \
                or jstopic.hmTitle.endswith("- свойства") \
                or jstopic.hmTitle.endswith("- методы"):
            jstopic.page_type = HelpPageType.LinkListPage
            logger.debug(f"parse_single_jstopic(): Предупреждение: страница со ссылками. Пропуск. {jstopic}")
            return None

        # страница класса интерфейса
        if _is_interface_page():
            jstopic.page_type = HelpPageType.Interface
            if not _parse_description():
                logger.debug(f"parse_single_jstopic(): Предупреждение: страница без содержимого. Пропуск. {jstopic}")
                return None

            jstopic.own_name = parser_injections.fix_interface_name(search_identifier(jstopic.hmTitle), jstopic.own_href)
            if jstopic.own_name == "":
                _print_empty_own_name()
                return None

            jstopic.hierarchy = parse_hierarchy(body, jstopic.own_name, jstopic.own_href)
            return jstopic

        # страница перечисления (enum)
        if "Константы API" in jstopic.hmBreadCrumbs \
                or "Структуры параметров и константы" in jstopic.hmBreadCrumbs:
            jstopic.page_type = HelpPageType.Enum

            jstopic.own_name = parser_injections.fix_enum_name(search_identifier(jstopic.hmTitle), jstopic.own_href)
            if jstopic.own_name == "":
                jstopic.own_name = ENUM_UNNAMED

            if not parse_description_for_enum(body, jstopic):
                return None

            return jstopic


        # страница метода или свойства
        if "- свойства" in jstopic.hmBreadCrumbs \
                or "- методы" in jstopic.hmBreadCrumbs:
            jstopic.page_type = HelpPageType.PropertyOrMethod
            if not _parse_description():
                logger.debug(f"parse_single_jstopic(): Предупреждение: страница без содержимого. Пропуск. {jstopic}")
                return None

            jstopic.own_name = parser_injections.fix_property_or_method_name(search_identifier(jstopic.hmTitle), jstopic.own_href)
            if jstopic.own_name == "":
                _print_empty_own_name()
                return None

            # не стоит пытаться найти parent_interface_href через hmBreadCrumps: это слишком сложно.
            # Если уж править, то тогда в parser_injections добавлять ссылку на parent_interface_href в fix_body() для определенных страниц.
            if jstopic.parent_interface_href == "":
                logger.warning(f"parse_single_jstopic(): Предупреждение: пустой parent_interface_href у {jstopic}")

            return jstopic

        # # страница события
        # if "- события" in jstopic.hmBreadCrumbs:
        #     logger.warning(f"parse_single_jstopic(): Предупреждение: найдена страница события. Что с этим делать? {jstopic}")
        #     pass  # TODO
        #     return jstopic

        # если пустая страница
        if not _parse_description():
            jstopic.page_type = HelpPageType.EmptyPage
            logger.warning(f"parse_single_jstopic(): Предупреждение: страница без содержимого. Пропуск. {jstopic}")
            return None

        # страница чего-то другого
        logger.warning(f"parse_single_jstopic(): Предупреждение: страница неизвестного типа. {jstopic}")
        return None

    except Exception as e:
        logger.error(f"parse_single_jstopic(): Ошибка: при парсинге html-контента у {jstopic}", exc_info=True)

    if jstopic.own_name == "":
        logger.critical(f"parse_single_jstopic(): Ошибка: попытка возврата jstopic с пустым own_name: {jstopic}")
        return None

    return jstopic


def parse_jstopics(
        filepaths: list[str],
        parsed_topics: set[str] = set(),
        ) -> list[Topic]:
    jstopics: list[Topic] = []

    for filepath in filepaths:
        jstopic_href = os.path.split(filepath)[1]
        logger.debug(f"'{jstopic_href}'")

        if jstopic_href in parsed_topics:
            logger.debug(f"\tПарсинг уже выполнен ранее для '{jstopic_href}'. Пропуск.")
            continue

        parsed_topics.add(jstopic_href)

        topic = parse_single_jstopic(filepath, own_href=jstopic_href)
        logger.debug(f"\ttopic={topic}")

        if topic is None:
            continue

        jstopics.append(topic)

    logger.info(f"Извлечено {len(jstopics)} объектов jstopic из {len(filepaths)} ссылок.")
    return jstopics


def find_non_unique_topics(jstopics: typing.Iterable[Topic]) -> dict[str, list[Topic]]:
    names_and_topics: dict[str, list[Topic]] = {}
    for topic in jstopics:
        if topic.own_name != "" and topic.own_name != classes.ENUM_UNNAMED:
            name = classes.get_topic_full_name(topic)
            if not name in names_and_topics:
                names_and_topics[name] = []
            names_and_topics[name].append(topic)
    return names_and_topics



def _merge_enum_members(members_to_stay: list[list[str]], members_to_remove: list[list[str]]) -> None:
    def _find_member(name: str) -> list[str]|None:
        for member in members_to_stay:
            n = member[0]
            if n == name:
                return member
        return None

    for r_member in members_to_remove:
        r_name, r_value, r_docstring = r_member
        s_member = _find_member(r_name)
        if s_member is None: # если нет удаляемого member в списке остающихся members
            members_to_stay.append(r_member.copy())
        else: # если удаляемый member есть в списке остающихся members
            s_name, s_value, s_docstring = s_member
            if r_value != s_value:
                logger.error(f"merge_enum_members(): Ошибка: для имен '{s_name}' разные значения: {repr(s_value)}, {repr(r_value)}")
                continue

            # r_member[2] = r_docstring if len(r_docstring) > len(s_docstring) else s_docstring
            r_member[2] = r_docstring + "\n\n" + s_docstring


def fix_jstopics_after_parsing(jstopics: list[Topic]) -> None:
    """
    Метод должен вызываться после того, как выполнен парсинг для всех страниц
    Справки: `Kompas6API5`, `KompasAPI7`, `constants`.
    """
    logger.info(f"Исправление объектов jstopic после окончательного парсинга...")

    ### проверка на уникальность наименований
    # нельзя использовать `classes.filter_by_type()`, потому что она возвращает словарь, и там классы одного типа затираются

    names_and_topics: dict[str, list[Topic]] = find_non_unique_topics(jstopics)

    for name, topics_list in names_and_topics.items():
        if len(topics_list) > 1:
            for topic in topics_list:
                logger.error(f"fix_jstopics_after_parsing(): Ошибка: объект jstopic с повторяющимся именем '{name}': {topic}")

    ### назначение родительских интерфейсов для страниц свойства/метода

    interfaces: list[Topic] = list(classes.filter_by_type(jstopics, HelpPageType.Interface).values())
    fixed_count: int = 0

    for topic in jstopics:
        if topic.page_type == HelpPageType.PropertyOrMethod:
            if topic.parent_interface_href == "":
                logger.error(f"fix_jstopics_after_parsing(): Ошибка: нет ссылки на родительский интерфейс у {topic}")
                continue

            parent_topic = classes.find_jstopic_by_href(topic.parent_interface_href, interfaces)
            if parent_topic is None:
                logger.error(f"fix_jstopics_after_parsing(): Ошибка: не найден родительский интерфейс по ссылке '{topic.parent_interface_href}' для {topic}")
                continue

            topic.parent_interface_name = parent_topic.own_name
            fixed_count += 1

    ### слияние enums с одинаковыми именами

    for name, topics_list in names_and_topics.items():
        topics_types = [t.page_type == HelpPageType.Enum for t in topics_list]
        if len(topics_list) > 1:
            if not any(topics_types):
                continue

            if not all(topics_types):
                logger.error(f"fix_jstopics_after_parsing(): Ошибка: объекты jstopic имеют разные типы, но одинаковые имена {repr(name)}: {topics_list}")
                continue

            topic = topics_list[0]  # остающийся объект. Остальные - к удалению.

            for t in topics_list:
                if t == topic: continue

                _merge_enum_members(topic.enum_members, t.enum_members)

                jstopics.remove(t)
                logger.warning(f"fix_jstopics_after_parsing(): Предупреждение: удален объект jstopic вследствие слияния enums с одинаковым именем {repr(name)}: {t}")


    ### вывод объектов, у которых page_type == Unknown

    for topic in jstopics:
        if topic.page_type == HelpPageType.Unknown:
            logger.warning(f"fix_jstopics_after_parsing(): Предупреждение: остается объект jstopic с неизвестным типом страницы: {topic}")

    logger.info(f"Исправлены {fixed_count} объектов jstopic.")


def load_topics(filepath: str) -> list[Topic]:
    if not os.path.exists(filepath):
        logger.error(f"load_topics(): Ошибка: файла не существует: '{filepath}'")
        return []
    l = json_utils.load_json_with_classes(filepath, [Topic])
    logger.info(f"Загружено {len(l)} объектов jstopic (страниц справки) из файла '{filepath}'.")
    return l


def get_jstopics_filepaths(toc_entry: TOCEntry, sdk_base_dir: str) -> list[str]:
    return [
        os.path.join(const.get_jstopics_dir(sdk_base_dir), utils.ensure_ext(toc_entry.href, ".js"))
        for toc_entry in
        parse_table_of_contents.get_toc_entries_list(toc_entry)
    ]


def sort_topics_by_toc(toc_entries_list: list[TOCEntry], topics: typing.Iterable[Topic]) -> list[Topic]:
    toc_entries_hrefs: list[str] = list(
        filter(
            None,
            map(
                lambda k: utils.ensure_ext(k.href, ".js"),
                toc_entries_list,
            )
        )
    )

    def _key(topic: Topic) -> int:
        try:
            return toc_entries_hrefs.index(topic.own_href)
        except ValueError:
            return 10 ** 9

    return sorted(topics, key=_key)




def main(
        sdk_base_dir: str,
        do_k5: bool = True,
        do_k7: bool = True,
        do_const: bool = True,
        ) -> None:

    toc_entries: list[TOCEntry] = parse_table_of_contents.load_root_toc_entries(const.toc_filepath)

    filepaths: list[str] = []

    if do_k7:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api7_root_topic_href, toc_entries, 1)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry, sdk_base_dir))

    if do_k5:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api5_root_topic_href, toc_entries, 1)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry, sdk_base_dir))

    if do_const:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_constants_topic_href, toc_entries, 3)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry, sdk_base_dir))

    jstopics: list[Topic] = []
    jstopics.extend(parse_jstopics(filepaths))

    fix_jstopics_after_parsing(jstopics)

    json_utils.save_json(const.topics_filepath, jstopics)
    logger.info(f"Записано {len(jstopics)} объектов Topic в файл '{const.topics_filepath}'")



if __name__ == "__main__":

#     if len(sys.argv) < 3:
#         print(f"""\
# Usage:
#     {sys.argv[0]} what_to_do help_sdk_base_dir

# what_to_do:
#     1 - KompasAPI 5
#     2 - KompasAPI 7
#     4 - KompasAPI constants
#     7 - all of the above
# """)
#         sys.exit(1)

#     what_to_do = int(sys.argv[1])
#     sdk_base_dir = sys.argv[2]

#     do_k5 = bool(what_to_do & 0b0001)
#     do_k7 = bool(what_to_do & 0b0010)
#     do_const = bool(what_to_do & 0b0100)

#     ### main

#     main(sdk_base_dir, do_k5, do_k7, do_const)

    pass
