"""Provider-neutral contracts and audio conversion for streaming STT."""

from __future__ import annotations

import audioop
import threading
from abc import ABC, abstractmethod
from array import array
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TranscriptEventKind(Enum):
    PARTIAL = "partial"
    COMPLETED = "completed"


@dataclass(frozen=True)
class StreamingTranscriptEvent:
    """One provider-addressable streaming transcription update."""

    kind: TranscriptEventKind
    source: str
    item_id: str
    text: str
    time_spoken: datetime | None = None


class StreamingSTTModelInterface(ABC):
    """Contract for providers that keep a persistent streaming session."""

    @abstractmethod
    def start(self):
        """Open the provider session and start its background workers."""

    @abstractmethod
    def append_audio(self, audio: bytes, captured_at=None):
        """Append source-format PCM audio to the persistent session."""

    @abstractmethod
    def commit(self):
        """Commit the current input turn when automatic turn detection is disabled."""

    @abstractmethod
    def stop(self):
        """Close the provider session and all background workers."""

    @abstractmethod
    def set_transcript_callback(self, callback):
        """Set callback(event) for provider-addressable transcript updates."""

    @abstractmethod
    def set_error_callback(self, callback):
        """Set callback(source, sanitized_message) for provider errors."""


class PCM16MonoResampler:
    """Incrementally convert arbitrary interleaved PCM into mono PCM16."""

    def __init__(self, sample_rate: int, sample_width: int, channels: int, target_rate: int = 24000):
        if sample_rate <= 0 or sample_width not in (1, 2, 3, 4) or channels <= 0:
            raise ValueError("Invalid PCM source format")
        self.sample_rate = int(sample_rate)
        self.sample_width = int(sample_width)
        self.channels = int(channels)
        self.target_rate = int(target_rate)
        self._pending = b""
        self._rate_state = None
        self._lock = threading.Lock()

    def convert(self, audio: bytes) -> bytes:
        """Convert a chunk without losing partial frames at chunk boundaries."""
        if not audio:
            return b""
        with self._lock:
            framed = self._pending + bytes(audio)
            frame_size = self.sample_width * self.channels
            complete_size = len(framed) - (len(framed) % frame_size)
            if complete_size <= 0:
                self._pending = framed
                return b""
            complete = framed[:complete_size]
            self._pending = framed[complete_size:]

            if self.sample_width == 1:
                complete = audioop.bias(complete, 1, -128)
            pcm16 = audioop.lin2lin(complete, self.sample_width, 2)
            mono = self._to_mono(pcm16)
            if self.sample_rate == self.target_rate:
                return mono
            converted, self._rate_state = audioop.ratecv(
                mono, 2, 1, self.sample_rate, self.target_rate, self._rate_state
            )
            return converted

    def reset(self):
        """Drop incomplete input and resampler history after a stream reset."""
        with self._lock:
            self._pending = b""
            self._rate_state = None

    def _to_mono(self, pcm16: bytes) -> bytes:
        if self.channels == 1:
            return pcm16
        if self.channels == 2:
            return audioop.tomono(pcm16, 2, 0.5, 0.5)

        samples = array("h")
        samples.frombytes(pcm16)
        mono = array("h")
        for offset in range(0, len(samples), self.channels):
            frame = samples[offset:offset + self.channels]
            mono.append(int(sum(frame) / len(frame)))
        return mono.tobytes()
