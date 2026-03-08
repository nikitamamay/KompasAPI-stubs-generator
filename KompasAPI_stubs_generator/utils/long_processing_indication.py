
from time import time as timestamp_now


MAX_DELAY: float = 2.0
""" Максимальное время ожидания в секундах  """

_next_moment: float = 0



def start_processing() -> None:
    global _next_moment
    _next_moment = timestamp_now() + MAX_DELAY


def check_processing() -> bool:
    global _next_moment
    now = timestamp_now()
    if now > _next_moment:
        _next_moment = now + MAX_DELAY
        return True
    return False


if __name__ == "__main__":
    """
    Пример использования:
    """

    from time import sleep as _time_sleep

    start_processing()

    max_count = 100
    for i in range(max_count):
        if check_processing():
            print(f"Прогресс: {i} / {max_count} (%.1f%%)", i / max_count * 100)

        _time_sleep(0.0113465)
