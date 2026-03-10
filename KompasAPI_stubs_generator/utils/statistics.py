"""
Формирование статистики об обработанных файлах.
"""

import typing
import sys
import os


def render_file_size(size_bytes: int) -> str:
    """
    Представляет размер файла в удобном для чтения формате c единицами измерения: b, Kb, Mb, Gb.
    """
    if size_bytes > 1073741824:
        return "%.1f GB" % (size_bytes / 1073741824)

    if size_bytes > 1048576:
        return "%.1f MB" % (size_bytes / 1048576)

    if size_bytes > 1024:
        return "%.1f KB" % (size_bytes / 1024)

    return "%.1f B" % (size_bytes / 1000)


def measure_size(filepaths: typing.Iterable[str|object|None]) -> int:
    """
    Замеряет суммарный размер файлов по путям `filepaths`.

    Если в списке путей `filepaths` встретится не строка (not `str`),
    это значение будет проигнорировано.
    """
    total_size: int = 0
    for filepath in filepaths:
        if isinstance(filepath, str):
            s = os.stat(filepath)
            total_size += s.st_size
    return total_size
