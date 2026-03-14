"""Desktop application runtime composition."""

from .controller import DesktopController
from .runtime import (
    initialize_desktop_runtime,
    initiate_app_threads,
    initiate_db,
    shutdown,
    start_audio_capture,
)

__all__ = [
    "DesktopController",
    "initialize_desktop_runtime",
    "initiate_app_threads",
    "initiate_db",
    "shutdown",
    "start_audio_capture",
]
