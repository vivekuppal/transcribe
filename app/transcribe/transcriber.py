"""Runtime contract shared by file/window and persistent streaming transcribers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TranscriberInterface(ABC):
    """Common lifecycle and control surface used by the desktop application."""

    transcribe: bool

    @abstractmethod
    def set_source_properties(self, mic_source=None, speaker_source=None):
        """Update capture formats after device selection."""

    @abstractmethod
    def set_source_enabled(self, source_name: str, enabled: bool):
        """Apply source enablement to provider resources when required."""

    @abstractmethod
    def set_transcription_enabled(self, enabled: bool):
        """Pause or resume transcription resources."""

    @abstractmethod
    def set_language(self, lang: str):
        """Update the expected source-audio language."""

    @abstractmethod
    def stop(self):
        """Release provider resources."""
