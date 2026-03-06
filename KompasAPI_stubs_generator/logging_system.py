"""
Модуль с некоторыми предварительными настройками системы вывода отладочной информации.

См. также модуль `logging`.
"""

import sys
import logging


DEFAULT_LEVEL = logging.DEBUG

logging.basicConfig(
    filename='output.log',
    encoding='utf-8',
    format="[%(asctime)s] %(name)s: %(levelname)s: %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

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
    level = DEFAULT_LEVEL
    l = logging.getLogger(name)
    l.setLevel(level)
    ch = StdoutInfoOnlyStreamHandler()
    l.addHandler(ch)
    return l
