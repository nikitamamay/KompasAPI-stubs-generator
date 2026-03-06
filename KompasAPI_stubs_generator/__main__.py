
from . import logging_system

import sys
import getopt


### arguments parsing

def usage():
    print(
f"""\
Использование:
    {sys.argv[0]} OPTIONS

Опции (OPTIONS):
    -h, --help
        Отобразить эту справку и выйти.

    --log=DEBUG
        Установить уровень вывода отладочной информации.
        Возможные значения: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL

""", end="")

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "h", [
        "help",
        "log="
    ])


    for opt, value in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in ("--log"):
            value = value.upper()
            if not value in logging_system.logging.getLevelNamesMapping():
                raise Exception(f"Некорректный уровень вывода отладочной информации: {repr(value)}")
            logging_system.DEFAULT_LEVEL = logging_system.logging.getLevelNamesMapping()[value]
        else:
            raise Exception(f"Неизвестная опция: '{opt} {value}'")

    if len(args) < 1:
        raise Exception("Недостаточно аргументов")

    sdk_base_dir = args[0]

except Exception as e:
    print(e, file=sys.stderr)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)


### main
# импорты после парсинга аргументов, потому что при импортах сразу создается Logger, а опцией CLI `--log=...` может задаваться его уровень логгирования.

from . import const
from . import parse_module
from . import parse_table_of_contents
from . import parse_topics
from . import update_module
from . import generate_hierarchy
from . import generate_stub
from . import generate_constants


logger = logging_system.get_logger(__name__)


logger.info(f"parse_module")
parse_module.main()


logger.info(f"")  # пустая строка для разделения
logger.info(f"parse_table_of_contents")
parse_table_of_contents.main(sdk_base_dir)

logger.info(f"")  # пустая строка для разделения
logger.info(f"parse_topics")
parse_topics.main(sdk_base_dir)


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


