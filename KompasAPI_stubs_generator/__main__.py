
from . import logging_system

import sys
import getopt

from . import const


### arguments parsing



do_only: bool = False
do_only_targets: dict[str, bool] = {
    "toc": False,
    "topics": False,
    "parse_module": False,
    "update_module": False,
    "hier": False,
    "stub": False,
    "const": False,
}

kompas_api_section_specified: bool = False
kompas_api_section: dict[str, bool] = {
    "1": False,
    "5": False,
    "7": False,
}



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

    -d, --do {underline("target")}
        Если флаг указан, то выполняется только {underline("target")}.
        Флаг может быть указан несколько раз.
        Если флаг не указан, выполняются все цели.
        Возможные значения: toc, topics, parse_module, update_module, hier, stub, const
        По умолчанию: выполняются все цели.

    -k, --kompas {underline("api_section")}
        Выполняет обработку для раздела API {underline("api_section")}.
        Флаг может быть указан несколько раз.
        Возможные значения: 1 - constants
                            5 - Кompas6 API 5
                            7 - Kompas API 7
        По умолчанию: выполняются для всех возможных разделов.

    -h, --help
        Отобразить эту справку и выйти.

""", end="")

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "s:a:o:hd:k:", [
        "sdk-dir=",
        "aux-dir=",
        "out-dir=",
        "help",
        "log=",
        "do=",
        "kompas="
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

        elif opt in ("-d", "--do"):
            do_only = True
            if not value in do_only_targets:
                raise Exception(f"Неверная цель: {repr(value)}")
            do_only_targets[value] = True

        elif opt in ("-k", "--kompas"):
            kompas_api_section_specified = True
            if not value in kompas_api_section:
                raise Exception(f"Неверный раздел KompasAPI: {repr(value)}")
            kompas_api_section[value] = True

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


do_k5 = not kompas_api_section_specified or kompas_api_section["5"]
do_k7 = not kompas_api_section_specified or kompas_api_section["7"]
do_const = not kompas_api_section_specified or kompas_api_section["1"]

if not do_only or do_only_targets["parse_module"]:
    logger.info(f"\nparse_module")
    parse_module.main(do_k5, do_k7)


if not do_only or do_only_targets["toc"]:
    logger.info(f"\nparse_table_of_contents")
    parse_table_of_contents.main()

if not do_only or do_only_targets["topics"]:
    logger.info(f"\nparse_topics")
    parse_topics.main(do_k5, do_k7, do_const)


if not do_only or do_only_targets["update_module"]:
    logger.info(f"\nupdate_module")
    update_module.main(do_k5, do_k7)


if not do_only or do_only_targets["hier"]:
    logger.info(f"\ngenerate_hierarchy")
    generate_hierarchy.main()

if not do_only or do_only_targets["stub"]:
    logger.info(f"\ngenerate_stub")
    generate_stub.main(do_k5, do_k7)

if not do_only or do_only_targets["const"]:
    if do_const:
        logger.info(f"\ngenerate_constants")
        generate_constants.main()


