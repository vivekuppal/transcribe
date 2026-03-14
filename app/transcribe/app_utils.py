"""Compatibility wrapper for provider and desktop runtime helpers."""

from .desktop.runtime import (
    initialize_desktop_runtime,
    initiate_app_threads,
    initiate_db,
    shutdown,
    start_audio_capture,
)
from .providers.llm import create_responder
from .providers.stt import create_transcriber, ensure_ffmpeg_available as start_ffmpeg

__all__ = [
    "create_responder",
    "create_transcriber",
    "initialize_desktop_runtime",
    "initiate_app_threads",
    "initiate_db",
    "shutdown",
    "start_audio_capture",
    "start_ffmpeg",
]
