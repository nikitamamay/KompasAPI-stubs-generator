
from .. import logging_system
logger = logging_system.get_logger(__name__)

import sys
import os
import typing

from . import js_to_json

import re
import datetime


PYTHON_TAB = "    "


re_multispace = re.compile(r"\s+", re.MULTILINE)


def indent_lines(
        text: str,
        indent: str="\t",
        ) -> str:
    return "".join([
        indent + line
        for line in text.splitlines(True)
    ])

def indent(text: str) -> str:
    return indent_lines(text, PYTHON_TAB)



def render_pretty_single_line(text: str) -> str:
    return re_multispace.subn(" ", text)[0].strip()


def escape_in_python_docstring(text: str) -> str:
    return text.strip().replace("\\", "\\\\").replace("\"\"\"", "\\\"\\\"\\\"")

def render_docstring(text: str) -> str:
    text = escape_in_python_docstring(text.strip())
    if text == "":
        return ""
    if "\n" in text:
        return f'"""\n{text}\n"""'
    return f'""" {text} """'



def parse_safe_int(text: str, allow_signs: bool = True) -> int:
    int_started = False
    value: int = 0
    for letter in text:
        if letter.isdigit() or (allow_signs and (letter == "-" or letter == "+")):
            int_started = True
            value += value * 10 + int(letter)
        elif int_started:
            break
    return value

def get_now_datetime_str() -> str:
    return datetime.datetime.now().isoformat(' ', 'seconds')


def fix_js_object_to_json(data: str) -> str:
    """
    Главные идеи:
    * найти и использовать далее самые большие фигурные скобки `{ }`
        (объект в JS/JSON нотации);
    * удаление экранированных символов обычного JS (`\\'`, `\\$`), которые в JSON недопустимы --- из-за этого ругается json decoder (invalid escape);
    * заключение свойств в двойные кавычки;
    """
    def _find_js_object(data: str) -> str:
        """
        Главная идея - найти самые большие фигурные скобки `{ }`
        (предполагается, что они в файле одни единственные)
        и вернуть их содержимое **вместе** с фигурными скобками.
        """
        i_start = data.find("{")
        i_end = data.rfind("}")
        if i_start == -1 or i_end == -1:
            raise Exception(f"Не найдены фигурные скобки")

        return data[i_start : i_end + 1]
    data = _find_js_object(data)
    output: str = js_to_json.js_to_json_general(data, 0, [])[0]
    return output


def ensure_ext(filepath: str, ext: str) -> str:
    """
    Возвращает путь к файлу с расширением `ext`.

    Если действительное расширение файла `filepath` другое,
    то меняет его на `ext`.

    Расширение должно быть записано с точкой, например: `.html`!
    """
    basename, existing_ext = os.path.splitext(filepath)
    if existing_ext == ext:
        return filepath
    else:
        return basename + ext


def import_python_module_by_filepath(filepath: str):
    """
    Загружает python-модуль по пути `filepath` и возвращает объект этого модуля.

    Актуально для загрузки ранее сгенерированного `KompasAPIclassesHierarchy.py`,
    который находится в другой папке (не в пределах проекта).
    """
    dirpath, module_name = os.path.split(os.path.abspath(filepath))
    module_name = os.path.splitext(module_name)[0]

    old_path = sys.path.copy()
    sys.path = [dirpath]
    module = __import__(module_name, globals(), locals())
    sys.path = old_path
    return module


def write_python_module(filepath: str, content: str) -> int:
    content = "\n".join([
        line.rstrip()
        for line in content.strip().splitlines(False)
    ])
    size: int = 0

    with open(filepath, "w", encoding="utf-8") as f:
        size += f.write(
            f"#\n" \
            f"# File '{os.path.split(os.path.abspath(filepath))[1]}'\n" \
            f"# is generated automatically on {get_now_datetime_str()}\n" \
            f"# by 'https://github.com/nikitamamay/KompasAPI-stubs-generator'\n" \
            f"#\n" \
            f"\n" \
            f"\n" \
            f"{content}\n" \
        )
    logger.info(f"Python-код записан в '{filepath}' ({size} bytes).")
    return size


def ensure_latin(text: str) -> str:
    cyryl = "КЕНХОРАВСМТехорас"
    latin = "KEHXOPABCMTexopac"

    for i in range(len(cyryl)):
        text = text.replace(cyryl[i], latin[i])

    return text


def render_hrefs(hrefs: list[str], as_comment: bool) -> str:
    if len(hrefs) == 0 or hrefs[0] == "":
        return ""
    s_hrefs = ", ".join([ensure_ext(h, ".html") for h in hrefs])
    if as_comment and s_hrefs != "":
        return f"  # {s_hrefs}"
    return s_hrefs
