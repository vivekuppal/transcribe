"""Entry point of the packaged Windows program (Transcribe.exe).

The packaged program keeps parameters.yaml, override.yaml and the bin folder next to
Transcribe.exe, so it always starts in that folder, wherever it is opened from.
"""
import os
import sys



def hide_own_console():
    """Opened by double-click, the program gets its own black console window: hide it (the log
    file keeps the messages). Started from a command prompt, the console stays, so command-line
    options like --help or -t still show their output."""
    if sys.platform != "win32" or len(sys.argv) > 1:
        return
    try:
        import ctypes  # pylint: disable=import-outside-toplevel
        kernel32 = ctypes.windll.kernel32
        processes = (ctypes.c_uint * 4)()
        if kernel32.GetConsoleProcessList(processes, 4) == 1:      # nobody else uses this console
            window = kernel32.GetConsoleWindow()
            if window:
                ctypes.windll.user32.ShowWindow(window, 0)        # SW_HIDE
    except Exception:  # pylint: disable=broad-except
        pass


if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
    hide_own_console()

from app.transcribe.main import main  # noqa: E402  (after the folder change)

if __name__ == "__main__":
    main()
