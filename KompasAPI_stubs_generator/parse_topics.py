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
import copy  # для copy.deepcopy()

from . import const

from . import parser_injections
from . import parse_table_of_contents

from .utils import json_utils
from .utils import js_to_json
from .utils import utils
from .utils import statistics
from .utils.utils import render_pretty_single_line
from .utils import long_processing_indication

from . import classes
from .classes import HelpPageType, DescriptionSection, Topic, TOCEntry
from .classes import ANY_TYPE_NAME, ENUM_UNNAMED
from .classes import CLASS_NAME_IDISPATCH


# ложное срабатывание на некоторых методах с текстом "NURBS-кривые" и "NURBS-поверхности"  # не_ставить re.IGNORECASE !
re_identifier_with_cyrillic = re.compile(r"\b(?!NURBS)[A-Za-z_][A-Za-z0-9_КЕНХОРАВСМТехорас]*\b", )

# ложное срабатывание на названиях интерфейсов с текстом "трехмерные NURBS" в K6API5
re_identifier_with_cyrillic_only = re.compile(r"^(?!NURBS)[A-Za-z_][A-Za-z0-9_КЕНХОРАВСМТехорас]*$", )

re_page_title_interface = re.compile(r"Интерфейс?ы?")  # (r"Интерфейс?ы? *-? *(\S+\b)")

# не забывать про `API интерфейсов. Версия 7 > Документ > Базовые интерфейсы > Интерфейс IKompasDocument > IKompasDocument - методы` для `Интерфейс IKompasDocument2D`
# и есть еще `API интерфейсов. Версия 5 > KompasObject - Интерфейс API КОМПАС > KompasObject - методы > Сервисные функции` для `ksEnableTaskAccess` и др.
re_breadcrumbs_property_or_method_endswith = re.compile(r"([cс]войств[ао]|методы?)$", re.IGNORECASE)
re_breadcrumbs_property_or_method_extra = re.compile(r"(KompasObject - методы|ksDocument2D - методы)", )

re_breadcrumbs_events = re.compile(r"([cс]обытия)$", re.IGNORECASE)
re_breadcrumbs_enum   = re.compile(r"(Константы API|Структуры параметров и константы)")

re_heading_interface     = re.compile(r"Интерфейс ?\.{0,3}$")
re_heading_example       = re.compile(r"Пример ?\.{0,3}$")
re_heading_events        = re.compile(r"Интерфейс событий ?\.{0,3}$")
re_heading_description   = re.compile(r"Описание ?(|:|\.)$")
re_heading_hierarchy     = re.compile(r"Иерархия ?(|:|\.)$")
re_heading_notes         = re.compile(r"П?римечани[яе] ?(|:|\.)$")  # нет буквы П в 'itextline_level.js"
re_heading_syntax_auto   = re.compile(r"(Синтаксис Automation ?(|:|\.)|Синтаксис ?:)$")  # Просто "Синтаксис:" - в ('ikompasdocument3d_enableundo.js', 'ikompasdocument3d_undocontainer.js')
re_heading_syntax_com    = re.compile(r"Синтаксис (C|С)OM ?(|:|\.)$")
re_heading_input_params  = re.compile(r"((В?ходные |)пара?метры|Входной параметр|Входные данные) ?(|:|\.)$", re.IGNORECASE)
re_heading_output_params = re.compile(r"(Выходн(ые|ой) параметры?) ?(|:|\.)$", re.IGNORECASE)
re_heading_return_value  = re.compile(r"(Возвращаемое значение) ?(|:|\.)$", re.IGNORECASE)

# удаление строки с двумя звёздочками (типа "Получить свойство (**)")
re_stars_in_brackets = re.compile(r"(\(\s*(\*+)\s*\))")

re_property_type = re.compile(r"^Тип данных ?: ?([^\n]+)", re.MULTILINE)
re_bool_type     = re.compile(r"\b(BOOL|TRUE|FALSE)\b", re.IGNORECASE | re.MULTILINE)
re_str_type      = re.compile(r"\b(BSTR|строка)\b", )
re_int_type      = re.compile(r"\b(long|int|short)\b", re.IGNORECASE)
re_float_type    = re.compile(r"\b(float|double)\b", re.IGNORECASE)
re_any_type      = re.compile(r"\bVARIANT\b", re.IGNORECASE)
re_None_type     = re.compile(r"\bNULL\b", re.IGNORECASE)

re_vt_type       = re.compile(r"\bVT_[A-Z0-9]+\b", )  # re.IGNORECASE)
re_vt_array_type = re.compile(r"\bVT_ARRAY *\|? *(VT_[A-Z0-9]+)\b", )  # re.IGNORECASE)

# под 'only имеется в виду, что вся строка (все содержимое ячейки таблицы) будет соответствовать этому RegExp.  # спасает от случаев ложных срабатываний на строках типа "90 градусов".
re_integer_only = re.compile(r"^([\+-]?\d+|0[xX]\d+)$")


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
    "VT_DISPATCH": CLASS_NAME_IDISPATCH,
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


def extract_subsections_hrefs(body: Tag) -> None:
    tags_to_remove: list[Tag] = []

    tags_to_remove.extend(body.find_all("p", attrs={"class": "p_Z_LOC_TOC_Title"}))
    tags_to_remove.extend(body.find_all("p", attrs={"class": "p_Z_LOC_TOC"}))

    for tag in tags_to_remove:
        tag.extract()


def extract_picture(body: Tag) -> bool:
    tags_to_remove: list[Tag] = []

    tags_to_remove.extend(body.find_all("p", attrs= { "class": "p_Picture_Title" }))

    # нельзя просто удалить div или table, который содержит img.
    # Есть случаи, где картинка помещена внутрь полезной таблицы: "ksdocument2d_ksannpoint.js"
    tags_to_remove.extend(body.find_all("img"))

    for tag in tags_to_remove:
        tag.extract()

    return len(tags_to_remove) > 0


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
        for i, cell_tag in enumerate(cell_tags):
            cell_content = render_pretty_single_line(cell_tag.get_text())  # TODO добавить поддержку многостроковых ячеек
            row.append(cell_content)
        max_column_count = max(max_column_count, len(cell_tags))

    column_widths: list[int] = [0 for i in range(max_column_count)]

    for row in table:
        for i, cell in enumerate(row):
            for line in cell.splitlines(False):
                column_widths[i] = max(column_widths[i], len(line))

    ### если пустая таблица

    if sum(column_widths) == 0:
        return ""

    ### игнорирование пустых столбцов

    ignored_indexes: list[int] = []
    for i, width in enumerate(column_widths):
        if width == 0:
            ignored_indexes.append(i)

    ### если с учетом проигнорированных столбцов осталась одна строка с одной ячейкой

    if len(table) == 1:
        rest_column_indexes = set(range(max_column_count)).difference(ignored_indexes)
        if len(rest_column_indexes) == 1:
            i = rest_column_indexes.pop()
            return f"{table[0][i]}\n"

    ### отрисовка таблицы

    string: str = ""
    s_horizontal_border: str = ""

    if do_render_horizontal_border:
        borders = vertical_borders().__iter__()
        s_table_length: int = len(next(borders))
        for i, width in enumerate(column_widths):
            if i in ignored_indexes: continue
            s_table_length += width + len(next(borders))
        s_horizontal_border = f" +{'-' * (s_table_length - 4)}+ \n"  # -2 потому что плюсы, и еще -2 потому что вокруг плюсов пробелы заменены на минусы

    string += s_horizontal_border

    for row in table:
        s_row = ""
        borders = vertical_borders().__iter__()
        s_row += next(borders)
        for i, cell in enumerate(row):
            if i in ignored_indexes: continue
            s_row += cell.ljust(column_widths[i]) + next(borders)

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
        #
        # Пусть указания о синтаксисе с двумя звездочками "(**)" останутся, так как они иногда правдивы.
        # Оказывается, в Python-модулях API бывает так, что указано свойство в _prop_map_get_ и _prop_map_put_,
        # и при этом есть еще и метод с тем же названием. Это приводит к пересечению названий при generate_stub.
        #
        # to_extract: list[Tag] = []
        # for tr_tag in table_tag.find_all("tr"):
        #     m = re_stars_in_brackets.search(tr_tag.get_text())
        #     if m is not None:
        #         if m.group(2) == "**":
        #             to_extract.append(tr_tag)
        # for tag in to_extract:
        #     tag.extract()

        output += render_table(table_tag, False, lambda: _vertical_borders_comments())
        # output = re_stars_in_brackets.subn("", output)[0]  # пусть звездочки останутся

    else:
        s_table = render_table(table_tag)
        if s_table != "":  # может быть пустой строкой, если произошел парсинг таблицы из одной строки и одной ячейки без текста, где была картинка
            output += s_table + "\n"

    return output


def parse_description_section(
        section: str,
        tags: list[Tag],
        description_data: DescriptionData,
        topic: Topic,
        do_try_parse_value_types: bool,
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


    # определение типа свойства или возвращаемого значения метода
    if do_try_parse_value_types:
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
                    logger.debug(f"_try_to_update_value_types(): найден тип данных возвращаемого значения: '{obtained_return_type}' у '{topic.own_hrefs[0]}'")
                    if description_data.return_type != "":
                        description_data.return_type += "|" + obtained_return_type
                    else:
                        description_data.return_type += obtained_return_type

        _try_to_update_value_types()

    return section_output

def parse_description(
        tag_help_body: Tag,
        topic: Topic,
        do_try_parse_value_types: bool,
        do_force_header_rendering: bool = False,
        ) -> DescriptionData:
    """
    Выполняет парсинг тела страницы
    и в конечном счете формирует python docstring (`__doc__`) - описание объекта
    (интерфейса, свойства, метода или др.).
    """
    own_href = topic.own_hrefs[0]
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

            # сделан ранее в parse_single_jstopic() путем extract_subsections_hrefs()
            # # пропуск ссылок на подразделы
            # if tag_class in ("p_Z_LOC_TOC_Title", "p_Z_LOC_TOC"):
            #     continue

            # пропуск тегов иерархии
            if tag_class.startswith("p_Hier_"):
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
    output: str = ""

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
            output += parse_description_section(section, sections[section], description_data, topic, do_try_parse_value_types)

    # ссылка на страницу Справки с примером
    s_example: str = ""
    if description_data.example_href != "":
        s_example = f"Пример в Справке: `{description_data.example_href}`\n\n"
        output = f"{s_example}{output}"

    # заголовок
    if output != "" or do_force_header_rendering:
        output = f"## {utils.render_pretty_single_line(topic.hmTitle)}\n\n{output}"

    description_data.docstring = output
    pih: str|None = parser_injections.fix_parent_interface_href(own_href)
    if pih is not None:
        description_data.parent_interface_href = pih

    return description_data



def parse_description_for_enum(body_tag: Tag, topic: Topic) -> bool:
    """ Возвращает `True`, если парсинг выполнен успешно. """
    own_href = topic.own_hrefs[0]

    table_tags = body_tag.find_all("table")

    for table_tag in table_tags:
        parent = table_tag.parent
        table_tag.extract()
        if parent is not None and parent.name == "div":
            parent.extract()

    if len(table_tags) == 0:
        logger.debug(f"parse_description_for_enum(): Предупреждение: нет таблиц у {topic}")
        return False

    # FIXME разрешается ли несколько таблиц?
    if len(table_tags) > 1:
        logger.error(f"parse_description_for_enum(): Ошибка: таблиц больше одной ({len(table_tags)} шт.) у {topic}")
        return False

    table_tag: Tag = table_tags[0]

    ### исправление таблицы
    # удаление строк, в которых есть colspan или rowspan
    cells_to_multiply: list[Tag] = []
    rows_to_remove: list[Tag] = []
    for tr_tag in table_tag.find_all("tr"):
        # if tr_tag.find(attrs={ "colspan": True }) or tr_tag.find(attrs={ "rowspan": True }):
        #     rows_to_remove.append(tr_tag)
        for td_tag in tr_tag.find_all(attrs={ "colspan": True }):
            cells_to_multiply.append(td_tag)
        if tr_tag.find(attrs={ "rowspan": True }):
            rows_to_remove.append(tr_tag)

    for td_tag in cells_to_multiply:
        try:
            count_to_add: int = int(str(td_tag.attrs.get("colspan", "1"))) - 1
        except Exception as e:
            logger.critical(f"parse_description_for_enum(): Ошибка: невозможно привести к int значение colspan в таблице у {topic}", exc_info=True)
            return False
        del td_tag.attrs["colspan"]
        while count_to_add > 0:
            td_copy = copy.deepcopy(td_tag)
            td_tag.insert_after(td_copy)
            count_to_add -= 1

    if len(rows_to_remove) > 0:
        logger.warning(f"parse_description_for_enum(): Предупреждение: таблица содержит некорректные строки (colspan, rowspan) у {topic}")
        for tag in rows_to_remove:
            tag.extract()


    ### понимание того, что где в каком столбце:
    # сначала ищется столбец с идентификатором - это имена (enum members);
    # затем - столбец с цифрами - это значения (enum values);
    # остальные столбцы - это описание
    # если есть заголовочная строка (has_header_row), то ячейки столбцов описания
    # приводятся вместе с заголовком столбца

    has_header_row: bool = parser_injections.does_enum_table_have_header_row(own_href)
    description_cells_headers: list[str] = []
    header_row_td_tags: list[Tag] = []

    # удаление первой заголовочной строки для дальнейшего парсинга строк с идентификаторами и значениями
    # и получение header_td_tags для первой строки заголовка
    if has_header_row:
        row_tag = table_tag.find("tr")
        if row_tag is None:
            logger.error(f"parse_description_for_enum(): Ошибка: не найдена заголовочная строка таблицы у {topic}")
            return False
        row_tag = row_tag.extract()
        header_row_td_tags.extend(row_tag.find_all("td"))

    name_cell_index: int = -1
    value_cell_index: int = -1
    description_indexes: list[int] = []
    name_cell_index, value_cell_index, description_indexes = parser_injections.fix_enum_table_cell_indexes(own_href)

    # получение first_data_row_td_tags для первой строки с данными
    row_tag = table_tag.find("tr")
    if row_tag is None:
        logger.error(f"parse_description_for_enum(): Ошибка: не найдена первая строка таблицы с данными (has_header_row={has_header_row}) у {topic}")
        return False
    first_data_row_td_tags = row_tag.find_all("td")

    # заполнение заголовков столбцов описания пустыми строками - пока. См. ниже.
    description_cells_headers.extend(["" for i in first_data_row_td_tags])

    # автоматический поиск столбца с идентификатором
    if name_cell_index == -1:
        for i, td_tag in enumerate(first_data_row_td_tags):
            td_text = utils.render_pretty_single_line(td_tag.get_text())
            if search_identifier(td_text, do_match = True) != "":
                name_cell_index = i
                break  # FIXME не сломает ли этот break другие enums?

        if name_cell_index == -1:
            logger.error(f"parse_description_for_enum(): Ошибка: не определен индекс столбца name_cell_index (has_header_row={has_header_row}) у {topic}")
            return False

    # автоматический поиск столбца со значением
    if value_cell_index == -1:
        for i, td_tag in enumerate(first_data_row_td_tags):
            if i == name_cell_index: continue
            td_text = utils.render_pretty_single_line(td_tag.get_text())
            if re_integer_only.match(td_text) is not None:
                value_cell_index = i
                break  # FIXME не сломает ли этот break другие enums?

        if value_cell_index == -1:
            logger.error(f"parse_description_for_enum(): Ошибка: не определен индекс столбца value_cell_index (has_header_row={has_header_row}) у {topic}")
            return False

        logger.debug(f"parse_description_for_enum(): индексы столбцов у enum: name={name_cell_index}, value={value_cell_index}, has_header_row={has_header_row} у {topic}")  # не надо в stderr

    # назначение оставшихся столбцов как столбцов описания
    if len(description_indexes) == 0:
        for i, td_tag in enumerate(first_data_row_td_tags):
            if i == name_cell_index: continue
            if i == value_cell_index: continue
            description_indexes.append(i)

    # назначение заголовков столбцов описания, если известно, что у таблицы есть заголовки в первой строке
    if has_header_row:
        for i in description_indexes:
            description_cells_headers[i] = utils.render_pretty_single_line(header_row_td_tags[i].get_text())
            if description_cells_headers[i] != "":
                description_cells_headers[i] = f"{description_cells_headers[i]}: "

    ### парсинг

    # к этому моменту из body_tag извлечены таблицы с enum members, поэтому они не попадут в docstring.
    enum_docstring = parse_description(body_tag, topic, False, True).docstring

    enum_members: list[list[str]] = []

    for j, row_tag in enumerate(table_tag.find_all("tr")):
        member_name: str = ""
        member_value: str = ""
        member_description_lines: list[str] = []

        for i, td_tag in enumerate(row_tag.find_all("td", recursive=False)):
            td_text = render_pretty_single_line(td_tag.get_text())
            if i == name_cell_index:
                member_name = td_text
            elif i == value_cell_index:
                member_value = td_text
            elif i in description_indexes:
                if td_text != "":
                    member_description_lines.append(f"{description_cells_headers[i]}{td_text}")
            else:
                pass # пропуск ячейки в этом столбце

        if member_name == "":
            logger.warning(f"parse_description_for_enum(): Предупреждение: не извлечено имя (member_name) в строке таблицы j={j}: name={repr(member_name)}, value={repr(member_value)} у {topic}")
            continue
        if member_value == "":
            logger.warning(f"parse_description_for_enum(): Предупреждение: не извлечено значение (member_value) в строке таблицы j={j}: name={repr(member_name)}, value={repr(member_value)} у {topic}")
            continue

        if not search_identifier(member_name, True):
            logger.warning(f"parse_description_for_enum(): Предупреждение: некорректный идентификатор (member_name) в строке таблицы j={j}: name={repr(member_name)}, value={repr(member_value)} у {topic}")
            continue

        member_docstring = "\n\n".join(member_description_lines)
        enum_members.append([member_name, member_value, member_docstring])

    ### применение свойств

    topic.docstring = enum_docstring
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


def parse_breadcrumbs(body: Tag) -> tuple[str, list[str]]:
    links: list[str] = []
    for a_tag in body.find_all("a", attrs={ "href": True }):
        href = utils.ensure_ext(str(a_tag.get("href", "")), ".js")
        links.append(href)
    text: str = render_pretty_single_line(body.get_text())
    return text, links


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
        jstopic.own_hrefs[0] = os.path.split(filepath)[1]
    else:
        jstopic.own_hrefs[0] = own_href

    jstopic.page_type = parser_injections.get_page_type(jstopic.own_hrefs[0])

    if jstopic.page_type == HelpPageType.Useless:
        logger.debug(f"parse_single_jstopic(): Известно, что эта страница бесполезна: '{jstopic.own_hrefs[0]}'")
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
        # breadcrumbs
        bc_body: Tag = BeautifulSoup(jstopic.hmBreadCrumbs, "lxml")  # .find("body") - не обязательно в данном случае
        jstopic.hmBreadCrumbs, jstopic.breadcrumbs_links = parse_breadcrumbs(bc_body)

        # body
        soup = BeautifulSoup(jstopic.hmBody, "lxml")
        body: Tag = soup.find("body") # type: ignore
        assert isinstance(body, Tag)

        # исправление косяков справки для некоторых известных страниц
        parser_injections.fix_body(body, jstopic.own_hrefs[0])

        # удаление ссылок на подразделы
        extract_subsections_hrefs(body)

        # удаление комментариев
        for tag in body.find_all(string=lambda text: isinstance(text, Comment)):
            tag.extract()

        # удаление таблицы с картинкой и абзаца подписи картинки
        if extract_picture(body):
            logger.debug(f"parse_single_jstopic(): убрана картинка со страницы '{own_href}'")

        ### здесь body готов для парсинга человекочитаемого description

        def _is_empty_page() -> bool:
            for s in body.stripped_strings:
                if len(s) > 0:
                    return False
            return True

        def _parse_description(do_try_parse_value_types: bool) -> bool:
            """ Возвращает `True`, если текст описания непустой """
            description_data: DescriptionData = parse_description(body, jstopic, do_try_parse_value_types)
            jstopic.docstring = description_data.docstring
            jstopic.parent_interface_href = description_data.parent_interface_href
            jstopic.example_href = description_data.example_href
            jstopic.value_types["return"] = description_data.return_type
            jstopic.value_types.update(description_data.input_parameters)
            return jstopic.docstring != ""

        ### определение типа страницы

        if jstopic.page_type == HelpPageType.Unknown:

            # страница перечня ссылок на свойства, методы, события
            if jstopic.own_hrefs[0].endswith("_props.js") \
                    or jstopic.own_hrefs[0].endswith("_methods.js") \
                    or jstopic.own_hrefs[0].endswith("_propers.js") \
                    or jstopic.own_hrefs[0].endswith("_events.js") \
                    or re_breadcrumbs_property_or_method_endswith.search(jstopic.hmTitle):
                jstopic.page_type = HelpPageType.LinkListPage
                logger.debug(f"parse_single_jstopic(): страница со ссылками. Пропуск. {jstopic}")
                return None

            # далее - определение интерфейса или метода/свойства:
            # важно помнить о случаях:
            # * в hmTitle для метода есть слово "Интерфейс": imathcurve3d_placement.js, imathsurface3d_placement.js, ireport_reportfilter.js и др.
            # * hmBreadCrumbs    заканчиваются на "- методы", но интерфейс: "IKompasDocument2D" и др.
            # * hmBreadCrumbs не_заканчиваются на "- методы", но метод: "ksEnableTaskAccess" и др.: "... KompasObject - методы > Сервисные функции"
            #
            # Решено: тип страницы "Interface" определяется перед типом "PropertyOrMethod".
            # ложное определение метода как интерфейса - путем ручных правок в parser_injections.

            # страница интерфейса
            elif re_page_title_interface.search(jstopic.hmTitle):
                jstopic.page_type = HelpPageType.Interface

            # страница метода или свойства
            elif re_breadcrumbs_property_or_method_endswith.search(jstopic.hmBreadCrumbs) \
                    or re_breadcrumbs_property_or_method_extra.search(jstopic.hmBreadCrumbs):
                jstopic.page_type = HelpPageType.PropertyOrMethod

            # страница перечисления (enum)
            elif re_breadcrumbs_enum.search(jstopic.hmBreadCrumbs):
                jstopic.page_type = HelpPageType.Enum

            # страница события
            elif re_breadcrumbs_events.search(jstopic.hmBreadCrumbs):
                jstopic.page_type = HelpPageType.Event

            # страница неизвестного типа
            else:
                pass  # ниже останется только проверить, что у нее пустое description (тогда - нормально, пропуск); иначе - предупреждение, что что-то не так


        def _print_empty_own_name():
            logger.error(f"parse_single_jstopic(): Ошибка: не извлечено own_name из hmTitle={repr(jstopic.hmTitle)} у {jstopic}")

        ### парсинг конкретного типа страницы

        # страница перечисления (enum)
        if jstopic.page_type == HelpPageType.Enum:
            jstopic.own_name = parser_injections.fix_enum_name(search_identifier(jstopic.hmTitle), jstopic.own_hrefs[0])
            if jstopic.own_name == "":
                jstopic.own_name = ENUM_UNNAMED

            if not parse_description_for_enum(body, jstopic):
                return None

            return jstopic

        # если пустая страница - пропуск
        # если непустая - этим вызовом произойдет парсинг описания для последующих случаев HelpPageType: Interface, PropertyOrMethod, Event
        # эта проверка - обязательно после парсинга страницы HelpPageType.Enum, ведь там задействуется parse_description() особым образом!
        if _is_empty_page():
            jstopic.page_type = HelpPageType.EmptyPage
            logger.debug(f"parse_single_jstopic(): страница без содержимого. Пропуск. {jstopic}")
            return None

        # страница класса интерфейса
        if jstopic.page_type == HelpPageType.Interface:
            jstopic.own_name = parser_injections.fix_interface_name(search_identifier(jstopic.hmTitle), jstopic.own_hrefs[0])
            if jstopic.own_name == "":
                _print_empty_own_name()
                return None

            _parse_description(False)

            # если после парсинга description обнаружилась ссылка на родительский интерфейс;
            # может быть, это ложное срабатывание алгоритма определения типа страницы:
            # на самом деле страница про метод, у которого в названии есть слово "Интерфейс"
            if jstopic.parent_interface_href != "" \
                    and re_breadcrumbs_property_or_method_endswith.search(jstopic.hmBreadCrumbs):
                logger.warning(f"parse_single_jstopic(): Предупреждение: тип страницы изначально определен как интерфейс, но далее будет обработан как свойство/метод: {jstopic}")
                jstopic.page_type = HelpPageType.PropertyOrMethod
                # нет return, чтобы дальше шла ветка `if jstopic.page_type == HelpPageType.PropertyOrMethod``

            # нет, это истинный интерфейс
            else:
                jstopic.hierarchy = parse_hierarchy(body, jstopic.own_name, jstopic.own_hrefs[0])
                return jstopic

        # страница метода или свойства
        if jstopic.page_type == HelpPageType.PropertyOrMethod:
            jstopic.own_name = parser_injections.fix_property_or_method_name(search_identifier(jstopic.hmTitle), jstopic.own_hrefs[0])
            if jstopic.own_name == "":
                _print_empty_own_name()
                return None

            _parse_description(True)

            # проверка на `jstopic.parent_interface_href == ""` перенесена в fix_jstopics_after_parsing().
            # Там же будет попытка поиска по breadcrumbs_links.

            return jstopic

        # страница события
        if jstopic.page_type == HelpPageType.Event:
            # logger.warning(f"parse_single_jstopic(): Предупреждение: найдена страница события. Что с этим делать? {jstopic}")
            # pass  # TODO
            return jstopic

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
    logger.info(f"Парсинг {len(filepaths)} страниц справки...")
    jstopics: list[Topic] = []

    long_processing_indication.start_processing()

    max_count = len(filepaths)
    for i, filepath in enumerate(filepaths):
        jstopic_href = os.path.split(filepath)[1]
        if long_processing_indication.check_processing():
            logger.info(f"Прогресс: {i} / {max_count} (%.1f%%)", i / max_count * 100)

        if jstopic_href in parsed_topics:
            logger.debug(f"parse_jstopics(): Парсинг уже выполнен ранее для '{jstopic_href}'. Пропуск.")
            continue

        logger.debug(f"parse_jstopics(): Парсинг '{jstopic_href}'")

        parsed_topics.add(jstopic_href)

        topic = parse_single_jstopic(filepath, own_href=jstopic_href)
        logger.debug(f"parse_jstopics(): Результат парсинга: {topic}")

        if topic is None:
            continue

        jstopics.append(topic)

    logger.info(f"Извлечено {len(jstopics)} объектов jstopic из {len(filepaths)} ссылок.")
    return jstopics


def find_non_unique_topics(jstopics: typing.Iterable[Topic], page_type_filter: int|None = None) -> dict[str, list[Topic]]:
    names_and_topics: dict[str, list[Topic]] = {}

    if page_type_filter is not None:
        jstopics = classes.filter_by_type(jstopics, page_type_filter)

    for topic in jstopics:
        if topic.own_name != "" and topic.own_name != classes.ENUM_UNNAMED:
            name = classes.get_topic_full_name(topic)
            if not name in names_and_topics:
                names_and_topics[name] = []
            names_and_topics[name].append(topic)

    return names_and_topics


def merge_docstrings(doc1: str, doc2: str) -> tuple[str, int]:
    if doc1 == "":
        return (doc2, 1)
    if doc2 == "":
        return (doc1, 0)
    index = 0 if len(doc1) >= len(doc2) else 1
    doc = doc1.rstrip() + "\n\n----------\n\n" + doc2.lstrip()
    return (doc, index)


def merge_hierarchy(hierarchy1: list[list[str]], hierarchy2: list[list[str]]) -> list[list[str]]:
    if len(hierarchy1[0]) >= len(hierarchy2[0]):
        return hierarchy1
    return hierarchy2


def merge_enum_members(members_to_stay: list[list[str]], members_to_remove: list[list[str]]) -> None:
    def _find_member(name: str) -> list[str]|None:
        for member in members_to_stay:
            n = member[0]
            if n == name:
                return member
        return None

    for r_member in members_to_remove:
        r_name, r_value, r_docstring = r_member
        s_member = _find_member(r_name)

        # если нет удаляемого member в списке остающихся members (= простое добавление)
        if s_member is None:
            members_to_stay.append(r_member.copy())

        # если удаляемый member есть в списке остающихся members (= слияние)
        else:
            s_name, s_value, s_docstring = s_member
            if r_value != s_value:
                logger.error(f"merge_enum_members(): Ошибка: для имен '{s_name}' разные значения: {repr(s_value)}, {repr(r_value)}")
                continue

            s_member[2], _ = merge_docstrings(s_docstring, r_docstring)


def find_parent_interface_href_by_breadcrumbs(breadcrumbs_links: list[str], interfaces: list[Topic]) -> Topic|None:
    i = len(breadcrumbs_links) - 1
    while i >= 0:
        href = breadcrumbs_links[i]
        parent_topic = classes.find_jstopic_by_href(href, interfaces)
        if parent_topic is not None:
            return parent_topic
        i -= 1
    return None


def fix_jstopics_after_parsing(jstopics: list[Topic]) -> None:
    """
    Метод должен вызываться после того, как выполнен парсинг для всех страниц
    Справки: `Kompas6API5`, `KompasAPI7`, `constants`.
    """
    logger.info(f"\nИсправление объектов jstopic после окончательного парсинга...")

    ### назначение имен родительских интерфейсов (parent_interface_name) для страниц свойств/методов
    # и попытка поиска родительского интерфейса через breadcrumbs_links

    interfaces: list[Topic] = classes.filter_by_type(jstopics, HelpPageType.Interface)

    found_parent_interface_count: int = 0
    for topic in jstopics:
        if topic.page_type == HelpPageType.PropertyOrMethod:
            # если нет ссылки на родительский интерфейс (очень характерно для многих методов в K6API5)
            if topic.parent_interface_href == "":
                # попытка поиска родительского интерфейса через breadcrumbs_links
                parent_topic = find_parent_interface_href_by_breadcrumbs(topic.breadcrumbs_links, interfaces)

                if parent_topic is None:
                    logger.error(f"fix_jstopics_after_parsing(): Ошибка: не найдена ссылка на родительский интерфейс через breadcrumbs_links у {topic}")
                    continue

                topic.parent_interface_href = parent_topic.own_hrefs[0]
                topic.parent_interface_name = parent_topic.own_name
                logger.debug(f"fix_jstopics_after_parsing(): Найдена ссылка на родительский интерфейс через breadcrumbs_links: {repr(topic.parent_interface_href)} у {topic}")
                found_parent_interface_count += 1

            # если уже есть ссылка на родительский интерфейс - просто назначение parent_interface_name
            else:
                parent_topic = classes.find_jstopic_by_href(topic.parent_interface_href, interfaces)
                if parent_topic is None:
                    logger.error(f"fix_jstopics_after_parsing(): Ошибка: не найден родительский интерфейс по ссылке '{topic.parent_interface_href}' для {topic}")
                    continue

                topic.parent_interface_name = parent_topic.own_name
    logger.info(f"Исправлено свойств/методов с доназначенными parent_interface_href: {found_parent_interface_count}")

    ### слияние объектов jstopics с одинаковыми именами
    # у enums, например, "DrawingObjectTypeEnum"
    # у классов, например, "ksrasterformatparam" - это "ksrasterformatparam.js", "ch1780194.js", "ck1888295.js", "ck1863757.js"
    #
    # нельзя использовать `classes.filter_by_type()`, потому что она возвращает словарь, и там классы одного типа затираются
    # обязательно после назначения `parent_interface_name`!

    names_and_topics: dict[str, list[Topic]] = find_non_unique_topics(jstopics)

    merged_enums_count: int = 0
    merged_classes_count: int = 0
    for name, topics_list in names_and_topics.items():
        topics_types = [t.page_type for t in topics_list]
        if not len(topics_list) > 1:
            continue

        if not all([topics_types[0] == tt for tt in topics_types]):
            logger.error(f"fix_jstopics_after_parsing(): Ошибка: объекты jstopic имеют разные типы, но одинаковые имена {repr(name)}: {topics_list}")
            continue

        topic = topics_list[0]  # остающийся объект. Остальные - к удалению.

        for t in topics_list:
            if t == topic: continue

            topic.own_hrefs.extend(t.own_hrefs)
            topic.docstring, biggest_doc_index = merge_docstrings(topic.docstring, t.docstring)

            if topics_types[0] == HelpPageType.Enum:
                merge_enum_members(topic.enum_members, t.enum_members)
                merged_enums_count += 1

            elif topics_types[0] == HelpPageType.Interface:
                topic.hierarchy = (topic.hierarchy, t.hierarchy)[biggest_doc_index]
                topic.example_href = (topic.example_href, t.example_href)[biggest_doc_index]
                merged_classes_count += 1

            else:
                logger.error(f"fix_jstopics_after_parsing(): Ошибка: не предусмотрено слияние объектов с page_type={HelpPageType.str_from_int(topics_types[0])} у {topic}")
                continue

            # topic.parent_interface_name =
            # topic.parent_interface_href =
            # topic.value_types =
            # topic.breadcrumbs_links =
            # topic.hmTitle =
            # topic.hmBreadCrumbs =

            jstopics.remove(t)
            logger.warning(f"fix_jstopics_after_parsing(): Предупреждение: удален объект jstopic вследствие слияния с одинаковым именем {repr(name)}: {t}, - слияние с {topic}")

    logger.info(f"Объединены перечисления (enums) с одинаковыми именами: {merged_enums_count}")
    logger.info(f"Объединены классы с одинаковыми именами: {merged_classes_count}")


    # ### проверка на уникальность наименований (справочная) после всех возможных исправлений

    # names_and_topics: dict[str, list[Topic]] = find_non_unique_topics(jstopics)

    # intersecting_names_count: int = 0
    # for name, topics_list in names_and_topics.items():
    #     if len(topics_list) > 1:
    #         for topic in topics_list:
    #             logger.error(f"fix_jstopics_after_parsing(): Ошибка: объект jstopic с повторяющимся именем '{name}': {topic}")
    #             intersecting_names_count += 1
    # logger.info(f"Исправлено объектов jstopic с повторяющимися именами: {intersecting_names_count}")


    # ### вывод объектов, у которых page_type == Unknown
    # не актуально, потому что такие вообще не возвращаются из parse_single_jstopic()

    # unknown_count = 0
    # for topic in jstopics:
    #     if topic.page_type == HelpPageType.Unknown:
    #         unknown_count += 1
    #         logger.warning(f"fix_jstopics_after_parsing(): Предупреждение: остается объект jstopic с неизвестным типом страницы: {topic}")
    # logger.info(f"Количество объектов jstopic с неизвестным типом страницы: {unknown_count}")


def load_topics(filepath: str) -> list[Topic]:
    if not os.path.exists(filepath):
        logger.error(f"load_topics(): Ошибка: файла не существует: '{filepath}'")
        return []
    l = json_utils.load_json_with_classes(filepath, [Topic])
    logger.info(f"Загружено {len(l)} объектов jstopic (страниц справки) из файла '{filepath}'.")
    return l


def get_jstopics_filepaths(toc_entry: TOCEntry) -> list[tuple[str, str]]:
    """
    Возвращает список `[ ( html_filepath, jstopics_js_filepath ), ... ]`, где
    * `html_filepath` - путь к html-файлу в корневой папке Справки SDK: `sdk_help_dir/*.html`;
    * `jstopics_js_filepath` - путь к js-файлу: `sdk_help_dir/jstopics/*.js`;
    """
    return [
        (
            os.path.join(const.get_sdk_help_dir(), toc_entry.href),
            os.path.join(const.get_jstopics_dir(), utils.ensure_ext(toc_entry.href, ".js")),
        )
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
            return toc_entries_hrefs.index(topic.own_hrefs[0])
        except ValueError:
            return 10 ** 9

    return sorted(topics, key=_key)




def main(
        do_k5: bool = True,
        do_k7: bool = True,
        do_const: bool = True,
        do_collect_statistics: bool = True,
        ) -> None:

    toc_entries: list[TOCEntry] = parse_table_of_contents.load_root_toc_entries(const.get_toc_filepath())

    filepaths: list[tuple[str, str]] = []

    if do_k7:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api7_root_topic_href, toc_entries, 1)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry))

    if do_k5:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_api5_root_topic_href, toc_entries, 1)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry))

    if do_const:
        root_toc_entry = parse_table_of_contents.get_toc_entry_from_href(const.help_constants_topic_href, toc_entries, 3)
        assert isinstance(root_toc_entry, TOCEntry)
        filepaths.extend(get_jstopics_filepaths(root_toc_entry))

    jstopics: list[Topic] = []
    jstopics.extend(parse_jstopics([fp[1] for fp in filepaths]))

    fix_jstopics_after_parsing(jstopics)

    logger.info(f"")  # пустая строка
    json_file_size: int = json_utils.save_json(const.get_topics_filepath(), jstopics)
    logger.info(f"Записано {len(jstopics)} объектов Topic в файл '{const.get_topics_filepath()}' ({statistics.render_file_size(json_file_size)})")

    if do_collect_statistics:
        html_files_size: int = statistics.measure_size([fp[0] for fp in filepaths])
        js_files_size: int = statistics.measure_size([fp[1] for fp in filepaths])
        total_size: int = html_files_size + js_files_size
        logger.info(f"Суммарный размер обработанных       js-файлов:   {statistics.render_file_size(js_files_size)}")
        logger.info(f"Суммарный размер соответствующих им html-файлов: {statistics.render_file_size(html_files_size)}")
        logger.info(f"Суммарный общий размер файлов страниц Справки:   {statistics.render_file_size(total_size)}")



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
