"""
В качестве исходных данных дается JS-код, как в примерах в main.

Задача - получить из него валидный JSON-объект и использовать его в скрипте Python.

"""


from .. import logging_system
logger = logging_system.get_logger(__name__)


import typing


JS_TO_JSON_DEBUG: bool = False


QUOTES = ("'", "\"", "`")


class JSGeneralDataType:
    Unknown = 0
    Whitespace = 1
    String = 2
    List = 3
    Dict = 4
    Parenthesis = 5
    Identifier = 6
    Number = 7


def skip_whitespace(data: str, i_start: int) -> int:
    """
    Пропускает пробелы и возвращает индекс первого non-whitespace символа.
    """
    i = i_start
    while i < len(data):
        if data[i].isspace():
            i += 1
        else:
            break
    return i


def check_for_keywords(data: str, i_start: int, keywords: list[str]) -> tuple[bool, str, int]:
    """
    Возвращает `(is_keyword_met, keyword, end_i)`:
    * `is_keyword_met: bool` - флаг о том, встретилось ли хоть одно из `keywords`;
    * `keyword: str` - какое именно слово встретилось среди `keywords`.
        Если достигнут EOF, то `keyword == ""`;
    * `end_i: int` - индекс символа, следующего сразу за `keyword`.

    В качестве `keywords`, помимо прочего, можно передать:
    * пустой список `[]`;
    * один символ `[","]`;
    """
    for keyword in keywords:
        keyword_length: int = len(keyword)
        i: int = i_start
        keyword_i: int = 0
        while i < len(data):
            if keyword[keyword_i] != data[i]:
                break
            i += 1
            keyword_i += 1
            if keyword_i == keyword_length:
                return (True, keyword, i)
    return (False, "", i_start)


def ensure_quotes(text: str, quote: str = "\"") -> str:
    if len(text) == 0:
        raise Exception(f"empty argument for ensure_quotes()")
    if text[0] == quote: # and text[-1] == quote:
        return text
    if text[0] in QUOTES:
        return quote + text[1:-1].replace(quote, "\\" + quote) + quote
    return quote + text.replace(quote, "\\" + quote) + quote


def js_to_json_string(data: str, starting_quote_i: int) -> tuple[str, int]:
    """
    Возвращает `(string, i_end)`:
    * `string: str` - содержимое от `starting_quote_i` (включительно) до соответствующей закрывающей кавычки (включительно);
    * `i_end: int` - индекс символа, следующего сразу за `ending_quote`.

    `starting_quote_i` - это индекс открывающей кавычки.
    """
    quote_symbol: str = data[starting_quote_i]
    is_escaped: bool = False

    output: str = quote_symbol

    i: int = starting_quote_i + 1
    while i < len(data):
        letter = data[i]

        if not is_escaped and letter == "\\":  # символ экранирования
            is_escaped = True
            i += 1
            continue  # `output += letter` не_нужно здесь; запоминается, что следующий символ экранирован; слэш будет добавлен только если разрешен (JSON valid escape)

        else:  # любой другой символ кроме обратного слэша
            if is_escaped:  # экранированный символ строки
                is_escaped = False

                if letter in (quote_symbol, "\\", "n", "r", "b", "t", "/", "f", "u"):  # разрешенный (valid) escape character
                    # JSON: "\uXXXX" is valid
                    output += "\\"

                else:  # invalid escape character
                    # удаление экранированных символов обычного JS, которые в JSON недопустимы: \$, \' --- из-за этого ругается json decoder (invalid escape)
                    # < слэш экранирования не_добавляется! >
                    pass

            else:  # неэкранированный символ строки
                if letter == quote_symbol:  # строка заканчивается
                    output += letter
                    i += 1
                    break

                else:  # строка продолжается
                    # < просто добавляется символ в строку >
                    pass
        output += letter
        i += 1

    else:
        raise Exception(f"Syntax error on i={i}: reached EOF when searching for string ending quote {repr(quote_symbol)}")
    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_string(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_dict(
        data: str,
        starting_bracket_i: int,
        key_callback: typing.Callable[[str], str],
        value_callback: typing.Callable[[str], str],
        ) -> tuple[str, int]:
    """
    Возвращает `(dict, end_i)`:
    * `dict: str` - содержимое от `starting_bracket_i` (включительно) до закрывающей фигурной скобки `}` (включительно);
    * `end_i: int` - индекс символа, следующего сразу за закрывающей фигурной скобкой `}`.
    """
    output: str = data[starting_bracket_i]
    i: int = starting_bracket_i + 1
    key: str = ""
    value: str = ""
    had_previous_pair: bool = False

    while i < len(data):
        # key

        key, data_type, ending_keyword, i = js_to_json_general(data, i, [":", "}"])  # закрывающая скобка валидна, если она после запятой

        if ending_keyword == "":
            raise Exception(f"Syntax error on i={i}: reached EOF when searching for dict key")

        if ending_keyword == "}":
            if key == "":
                output += ending_keyword
                break  # словарь закончился
            else:
                raise Exception(f"Syntax error on i={i}: dict closed with non-empty key provided (unexpected '}}')")

        if key == "":
            raise Exception(f"Syntax error on i={i}: empty key (unexpected ':')")

        if had_previous_pair:  # исключает пустую запятую в самом конце перед закрывающей скобкой
            output += ","

        output += key_callback(key)
        output += ":"

        # value

        value, data_type, ending_keyword, i = js_to_json_general(data, i, [",", "}"])

        if ending_keyword == "":
            raise Exception(f"Syntax error on i={i}: reached EOF when searching for dict value")

        if value == "":
            raise Exception(f"Syntax error on i={i}: empty value provided after key '{key}' (unexpected {ending_keyword})")

        output += value_callback(value)

        had_previous_pair = True

        if ending_keyword == "}":
            output += ending_keyword
            break  # словарь закончился

    else:
        raise Exception(f"Syntax error on i={i}: reached EOF when searching for dict entries")

    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_dict(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_list(
        data: str,
        starting_bracket_i: int,
        item_callback: typing.Callable[[str], str],
        ) -> tuple[str, int]:
    """
    Возвращает `(s_list, end_i)`:
    * `s_list: str` - содержимое от `starting_bracket_i` (включительно) до закрывающей квадратной скобки `]` (включительно);
    * `end_i: int` - индекс символа, следующего сразу за закрывающей квадратной скобкой `]`.
    """
    output: str = data[starting_bracket_i]
    i = starting_bracket_i + 1
    had_previous_item: bool = False
    while i < len(data):
        item, data_type, ending_keyword, i = js_to_json_general(data, i, [",", "]"])

        if ending_keyword == "":
            raise Exception(f"Syntax error on i={i}: reached EOF when searching for list entries")

        if ending_keyword == "]" and item == "":
            output += ']'
            break  # список закончился после запятой

        if item == "":
            raise Exception("Syntax error on i={i}: empty list item provided (unexpected ',')")

        if had_previous_item:  # исключает пустую запятую в самом конце перед закрывающей скобкой
            output += ","

        output += item_callback(item)
        had_previous_item = True

        if ending_keyword == "]":
            output += ending_keyword
            break

    else:
        raise Exception(f"Syntax error on i={i}: reached EOF when searching for list entries")

    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_list(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_identifier(data: str, i_start: int) -> tuple[str, int]:
    """
    Возвращает `(identifier_name, end_i)`:
    * `identifier_name: str` - содержимое от `i_start` (включительно) до первого постороннего символа (невключительно);
    * `end_i: int` - индекс первого постороннего символа.

    Под посторонним символом имеется в виду символ, который не может быть частью идентификатора.
    """
    output: str = data[i_start]

    i: int = i_start + 1
    while i < len(data):
        letter = data[i]
        if letter.isalpha() or letter.isdecimal() or letter == "_":
            output += letter
        else:
            break
        i += 1
    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_identifier(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_number(data: str, i_start: int) -> tuple[str, int]:
    """
    Возвращает `(number_str, end_i)`:
    * `number_str: str` - содержимое от `i_start` (включительно) до первого постороннего символа (невключительно);
    * `end_i: int` - индекс первого постороннего символа.

    Под посторонним символом имеется в виду символ, который не может быть частью числа.
    """
    output: str = data[i_start]

    i: int = i_start + 1
    while i < len(data):
        letter = data[i]

        # if letter == "e": # TODO

        if letter.isdecimal() or letter == ".":
            output += letter
        else:
            break
        i += 1
    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_identifier(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_parenthesis(data: str, i_start: int) -> tuple[str, int]:
    """
    Возвращает `(contents, end_i)`:
    * `contents: str` - содержимое от `i_start` (включительно) до закрывающей скобки `)` (включительно);
    * `end_i: int` - индекс символа, следующего сразу за закрывающей скобкой `)`.
    """
    output: str = data[i_start]

    # TODO сделать возможность разделителей по запятой.

    i: int = i_start + 1
    # while i < len(data):
    output, data_type, ending_keyword, i = js_to_json_general(data, i, [")"])
    if ending_keyword == "":
        raise Exception(f"Syntax error on i={i}: reached EOF when searching for parenthesis contents")

    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_parenthesis(): i={i}, output={repr(output)}")
    return (output, i)


def js_to_json_general(data: str, i_start: int, ending_keywords: list[str]) -> tuple[str, int, str, int]:
    """
    Возвращает `(general_data, general_data_type, ending_keyword, end_i)`:
    * `general_data: str` - содержимое от `i_start` (включительно) до одного из `ending_keywords` (невключительно);
    * `general_data_type: int` - тип `general_data` (см. `JSGeneralDataType`);
    * `ending_keyword: str` - какое именно слово встретилось среди `ending_keywords`.
        Если достигнут EOF, то `ending_keyword == ""`;
    * `end_i: int` - индекс символа, следующего сразу за `ending_keyword`.

    См. также `check_for_ending_keywords()`.
    """
    output: str = ""
    i: int = i_start
    ending_keyword: str = ""
    general_data_type: int = JSGeneralDataType.Unknown
    found_something: bool = False

    while i < len(data):

        if len(ending_keywords) > 0:
            is_ending_keyword_met, ending_keyword, i = check_for_keywords(data, i, ending_keywords)
            if is_ending_keyword_met:
                break
        else:
            if found_something:
                break

        found_something = True

        letter = data[i]

        if letter.isspace():  # пустые пробелы должны пропускаться
            i = skip_whitespace(data, i)
            general_data_type = JSGeneralDataType.Whitespace
            found_something = False
            continue

        if letter in QUOTES:  # сейчас нет режима строки, начинается строка
            string, i = js_to_json_string(data, i)
            output += string
            general_data_type = JSGeneralDataType.String
            continue

        if letter == "[":
            s_list, i = js_to_json_list(data, i, lambda item: item)
            output += s_list
            general_data_type = JSGeneralDataType.List
            continue

        if letter == "{":
            s_dict, i = js_to_json_dict(data, i, ensure_quotes, lambda item: ensure_quotes(item) if item[0] in QUOTES else item)
            output += s_dict
            general_data_type = JSGeneralDataType.Dict
            continue

        if letter == "(":
            parenthesis_contents, i = js_to_json_parenthesis(data, i)
            output += parenthesis_contents
            general_data_type = JSGeneralDataType.Parenthesis
            continue


        if letter.isalpha() or letter == "_":
            s_identifier, i = js_to_json_identifier(data, i)
            output += s_identifier
            general_data_type = JSGeneralDataType.Identifier
            continue

        if letter.isdecimal() or letter == "-" or letter == "+":
            s_number, i = js_to_json_number(data, i)
            output += s_number
            general_data_type = JSGeneralDataType.Number
            continue


        if letter in ("]", "}", ")", ","):
            raise Exception(f"Syntax error on i={i}: unexpected symbol {repr(letter)}")

        raise Exception(f"Parser NotImplemented error on i={i}: unknown symbol {repr(letter)}")


        # i += 1

    if JS_TO_JSON_DEBUG: logger.debug(f"js_to_json_general(): i={i}, output={repr(output)}")
    return (output, general_data_type, ending_keyword, i)







if __name__ == "__main__":

    def _fix_js_object_to_json(data: str) -> str:
        """
        Главные идеи:
        * удаление экранированных символов обычного JS, которые в JSON недопустимы --- из-за этого ругается json decoder (invalid escape);
        * заключение свойств в двойные кавычки;
        """
        output: str = js_to_json_general(data, 0, [])[0]
        return output

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

    text = r"""hmLoadTopic({
        hmKeywords:"",
        hmTitle:"Интерфейс ksProcess2DNotify\\IProcess2DNotify",
        hmDescription:"Интерфейс событий для процесса 2D. Иерархия: IDispatch ksProcess2DNotify События позволяют контролировать события процесса 2D. Источником событий для подписки на данный интерф",
        hmPrevLink:"ksplmobjectnotify_plmstatuschanged.html",
        hmNextLink:"ksprocess2dnotify_events.html",
        hmParentLink:"sobutiy.html",
        hmBreadCrumbs:"<a href=\"applicate.html\">API интерфейсов. Версия 7<\/a> &gt; <a href=\"sobutiy.html\">Интерфейсы событий&nbsp;<\/a>",
        hmTitlePath:"API интерфейсов. Версия 7 > Интерфейсы событий  > Интерфейс ksProcess2DNotify\\IProcess2DNotify ",
        hmHeader:"<h1 class=\"p_Heading1\"><span class=\"f_Heading1\">Интерфейс ksProcess2DNotify\\IProcess2DNotify <\/span><\/h1>\n\r",
        hmBody:"<p class=\"p_bodytext\"><span class=\"f_bodytext\" style=\"font-weight: bold;\">Интерфейс событий для процесса 2D<\/span><span class=\"f_bodytext\">.<\/span><\/p>\n\r<p class=\"p_bodytext\"><span class=\"f_bodytext\" style=\"font-weight: bold;\">Иерархия<\/span><span class=\"f_bodytext\">:<\/span><\/p>\n\r<p class=\"p_Hier_0_BLANK\"><span class=\"f_Hier_0_BLANK\">IDispatch<\/span><\/p>\n\r<p class=\"p_Hier_1_BLUE\"><span class=\"f_Hier_1_BLUE\"><a href=\"ksprocess2dnotify.html\" class=\"topiclink\">ksProcess2DNotify<\/a><\/span><\/p>\n\r<p class=\"p_bodytext\"><span class=\"f_bodytext\">События позволяют контролировать события процесса 2D.<\/span><\/p>\n\r<p class=\"p_bodytext\"><span class=\"f_bodytext\">Источником событий для подписки на данный интерфейс является:<\/span><\/p>\n\r<p class=\"p_bodytext\"><span class=\"f_bodytext\" style=\"text-decoration: underline;\"><a href=\"iprocess2d.html\" class=\"topiclink\">IProcess2D <\/a><\/span><span class=\"f_bodytext\">- интерфейс процесса 2D.<\/span><\/p>\n\r<p class=\"p_Z_LOC_TOC_Title\" style=\"border-top: none; border-right: none; border-left: none;\"><span class=\"f_Z_LOC_TOC_Title\">Подразделы:<\/span><\/p>\n\r<p class=\"p_Z_LOC_TOC\"><span class=\"f_Z_LOC_TOC\"><a href=\"ksprocess2dnotify_events.html\" class=\"topiclink hmlinklistitem\">События <\/a><\/span><\/p>\n\r"
        })
    """

    text = r"""hmLoadTOC({items:[{tp:"topiclink",bs:0,lv:1,cp:"SDK КОМПАС-3D ",hf:"index.html",ac:"",tr:"",i0:".\/images\/toc_topic.svg",i1:".\/images\/",md:"",mi:"",rf:null,items:[]},{tp:"topiclink",bs:1,lv:1,cp:"Новые возможности в API КОМПАС-3D v22 по сравнению с предыдущими версиями КОМПАС ",hf:"new_api.html",ac:"",tr:"",i0:".\/images\/toc_chapter_closed.svg",i1:".\/images\/toc_chapter_open.svg",md:"",mi:"",rf:null,items:[{tp:"topiclink",bs:52,lv:5,cp:"LibGetDisableReason - Причина недоступности команды ",hf:"libgetdisablereason.html",ac:"",tr:"",i0:".\/images\/toc_topic.svg",i1:".\/images\/",md:"",mi:"",rf:null,items:[]},{tp:"topiclink",bs:53,lv:5,cp:"LibGetDisableReasonW - Причина недоступности команды. Unicode ",hf:"libgetdisablereasonw.html",ac:"",tr:"",i0:".\/images\/toc_topic.svg",i1:".\/images\/",md:"",mi:"",rf:null,items:[]}]}]})"""

    text = _find_js_object(text)


    # заведомо с ошибками
    # text = r"""{items:[   {tp:"topiclink",bs:0,lv:1,cp:"SDK КОМПАС-3D ",hf:"index.html",ac:"",tr:"",i0:".\/images\/toc_topic.svg",i1:".\/images\/",md:"",mi:"",rf:null,items:[]},{tp:"topiclink",bs:1,lv:1,cp:"Новые возможности в API КОМПАС-3D v22 по сравнению с предыдущими версиями КОМПАС ",hf:"new_api.html",ac:"",tr:"",i0:".\/images\/toc_chapter_closed.svg",i1:".\/images\/toc_chapter_open.svg",md:"",mi:"",rf:null,items:[{tp:"topiclink",bs:2,lv:2,cp:"Новые интерфейсы в API КОМПАС-3D v22 ",hf:"new_intrfs_v22.html",ac:"",tr:"",i0:".\/images\/toc_topic.svg",i1:".\/images\/",md:"",mi:"",rf:null,items:[]},{tp:"topiclink",bs:3,lv:2"""


    output = _fix_js_object_to_json(text)

    print(f"\noutput='''{output}'''\n")

    import json

    print(f"json.loads() and json.dumps():\n{json.dumps(json.loads(output), ensure_ascii=False, indent=2)}")
