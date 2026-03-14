import sys
import atexit
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

try:
    from .appui import AppUI
    from .cli.arguments import create_args, update_args_config
    from .cli.batch import handle_batch_tasks
    from .core.state import T_GLOBALS
    from .desktop import DesktopController
    from .desktop.runtime import (
        initialize_desktop_runtime,
        initiate_app_threads,
        shutdown,
        start_audio_capture,
    )
except ImportError:
    from appui import AppUI
    from cli.arguments import create_args, update_args_config
    from cli.batch import handle_batch_tasks
    from core.state import T_GLOBALS
    from desktop import DesktopController
    from desktop.runtime import initialize_desktop_runtime, initiate_app_threads, shutdown, start_audio_capture

from tsutils import app_logging as al
from tsutils import configuration


def main():
    """Primary method to run transcribe
    """
    args = create_args()

    config = configuration.Config().data
    global_vars = T_GLOBALS

    update_args_config(args, config)
    if handle_batch_tasks(args, config):
        return

    initialize_desktop_runtime(global_vars, config)

    # Convert raw audio files to real wav file format when program exits
    atexit.register(shutdown, global_vars)

    start_audio_capture(global_vars)

    # Initiate logging
    log_listener = al.initiate_log(config=config)

    controller = DesktopController(config=config, global_vars=global_vars)
    aui = AppUI(config=config, controller=controller)
    initiate_app_threads(global_vars=global_vars, config=config)

    print("READY")

    # Set the response lang in STT Model.
    global_vars.transcriber.stt_model.set_lang(config['OpenAI']['audio_lang'])
    aui.update_initial_transcripts()
    aui.start()
    log_listener.stop()


if __name__ == "__main__":
    main()
