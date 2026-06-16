"""Provider-neutral transcription result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranscriptSegment:
    """A timestamped transcript segment normalized across STT providers."""

    id: int
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class TranscriptionHypothesis:
    """A provider response normalized for live transcription reconciliation."""

    provider: str
    text: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    audio_start_seconds: float = 0.0
    audio_end_seconds: float = 0.0
