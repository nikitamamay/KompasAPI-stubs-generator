"""
Константы для работы в этом проекте:
* пути к файлам Справки SDK Компас;
* пути к файлам промежуточным и результирующим этого проекта;

"""

import os


OUTPUT_BASE_DIR = "./output"
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)


### файлы справки КомпасAPI

help_api7_root_topic_href = "applicate.html"
help_api5_root_topic_href = "ag57940.html"
help_constants_topic_href = "bk1803360.html"

module_KAPI7_tail: str = "KompasAPI7.py"
module_K6API5_tail: str = "Kompas6API5.py"

def get_hmcontent_js_filepath(sdk_help_base_dir: str) -> str:
    return os.path.join(sdk_help_base_dir, "js/hmcontent.js")

def get_jstopics_dir(sdk_help_base_dir: str) -> str:
    return os.path.join(sdk_help_base_dir, "jstopics")

### файлы промежуточные и результирующие этого проекта

toc_filepath = os.path.join(OUTPUT_BASE_DIR, 'toc.json')

topics_filepath = os.path.join(OUTPUT_BASE_DIR, 'topics.json')

pylib_KAPI7_filepath_raw = os.path.join(OUTPUT_BASE_DIR, module_KAPI7_tail.replace(".py", "_raw.json"))
pylib_K6API5_filepath_raw = os.path.join(OUTPUT_BASE_DIR, module_K6API5_tail.replace(".py", "_raw.json"))

pylib_KAPI7_filepath_updated = os.path.join(OUTPUT_BASE_DIR, module_KAPI7_tail.replace(".py", ".json"))
pylib_K6API5_filepath_updated = os.path.join(OUTPUT_BASE_DIR, module_K6API5_tail.replace(".py", ".json"))

KompasAPIclassesHierarchy_file = os.path.join(OUTPUT_BASE_DIR, "classes_hierarchy.py")
KompasAPIconstants_file = os.path.join(OUTPUT_BASE_DIR, "constants.py")
pyi_KAPI7_filepath = os.path.join(OUTPUT_BASE_DIR, module_KAPI7_tail + "i")    # .py -> .pyi
pyi_K6API5_filepath = os.path.join(OUTPUT_BASE_DIR, module_K6API5_tail + "i")  # .py -> .pyi




