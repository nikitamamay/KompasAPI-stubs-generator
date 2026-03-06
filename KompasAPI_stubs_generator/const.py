"""
Константы для работы в этом проекте:
* пути к файлам Справки SDK Компас;
* пути к файлам промежуточным и результирующим этого проекта;

"""

import os


_OUTPUT_DIR_PATH = "./"
""" Путь к папке для результирующих файлов. """

_AUX_DIR_PATH = "./auxdir"
""" Путь к папке с вспомогательными временными файлами проекта. """

_SDK_HELP_DIR_PATH = ""
""" Путь к папке Справки SDK Компас, распакованной из zip-архива. (В этой папке должен лежать `index.html`) """


_are_filepaths_initialized: bool = False

_hmcontent_js_filepath: str = ""
_jstopics_dir: str = ""
_toc_filepath: str = ""
_topics_filepath: str = ""

_pylib_KAPI7_filepath_raw: str = ""
_pylib_K6API5_filepath_raw: str = ""
_pylib_KAPI7_filepath_updated: str = ""
_pylib_K6API5_filepath_updated: str = ""
_KompasAPIclassesHierarchy_file: str = ""
_KompasAPIconstants_file: str = ""
_pyi_KAPI7_filepath: str = ""
_pyi_K6API5_filepath: str = ""


def set_auxdir(auxdir_path: str) -> None:
    global _AUX_DIR_PATH
    _AUX_DIR_PATH = auxdir_path

def set_output_dir(output_dir_path: str) -> None:
    global _OUTPUT_DIR_PATH
    _OUTPUT_DIR_PATH = output_dir_path

def set_sdk_help_dir(sdk_help_dir_path: str) -> None:
    global _SDK_HELP_DIR_PATH
    _SDK_HELP_DIR_PATH = sdk_help_dir_path

def is_sdk_dir_correct() -> bool:
    return os.path.isdir(_SDK_HELP_DIR_PATH)


def init_filepaths():
    os.makedirs(_AUX_DIR_PATH, exist_ok=True)
    os.makedirs(_OUTPUT_DIR_PATH, exist_ok=True)

    global _hmcontent_js_filepath
    global _jstopics_dir
    global _toc_filepath
    global _topics_filepath
    global _pylib_KAPI7_filepath_raw
    global _pylib_K6API5_filepath_raw
    global _pylib_KAPI7_filepath_updated
    global _pylib_K6API5_filepath_updated
    global _KompasAPIclassesHierarchy_file
    global _KompasAPIconstants_file
    global _pyi_KAPI7_filepath
    global _pyi_K6API5_filepath
    _hmcontent_js_filepath = os.path.join(_SDK_HELP_DIR_PATH, "js/hmcontent.js")
    _jstopics_dir = os.path.join(_SDK_HELP_DIR_PATH, "jstopics")
    _toc_filepath = os.path.join(_AUX_DIR_PATH, 'toc.json')
    _topics_filepath = os.path.join(_AUX_DIR_PATH, 'topics.json')
    _pylib_KAPI7_filepath_raw = os.path.join(_AUX_DIR_PATH, module_KAPI7_tail.replace(".py", "_raw.json"))
    _pylib_K6API5_filepath_raw = os.path.join(_AUX_DIR_PATH, module_K6API5_tail.replace(".py", "_raw.json"))
    _pylib_KAPI7_filepath_updated = os.path.join(_AUX_DIR_PATH, module_KAPI7_tail.replace(".py", ".json"))
    _pylib_K6API5_filepath_updated = os.path.join(_AUX_DIR_PATH, module_K6API5_tail.replace(".py", ".json"))
    _KompasAPIclassesHierarchy_file = os.path.join(_OUTPUT_DIR_PATH, "classes_hierarchy.py")
    _KompasAPIconstants_file = os.path.join(_OUTPUT_DIR_PATH, "constants.py")
    _pyi_KAPI7_filepath = os.path.join(_OUTPUT_DIR_PATH, module_KAPI7_tail + "i")    # .py -> .pyi
    _pyi_K6API5_filepath = os.path.join(_OUTPUT_DIR_PATH, module_K6API5_tail + "i")  # .py -> .pyi

    global _are_filepaths_initialized
    _are_filepaths_initialized = True



### файлы справки КомпасAPI

help_api7_root_topic_href = "applicate.html"
help_api5_root_topic_href = "ag57940.html"
help_constants_topic_href = "bk1803360.html"

module_KAPI7_tail = "KompasAPI7.py"
module_K6API5_tail = "Kompas6API5.py"



def get_hmcontent_js_filepath() -> str:
    if not is_sdk_dir_correct(): raise Exception(f"Неверно указан путь к папке Справки SDK Компас: '{_SDK_HELP_DIR_PATH}'")
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _hmcontent_js_filepath

def get_jstopics_dir() -> str:
    if not is_sdk_dir_correct(): raise Exception(f"Неверно указан путь к папке Справки SDK Компас: '{_SDK_HELP_DIR_PATH}'")
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _jstopics_dir


### файлы промежуточные и результирующие этого проекта

def get_toc_filepath() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _toc_filepath


def get_topics_filepath() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _topics_filepath


def get_pylib_KAPI7_filepath_raw() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pylib_KAPI7_filepath_raw

def get_pylib_K6API5_filepath_raw() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pylib_K6API5_filepath_raw


def get_pylib_KAPI7_filepath_updated() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pylib_KAPI7_filepath_updated

def get_pylib_K6API5_filepath_updated() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pylib_K6API5_filepath_updated


def get_KompasAPIclassesHierarchy_file() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _KompasAPIclassesHierarchy_file

def get_KompasAPIconstants_file() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _KompasAPIconstants_file

def get_pyi_KAPI7_filepath() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pyi_KAPI7_filepath

def get_pyi_K6API5_filepath() -> str:
    if not _are_filepaths_initialized: raise Exception(f"Filepaths are not initialized!")
    return _pyi_K6API5_filepath

