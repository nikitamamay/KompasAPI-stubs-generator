"""
Содержит функции ("инъекции") для исправления некоторых страниц Справки SDK Компас.

"""


from . import logging_system
logger = logging_system.get_logger(__name__)

import sys

from bs4 import BeautifulSoup, Tag, Comment
from bs4.element import NavigableString, PageElement

from .classes import HelpPageType, DescriptionSection
from .classes import CLASS_NAME_IDispatch





def fix_body(body: Tag, jstopic_own_href: str) -> None:
    # def _add_parent_href(body: Tag, parent_href: str) -> None:
    #     t = Tag(name="p", attrs={"class": "p_bodytext"})
    #     a = Tag(name="a", attrs={"href": parent_href})
    #     a.string = "Интерфейс..."
    #     body.append(t)
    #     t.append(a)

    def _fix_SyntaxCOM_wrap(body: Tag, syntaxCOM_text: str) -> None:
        bad_span = body.find("span", string="Синтаксис COM")  # type: ignore
        assert isinstance(bad_span, Tag)
        p1 = Tag(name="p", attrs={"class": "p_bodytext"})
        span1 = bad_span.copy_self()  # чтобы сохранить "font-weight: bold"
        span1.string = "Синтаксис COM"
        p1.append(span1)
        p2 = Tag(name="p", attrs={"class": "p_bodytext"})
        p2.string = syntaxCOM_text
        bad_span.parent.replace_with(p1)  # type: ignore
        p1.insert_before(p2)


    if jstopic_own_href == "ispline3dsmoothingparams.js":  # обычный текст влеплен внутрь p_Hier_0_BLANK (должен быть класс p_bodytext)
        last_pHier_tag: Tag = body.find_all("p", attrs={"class": "p_Hier_0_BLANK"})[-1]
        last_pHier_tag.attrs["class"] = "p_bodytext"

    if jstopic_own_href == "imateinterval.js":  # есть бессмысленный пустой p_Hier_0_BLANK в конце body
        last_pHier_tag: Tag = body.find_all("p", attrs={"class": "p_Hier_0_BLANK"})[-1]
        last_pHier_tag.extract()


    if jstopic_own_href == "icomponentpositioner7_initplanebyplacement.js":  # нет переноса после заголовка "Синтаксис COM"
        _fix_SyntaxCOM_wrap(body, "HRESULT InitPlaneByPlacement( IPlacement3D * Placement, BOOL * Result );")

    if jstopic_own_href == "isketch_usersetplacement.js":  # нет переноса после заголовка "Синтаксис COM"
        _fix_SyntaxCOM_wrap(body, "HRESULT UserSetPlacement( BSTR Prompt, BOOL * Result );")


    # TODO: kompasobject_getdynamicarray.js


    # страницы констант

    if jstopic_own_href in ( # удаление первой строки заголовка таблицы, состоящего из двух строк
            "ksarrowenum.js",
            ):
        body.find("table").find("tr").extract()   # type: ignore

    if jstopic_own_href == "ksconstrainttypeenum.js":  # написана русская 'к'
        body.find("td").string = "ksCUnknown"   # type: ignore

    if jstopic_own_href == "paramtype.js":  # какой-то артефакт в последней строке таблицы: "0x08 //>0"
        body.find_all("td")[-2].string = "0x08"


def get_page_type(own_href: str) -> int:
    if own_href in (
            "ksspcstyleparam_gettuning.js",
            ):
        return HelpPageType.PropertyOrMethod

    if own_href in (
            "idrawingobjects.js",  # страница интерфейса, но в заглавии нет слова "Интерфейс "
            "ksribdefinition.js",  # страница интерфейса, но в заглавии нет слова "Интерфейс "
            # "ikompasdocument2d.js",       # находятся внутри раздела "- методы"
            # "ikompasdocument3d.js",       # находятся внутри раздела "- методы"
            # "itextdocument.js",           # находятся внутри раздела "- методы"
            # "ispecificationdocument.js",  # находятся внутри раздела "- методы"
            ):
        return HelpPageType.Interface

    if own_href in (
            "iapplication_events.js",  # страница с перенаправлениями
            "bb2327204.js",  # страница с перенаправлениями
            "cj1798939.js",  # страница с перенаправлениями
            ):
        return HelpPageType.Useless

    return HelpPageType.Unknown


def fix_parent_interface_href(own_href: str) -> str|None:
    # должно найти через breadcrumbs:
        # if parent_interface_href == "propertymanagernotify.js":
        #     return "kspropertymanagernotify.js"

        # if jstopic_own_href == "ireport_stylescount.js":  # отсутствует ссылка на родительский интерфейс
        #     _add_parent_href(body, "ireport.html")  # измени на .js

        # if jstopic_own_href == "iembodiment_part.js":  # отсутствует ссылка на родительский интерфейс
        #     _add_parent_href(body, "iembodiment.html")  # измени на .js

        # if jstopic_own_href == "ispecificationobject_additionalcolumns.js":  # отсутствует ссылка на родительский интерфейс
        #     _add_parent_href(body, "ispecificationobject.html")  # измени на .js

    if own_href == "ikompasdocument2d1_libprocess.js":  # parent_interface_href дана неверная
        return "ikompasdocument2d1.js"

    if own_href in (  # даны parent_interface_href для "IModelObject"
            'idiametraldimension3d_getcenterpoint.js',
            'idiametraldimension3d_getsurfacepoint.js',
            'idiametraldimension3d_setcenterpoint.js',
            'idiametraldimension3d_setsurfacepoint.js',
            ):
        return "idiametraldimension3d.js"

    if own_href in ( # даны parent_interface_href для "IModelObject"
            'iradialdimension3d_getcenterpoint.js',
            'iradialdimension3d_getsurfacepoint.js',
            'iradialdimension3d_setcenterpoint.js',
            'iradialdimension3d_setsurfacepoint.js',
            ):
        return "iradialdimension3d.js"

    return None


def fix_interface_name(text: str, own_href: str = "") -> str:
    """
    Возвращает исправленное название интерфейса, которое получено путем парсинга
    заголовка страницы Справки SDK Компас.
    """
    if text == "IСonverter":  # русская С в названии
        return "IConverter"

    if text == "AngleDimensions":  # пропущена буква I
        return "IAngleDimensions"

    if own_href == "ksobject2dnotifyresult.js":  # "Интерфейс результатов редактирования объекта (Интерфейс ksObject2DNotifyResult, IObject2DNotifyResult)"
        return "ksObject2DNotifyResult"

    if text.startswith("IProcess3DManipulatorsNotify"):
        return "ksProcess3DManipulatorsNotify"

    if own_href == "idrawingobjects.js":
        return "IDrawingObjects"

    if own_href == "izonedivision.js":
        return "IZoneDivision"

    if text.startswith("ks") and "otify" in text:  # `ks...Notify` - это один из интерфейсов событий
        i = text.find("/")
        if i == -1:
            i = text.find("\\")

        if i != -1:
            return text[:i]

    if not text.isidentifier() or not text.isascii():
        logger.warning(f"fix_interface_name(): Предупреждение: сомнительное имя интерфейса: {repr(text)} у файла '{own_href}'")
    return text


def fix_class_hierarchy(own_href: str) -> list[list[str]] | None:
    if own_href == "ikompasapiobject.js":  # исключение. Иерархия вообще не показана.
        return [[CLASS_NAME_IDispatch], []]

    if own_href in (
            "ireportparam.js",  # написано IReportTable вместо IReportParam, поэтому не находит
            "ksglobject.js",  # что-то связанное с OpenGL; догадка, что родитель IDispatch
            "iframetreesmanager.js",  # интерфейс является дополнительным
            "iexternaltessellationmanager.js",  # интерфейс является дополнительным
            ):
        return [[CLASS_NAME_IDispatch], []]

    if own_href in (
            "iexternaltessellationobject.js",  # догадка судя по свойствам и методам в KompasAPI7.py
            "imarknode.js",  # догадка судя по свойствам и методам в KompasAPI7.py
            ):
        return [["IKompasAPIObject"], []]

    if own_href in (
            "imateconstraints3d.js",  # догадка судя по свойствам и методам в KompasAPI7.py
            "iangledimensions3d.js",  # зачем-то вписан IModelObject после IKompasCollection
            ):
        return [["IKompasCollection"], []]

    if own_href in (
            "ibilletobsolete.js",  # случайно увидел. Догадка.
            ):
        return [["ILocalCSObject"], []]

    return None


def fix_property_or_method_name(text: str, own_href: str) -> str:
    if own_href == "ipropertycontrol_controltype.js":  # русская С в названии
        return "ControlType"

    if own_href == "ibuildingaxis_textafter.js":  # русская Т в названии
        return "TextAfter"

    if own_href == "ksdocument3dnotify7_choicematerial.js":  # русская С в названии
        return "ChoiceMaterial"

    if own_href == "ksrasterformatparam_colortype.js":
        return "colorType"  # русская с в названии

    # if own_href == "ikompaserror_clear.js":  # написано "Clear- Сбросить ошибку", поэтому RegExp не срабатывает с наличием "-" после слова
    #     return "Clear"

    if not text.isidentifier() or not text.isascii():
        logger.warning(f"fix_property_or_method_name(): Предупреждение: сомнительное имя свойства/метода: {repr(text)} у файла '{own_href}'")
    return text


def fix_enum_name(text: str, own_href: str) -> str:
    if own_href == "objtypes.js":
        return "DrawingObjectTypeEnum"

    if own_href == "obj3dtype.js":
        return "ksObj3dTypeEnum"  # случаи с "Obj3dTypeEnum" будут автоматически исправлены на "ksObj3dTypeEnum"


    if text == "":  # для случая ENUM_UNNAMED
        return text

    if not text.isidentifier() or not text.isascii():
        logger.warning(f"fix_enum_name(): Предупреждение: сомнительное имя enum: {repr(text)} у файла '{own_href}'")
    return text


def does_enum_table_have_header_row(own_href: str) -> bool:
    if own_href in (
            "obj3dtype.js",
            "objtypes.js",
            "drawingobjecttypeenum.js",
            "ksarrowenum.js",
            "ksrequestfilestypeenum.js",
            ):
        return True
    return False


def fix_enum_table_cell_indexes(own_href: str) -> tuple[int, int, list[int]]:
    """
    Возвращает индексы столбцов: `(member_name_index, member_value_index, member_description_indexes)`:
    * `member_name_index: int` - индекс столбца с идентификатором.
        Если вернуть число `-1`, то этот индекс будет найден автоматически;
    * `member_value_index: int` - индекс столбца со значением.
        Если вернуть число `-1`, то этот индекс будет найден автоматически;
    * `member_description_indexes: list[int]` - индексы столбцов, которые пойдут в описание.
        Если вернуть пустой список `[]`, то эти индексы будут найдены автоматически.
        Если вернуть список `[-1]`, то ни один столбец не будет задействован для описания.

    Используй также `does_enum_table_have_header_row()`.
    """

    if own_href in (
            "stypes.js",  # самая первая строка не_имеет идентификатора
            ):
        return (0, 1, [])

    # TODO все те enums, у которых does_enum_table_have_header_row() == True

    return (-1, -1, [])


def fix_function_return_type(own_href: str) -> str|None:
    if own_href == "imateconstraints3d_mateconstraint3d.js":  # дана ссылка на imateconstraints3d, а не imateconstraint3d
        return "IMateConstraint3D"

    if own_href == "imultilines_add.js":
        return "IMultiline"  # должно быть с маленькой l, а не IMultiLine, как в Справке

    if own_href in (
            "itolerances3d_add.js",  # опечатка; написано "Itolerance3D"
            "itolerances3d_tolerance3d.js",  #  написано "ITolerance", хотя речь про ITolerance3D
            ):
        return "ITolerance3D"


    # if not text.isidentifier() or not text.isascii():
    #     logger.warning(f"fix_function_return_type(): Предупреждение: сомнительное имя типа возврата: {repr(text)} у файла '{own_href}'")
    return None


def fix_description_section_heading(heading_text: str, own_href: str) -> str|None:
    if own_href in (
            'ksdocumentframenotify_mousedblclick.js',
            'ksdocumentframenotify_mousedown.js',
            'ksdocumentframenotify_mousemove.js',
            'ksdocumentframenotify_mouseup.js',
            ):
        if heading_text.startswith("Значения системных кнопок, допустимых в комбинации параметра nShiftState:") \
                or heading_text.startswith("Значения типов кнопок мыши для параметра nButton:"):
            return DescriptionSection.InputParameters

    if own_href == 'ibuildingaxes_add.js':
    	if heading_text == 'Возможные значения type:':
            return DescriptionSection.InputParameters

    if own_href == 'imarks_add.js':
    	if heading_text == 'Возможные значения MarkType':
            return DescriptionSection.InputParameters

    if own_href == 'ipart7_defaultobject.js':
    	if heading_text == 'Типы объектов (Type):':
            return DescriptionSection.InputParameters

    if own_href == 'ileaders_add.js':
    	if heading_text == 'Типы линий-выносок:':
            return DescriptionSection.InputParameters

    return None


