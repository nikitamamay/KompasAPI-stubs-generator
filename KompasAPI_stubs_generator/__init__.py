
import sys
import os
from .utils import utils



def _escape_filename(text: str) -> str:
    return text.replace(" ", "").replace("\"", ".").replace("\'", ".")

def redirect_output(file, do_redirect_stderr = True):
    file = os.path.basename(file)
    STDOUT_FILEPATH: str = f"out-{_escape_filename(file)}.log"
    STDERR_FILEPATH: str = f"errors-{_escape_filename(file)}.log" if do_redirect_stderr else STDOUT_FILEPATH

    print(f"output is redirected: stdout='{STDOUT_FILEPATH}', stderr='{STDERR_FILEPATH}'")

    sys.stdout = open(STDOUT_FILEPATH, "a", encoding="utf-8")

    if do_redirect_stderr:
        sys.stderr = open(STDERR_FILEPATH, "a", encoding="utf-8")
    else:
        sys.stderr = sys.stdout

    print(f"""
===========================================
{utils.get_now_datetime_str()}
{file}
===========================================
""")

    if sys.stdout != sys.stderr:
        print(f"""
===========================================
{utils.get_now_datetime_str()}
{file}
===========================================
""", file=sys.stderr)


