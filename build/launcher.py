"""Entry point of the packaged Windows program (Transcribe.exe).

The packaged program keeps parameters.yaml, override.yaml and the bin folder next to
Transcribe.exe, so it always starts in that folder, wherever it is opened from.

Transcribe.exe is built as a window program: double-clicked, no console window opens at all.
Its messages then go to a log file. Run from a command prompt (for example --help or -t), its
output goes to that prompt, or to the file it is redirected to.
"""
import os
import sys

STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
ATTACH_PARENT_PROCESS = -1


def _stream_from_handle(kernel32, which):
    """A text stream for an inherited standard handle (a file or pipe the caller redirected to)."""
    import ctypes  # pylint: disable=import-outside-toplevel
    import msvcrt  # pylint: disable=import-outside-toplevel
    handle = kernel32.GetStdHandle(which)
    invalid = (None, 0, ctypes.c_void_p(-1).value)
    if handle in invalid or kernel32.GetFileType(handle) == 0:      # 0 = no usable handle
        return None
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_WRONLY)
        return open(fd, "w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    except OSError:
        return None


def connect_output():
    """Give a window program somewhere to write: the caller's redirect, the caller's console,
    or (double-clicked) a log file. Without this, writing to the missing console fails."""
    if sys.platform != "win32" or (sys.stdout is not None and sys.stderr is not None):
        return
    import ctypes  # pylint: disable=import-outside-toplevel
    kernel32 = ctypes.windll.kernel32
    kernel32.GetStdHandle.restype = ctypes.c_void_p
    kernel32.GetStdHandle.argtypes = [ctypes.c_ulong]
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]

    out = _stream_from_handle(kernel32, ctypes.c_ulong(STD_OUTPUT_HANDLE).value)
    err = _stream_from_handle(kernel32, ctypes.c_ulong(STD_ERROR_HANDLE).value)
    if out is None and len(sys.argv) > 1 and kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
        # started from a command prompt with options: write into that prompt
        console = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        console.write("\n")
        out = err = console
    if out is None:
        # double-clicked: keep the messages in a log file next to the program's other logs
        # (the same folder as the program's other logs: tsutils.utilities.get_data_path)
        folder = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "viveku", "Transcribe", "logs")
        try:
            os.makedirs(folder, exist_ok=True)
            out = open(os.path.join(folder, "console.txt"), "w", encoding="utf-8", errors="replace", buffering=1)
        except OSError:
            out = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stdout or out
    sys.stderr = sys.stderr or err or out


if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
    connect_output()

from app.transcribe.main import main  # noqa: E402  (after the folder change)

if __name__ == "__main__":
    main()
