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
    def _add_parent_href(body: Tag, parent_href: str) -> None:
        t = Tag(name="p", attrs={"class": "p_bodytext"})
        a = Tag(name="a", attrs={"href": parent_href})
        a.string = "Интерфейс..."
        body.append(t)
        t.append(a)

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

    if jstopic_own_href == "ireport_stylescount.js":  # отсутствует ссылка на родительский интерфейс
        _add_parent_href(body, "ireport.html")

    if jstopic_own_href == "iembodiment_part.js":  # отсутствует ссылка на родительский интерфейс
        _add_parent_href(body, "iembodiment.html")

    if jstopic_own_href == "ispecificationobject_additionalcolumns.js":  # отсутствует ссылка на родительский интерфейс
        _add_parent_href(body, "ispecificationobject.html")

    if jstopic_own_href == "icomponentpositioner7_initplanebyplacement.js":  # нет переноса после заголовка "Синтаксис COM"
        _fix_SyntaxCOM_wrap(body, "HRESULT InitPlaneByPlacement( IPlacement3D * Placement, BOOL * Result );")

    if jstopic_own_href == "isketch_usersetplacement.js":  # нет переноса после заголовка "Синтаксис COM"
        _fix_SyntaxCOM_wrap(body, "HRESULT UserSetPlacement( BSTR Prompt, BOOL * Result );")


    # TODO: kompasobject_getdynamicarray.js


    # страницы констант

    if jstopic_own_href in ( # удаление первой строки-заголовка у таблицы
            "obj3dtype.js"
            "objtypes.js",
            # "objects_select.js",  # первая строка сделана с colspan (как caption)
            "drawingobjecttypeenum.js",
            ):
        body.find("table").find("tr").extract()   # type: ignore

    if jstopic_own_href in ( # удаление заголовка таблицы, состоящего из двух строк
            "ksarrowenum.js",
            ):
        body.find("table").find("tr").extract()   # type: ignore
        body.find("table").find("tr").extract()   # type: ignore

    if jstopic_own_href == "ksconstrainttypeenum.js":  # написана русская 'к'
        body.find("td").string = "ksCUnknown"   # type: ignore

    if jstopic_own_href == "paramtype.js":  # какой-то артефакт в последней строке таблицы: "0x08 //>0"
        body.find_all("td")[-2].string = "0x08"


def is_useless_page(own_href: str) -> bool:
    if own_href in (
            # KAPI7:
            "iapplication_events.js",  # страница с перенаправлениями
            "bb2327204.js",  # страница с перенаправлениями
            "cj1798939.js",  # страница с перенаправлениями
            # K6API5:
            'ag91931.js',  # 'Методы вывода на экран'
            'ag95246.js',  # 'Работа с файлами'
            'ag92071.js',  # 'Сервисные функции'
            'int_pr_curve.js',  # 'Интерфейсы пространственных кривых'
            'nt_surface.js',  # 'Интерфейсы поверхностей'
            'int_copy.js',  # 'Интерфейсы копирования'
            'i.js',  # 'Интерфейсы копирования компонентов сборки'
            'int_operation.js',  # Интерфейсы формообразующих операций'
            'int_additional.js',  # Интерфейсы дополнительных элементов'
            'bt1730611.js',  # 'Аннотационные объекты'
            'bt1730612.js',  # 'Составные объекты'
            'bt1730613.js',  # 'Стили'
            'bt1756228.js',  # 'Окна'
            'bt1730186.js',  # 'Параметры'
            'bt1730197.js',  # 'Связи и ограничения'
            'bt1742269.js',  # 'Навигация'
            'bt1744101.js',  # 'Параметрические переменные'
            'bt1730260.js',  # 'Работа с документом'
            'bt1730281.js',  # 'Оформление чертежа'
            'bt1732733.js',  # 'Группы объектов'
            'bt1734633.js',  # 'Операции редактирования'
            'bt1730357.js',  # 'Редактирование графических объектов'
            'bt1730395.js',  # 'Создание видов'
            'bt1732273.js',  # 'Работа со слоями'
            'bt1731191.js',  # 'Текстовые надписи'
            'bt1731193.js',  # 'Работа с таблицей и с допуском формы'
            'bt1730488.js',  # 'Размеры и технологические обозначения'
            'bt1756850.js',  # 'Матрицы преобразования'
            'bt1730616.js',  # 'Графические примитивы'
            'cc1711098.js',  # 'Интерфейсы фантомов'
            'cc1711812.js',  # 'Интерфейсы видов, слоев, запроса к системе'
            'cd1743949.js',  # 'Интерфейсы параметров графических примитивов'
            'cd1711795.js',  # 'Интерфейсы точек касания и сопряжения'
            'ce1717197.js',  # 'Интерфейсы параметров формата и компоновки чертежа'
            'cf1711377.js',  # 'Интерфейсы параметров стилей объектов'
            'cf1713887.js',  # 'Интерфейсы параметров размеров'
            'ch1786244.js',  # 'Интерфейсы параметров обозначений'
            'ch1780203.js',  # 'Интерфейсы спецификации'
            'ck1918891.js',  # 'Интерфейсы параметров элементов текста'
            "int_geometry.js",
            ):
        return True
    return False


def is_interface_page(own_href: str) -> bool|None:
    if own_href in (
            "idrawingobjects.js",  # страница интерфейса, но в заглавии нет слова "Интерфейс "
            "izonedivision.js"  # написано "Интерфей " с пропущенной "с"
            ):
        return True

    return None


def fix_parent_interface_href(parent_interface_href: str, own_href: str) -> str:
    if parent_interface_href == "propertymanagernotify.js":
        return "kspropertymanagernotify.js"

    return parent_interface_href


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

    # if own_href == "ikompaserror_clear.js":  # написано "Clear- Сбросить ошибку", поэтому RegExp не срабатывает с наличием "-" после слова
    #     return "Clear"

    if not text.isidentifier() or not text.isascii():
        logger.warning(f"fix_property_or_method_name(): Предупреждение: сомнительное имя свойства/метода: {repr(text)} у файла '{own_href}'")
    return text


def fix_enum_name(text: str, own_href: str) -> str:
    if own_href == "objtypes.js":
        return "DrawingObjectTypeEnum"



    if text == "":
        return text

    if not text.isidentifier() or not text.isascii():
        logger.warning(f"fix_enum_name(): Предупреждение: сомнительное имя enum: {repr(text)} у файла '{own_href}'")
    return text


def fix_enum_table_cell_indexes(own_href: str) -> tuple[int, int]:
    if own_href == "objtypes.js":
        return (1, 2)

    if own_href in (
            "stypes.js",  # самая первая строка не_имеет идентификатора
            ):
        return (0, 1)

    "ksarrowenum.js"  # TODO

    return (-1, -1)


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


