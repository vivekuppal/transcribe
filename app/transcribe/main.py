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
    from .core.state import create_app_runtime
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
    from core.state import create_app_runtime
    from desktop import DesktopController
    from desktop.runtime import initialize_desktop_runtime, initiate_app_threads, shutdown, start_audio_capture

from tsutils import app_logging as al
from tsutils import configuration


def main():
    """Primary method to run transcribe
    """
    args = create_args()

    config = configuration.Config().data
    runtime = create_app_runtime()

    update_args_config(args, config)
    if handle_batch_tasks(args, config):
        return

    initialize_desktop_runtime(runtime, config)

    # Convert raw audio files to real wav file format when program exits
    atexit.register(shutdown, runtime)

    start_audio_capture(runtime)

    # Initiate logging
    log_listener = al.initiate_log(config=config)

    controller = DesktopController(config=config, runtime=runtime)
    aui = AppUI(config=config, runtime=runtime, controller=controller)
    initiate_app_threads(runtime=runtime, config=config)

    print("READY")

    # Set the response lang in STT Model.
    runtime.transcriber.stt_model.set_lang(config['OpenAI']['audio_lang'])
    aui.update_initial_transcripts()
    aui.start()
    log_listener.stop()


if __name__ == "__main__":
    main()
