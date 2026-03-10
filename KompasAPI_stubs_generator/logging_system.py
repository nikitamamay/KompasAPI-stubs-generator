"""
Модуль с некоторыми предварительными настройками системы вывода отладочной информации.

См. также модуль `logging`.
"""

import sys
import logging
import os

from . import const

DEFAULT_LEVEL = logging.DEBUG

def get_logfile_path() -> str:
    return os.path.join(const.get_auxdir(), "output.log")


class StdoutInfoOnlyStreamHandler(logging.StreamHandler):
    def __init__(self) -> None:
        super().__init__(sys.stdout)
        self.setLevel(logging.INFO)

    def handle(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.WARNING and record.levelno >= logging.INFO:
            return super().handle(record)
        return False


def get_logger(
        name: str|None,
        # level: int = DEFAULT_LEVEL,
        ) -> logging.Logger:
    logging.basicConfig(
        filename=get_logfile_path(),
        encoding='utf-8',
        format="[%(asctime)s] %(name)s: %(levelname)s: %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )
    level = DEFAULT_LEVEL
    l = logging.getLogger(name)
    l.setLevel(level)
    ch = StdoutInfoOnlyStreamHandler()
    l.addHandler(ch)
    return l
