
from . import logging_system

import sys
import getopt

from . import const


### arguments parsing

def underline(text: str) -> str:
    return f"\033[4m{text}\033[m"

def usage():
    print(
f"""\
Использование:
    {sys.argv[0]} OPTIONS

Опции (OPTIONS):
    -s, --sdk-dir {underline("path")}
        Установить путь к папке Справки SDK Компас, распакованной из zip-архива.
        Обязательный аргумент, если указаны требуются действия для анализа Справки.
        По умолчанию: ""

    -a, --aux-dir {underline("path")}
        Установить директорию для вывода вспомогательных файлов.
        По умолчанию: "./auxdir"

    -o, --out-dir {underline("path")}
        Установить директорию для вывода результирующих файлов.
        По умолчанию: "./"

    --log {underline("level")}
        Установить уровень вывода отладочной информации.
        Возможные значения: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
        По умолчанию: DEBUG

    -h, --help
        Отобразить эту справку и выйти.

""", end="")

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "s:a:o:h", [
        "sdk-dir=",
        "aux-dir=",
        "out-dir=",
        "help",
        "log=",
    ])

    for opt, value in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)

        elif opt in ("-s", "--sdk-dir"):
            const.set_sdk_help_dir(value)

        elif opt in ("-a", "--aux-dir"):
            const.set_auxdir(value)

        elif opt in ("-o", "--out-dir"):
            const.set_output_dir(value)

        elif opt in ("--log"):
            value = value.upper()
            if not value in logging_system.logging.getLevelNamesMapping():
                raise Exception(f"Некорректный уровень вывода отладочной информации: {repr(value)}")
            logging_system.DEFAULT_LEVEL = logging_system.logging.getLevelNamesMapping()[value]

        else:
            raise Exception(f"Неизвестная опция: '{opt}' '{value}'")

    # if len(args) < 1:
    #     raise Exception("Недостаточно аргументов")

except Exception as e:
    print(f"{e}\n\nИспользуйте флаг '--help' для вывода справки.")
    # usage()
    sys.exit(2)



logger = logging_system.get_logger(__name__)

const.init_filepaths()

# проверка на правильность указания пути к папке SDK
if not const.is_sdk_dir_correct():
    print(f"Неверно указан путь к папке Справки SDK Компас: '{const._SDK_HELP_DIR_PATH}'")
    print(f"Не использован флаг '--sdk-dir=' ?")
    print(f"\nИспользуйте флаг '--help' для вывода справки.")
    sys.exit(1)


### main
# импорты после парсинга аргументов, потому что при импортах сразу создается Logger, а опцией CLI `--log=...` может задаваться его уровень логгирования.

from . import parse_module
from . import parse_table_of_contents
from . import parse_topics
from . import update_module
from . import generate_hierarchy
from . import generate_stub
from . import generate_constants


logger.info(f"parse_module")
parse_module.main()


logger.info(f"")  # пустая строка для разделения
logger.info(f"parse_table_of_contents")
parse_table_of_contents.main()

logger.info(f"")  # пустая строка для разделения
logger.info(f"parse_topics")
parse_topics.main()


logger.info(f"")  # пустая строка для разделения
logger.info(f"update_module")
update_module.main()


logger.info(f"")  # пустая строка для разделения
logger.info(f"generate_hierarchy")
generate_hierarchy.main()

logger.info(f"")  # пустая строка для разделения
logger.info(f"generate_stub")
generate_stub.main()

logger.info(f"")  # пустая строка для разделения
logger.info(f"generate_constants")
generate_constants.main()


