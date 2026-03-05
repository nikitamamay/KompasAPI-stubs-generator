import typing

from .utils import json_utils
from .utils import utils


DO_USE_LOWERCASE_NAMES: bool = True

ANY_TYPE_NAME = "ANY_TYPE"
ENUM_UNNAMED = "ENUM_UNNAMED"

CLASS_NAME_IDispatch = "IDispatch"


class HelpPageType:
    Unknown = 0
    Interface = 1
    LinkListPage = 2
    PropertyOrMethod = 4
    Enum = 8
    EmptyPage = 16

    @staticmethod
    def str_from_int(value: int) -> str:
        if value == 1: return "Interface"
        if value == 2: return "LinkListPage"
        if value == 4: return "PropertyOrMethod"
        if value == 8: return "Enum"
        if value == 16: return "EmptyPage"
        return "Unknown"


class Topic(json_utils.JSONable):
    """
    Представляет собой страницу Справки Компас SDK.
    """
    def __init__(self) -> None:
        self.own_href: str = ""
        """ Ссылка на страницу. Должна иметь расширение `.js`. """
        self.own_name: str = ""
        """ Имя интерфейса, метода или свойства, которое описывается этой страницей. """
        self.page_type: int = HelpPageType.Unknown
        """ Тип этой страницы справки. """
        self.hierarchy: list[list[str]] = [[], []]
        """
        Иерархия класса интерфейса: `[direct_base_classes, hierarchy_add]`.
        * `direct_base_classes: list[str]` - список названий **прямых** родителей класса интерфейса;
        * `hierarchy_add: list[str]` - список названий чего-то непонятного... видимо, это список дополнительных интерфейсов, которые можно получить через `QueryInterface()`. *Но это неточно: в справке эти дополнительные интерфейсы обычно пишутся просто в тексте примечаний, и не все из них попадают в `hierarchy_add`.*
        """
        self.parent_interface_name: str = ""
        """ Имя класса интерфейса, к которому принадлежит свойство или метод, описываемый этой страницей. """
        self.parent_interface_href: str = ""
        """ Ссылка на страницу интерфейса, к которому принадлежит свойство или метод, который описывает эта страница. Должна иметь расширение `.js`. """
        self.example_href: str = ""
        """ Ссылка на страницу с примером. """
        self.value_types: dict[str, str] = {}
        """
        Типы данных:
        * для методов: `{ название_параметра: тип, ..., "return": тип_возвращаемого_значения }`;
        * для свойств: `{ "return": тип_свойства }` (как будто возвращаемое значение `getter()`);
        """
        self.docstring: str = ""
        """ Описание в pyi-совместимом виде. """
        self.enum_members: list[list[str]] = []
        """ Члены перечисления в виде `[ [name, value, member_docstring], ... ]` """

        self.hmTitle: str = ""
        """ Заголовок страницы. """
        self.hmBreadCrumbs: str = ""
        """ "Хлебные крошки", то есть путь к этой странице в Справке. """

        self.hmDescription: str = ""
        self.hmKeywords: str = ""
        self.hmPrevLink: str = ""
        self.hmNextLink: str = ""
        self.hmParentLink: str = ""
        self.hmTitlePath: str = ""
        self.hmHeader: str = ""
        self.hmBody: str = ""

    def to_json(self) -> dict:
        d = self.to_json_base()
        v = vars(self).copy()
        for key in v:
            if not key in (
                    # "hmTitle",
                    "hmKeywords",
                    # "hmDescription",
                    "hmPrevLink",
                    "hmNextLink",
                    "hmParentLink",
                    # "hmBreadCrumbs",
                    "hmTitlePath",
                    "hmHeader",
                    "hmBody",

                    "subsections_hrefs"
                    ):
                d[key] = v[key]
        return d

    def __repr__(self) -> str:
        s_own_name = f"own_name={repr(self.own_name)}, " if self.own_name != "" else ""
        s_parent_name = repr(self.parent_interface_name) if self.parent_interface_name != "" else repr(self.parent_interface_href)
        s_parent = f"parent_interface={s_parent_name}, " \
            if s_parent_name != "" else ""
        return f"<Topic own_href={repr(self.own_href)}, {s_own_name}{s_parent}page_type={HelpPageType.str_from_int(self.page_type)}>"

    __str__ = __repr__



class TOCEntry(json_utils.JSONable):
    def __init__(self) -> None:
        self.title: str = ""  # cp
        self.href: str = ""  # hf
        self.children: list[TOCEntry] = []  # items



class PythonEntry(json_utils.JSONable):
    def __init__(self) -> None:
        self.name: str = ""
        self.doc: str = ""
        self.href: str = ""

class PythonClass(PythonEntry):
    def __init__(self) -> None:
        super().__init__()
        self.base_classes: list[str] = []
        self.children: list[PythonEntry] = []

class PythonFunction(PythonEntry):
    def __init__(self) -> None:
        super().__init__()
        self.return_type: str = ""
        self.parameters: list[str] = []

class PythonVariable(PythonEntry):
    def __init__(self) -> None:
        super().__init__()
        self.value_type: str = ""
        self.value: str = "..."

class PythonProperty(PythonVariable):
    def __init__(self) -> None:
        super().__init__()
        self.has_getter: bool = False
        self.has_setter: bool = False


class DescriptionSection():
    PlainDescription = "Описание"
    Hierarchy = "Иерархия"
    Notes = "Примечания"
    SyntaxAutomation = "Синтаксис Automation"
    SyntaxCOM = "Синтаксис COM"
    InputParameters = "Входные параметры"
    OutputParameters = "Выходные параметры"
    # PropertyValues = "Значения свойства"
    ReturnValue = "Возвращаемое значение"




def get_topic_full_name(topic: Topic) -> str:
    name = topic.own_name
    if topic.parent_interface_name != "":
        name = f"{topic.parent_interface_name}.{name}"
    return name.lower() if DO_USE_LOWERCASE_NAMES else name

def get_py_entry_full_name(entry: PythonEntry|str, parent: PythonEntry|str|None) -> str:
    if isinstance(entry, PythonEntry):
        name = entry.name
    else:
        name = entry

    if parent is not None:
        parent_name = get_py_entry_full_name(parent, None)
        name = f"{parent_name}.{name}"

    return name.lower() if DO_USE_LOWERCASE_NAMES else name



def filter_by_type(list_jstopics: typing.Iterable[Topic], page_type: int) -> dict[str, Topic]:
    """
    Возвращает `{ "topic.own_name": <Topic>, ... }`.
    """
    interfaces: dict[str, Topic] = {}
    for topic in list_jstopics:
        if topic.page_type == page_type:
            name = get_topic_full_name(topic)
            interfaces[name] = topic
    return interfaces


def find_jstopic_by_href(
        href: str,
        jstopics: list[Topic],
        ) -> Topic|None:
    href = utils.ensure_ext(href, ".js")
    for topic in jstopics:
        if topic.own_href == href:
            return topic
    return None


def sort_py_entries(
        py_entries: typing.Iterable[PythonEntry],
        recommended_order: list[str],
        ) -> list[PythonEntry]:
    recommended_order = [s.lower() for s in recommended_order]

    def _key(entry: PythonEntry) -> int:
        try:
            return recommended_order.index(entry.name.lower())
        except ValueError:
            return 10 ** 9

    return sorted(py_entries, key=_key)

