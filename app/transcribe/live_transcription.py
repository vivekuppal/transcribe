"""Live transcription reconciliation for rolling audio windows."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from sdk.transcription_result import TranscriptSegment, TranscriptionHypothesis


DEFAULT_WINDOW_SECONDS = 30
DEFAULT_MUTABLE_TAIL_SECONDS = 5
DEFAULT_AUDIO_CONTEXT_SECONDS = 10
DEFAULT_STABILITY_PASSES = 2


@dataclass
class LiveTranscriptUpdate:
    """Conversation update produced from a live transcription hypothesis."""

    text: str
    update_previous: bool
    changed: bool


@dataclass
class _SpeakerTranscriptState:
    current_text: str = ""
    finalized_text: str = ""
    last_hypothesis_text: str = ""
    stability_count: int = 0


class LiveTranscriptManager:
    """Maintain stable live transcript text across overlapping STT windows."""

    def __init__(self, config: dict):
        general = config.get("General", {})
        self.mutable_tail_seconds = float(
            general.get("live_transcription_mutable_tail_seconds", DEFAULT_MUTABLE_TAIL_SECONDS)
        )
        self.stability_passes = int(
            general.get("live_transcription_stability_passes", DEFAULT_STABILITY_PASSES)
        )
        self._states: dict[str, _SpeakerTranscriptState] = {}

    def clear(self):
        """Clear all live transcript reconciliation state."""
        self._states.clear()

    def process_hypothesis(
        self,
        speaker: str,
        hypothesis: TranscriptionHypothesis,
        new_phrase: bool,
    ) -> LiveTranscriptUpdate:
        """Merge a provider hypothesis into the speaker's current transcript."""
        state = self._states.setdefault(speaker, _SpeakerTranscriptState())
        hypothesis_text = self._clean_text(hypothesis.text)
        if not hypothesis_text:
            return LiveTranscriptUpdate(text=state.current_text, update_previous=True, changed=False)

        if new_phrase:
            state.current_text = hypothesis_text
            state.finalized_text = self._finalized_prefix(hypothesis)
            state.last_hypothesis_text = hypothesis_text
            state.stability_count = 1
            return LiveTranscriptUpdate(text=state.current_text, update_previous=False, changed=True)

        merged_text = self._merge_text(state.current_text, hypothesis_text)
        protected_text = self._protect_finalized_prefix(state.finalized_text, merged_text)
        changed = protected_text != state.current_text

        if hypothesis_text == state.last_hypothesis_text:
            state.stability_count += 1
        else:
            state.stability_count = 1

        state.current_text = protected_text
        state.finalized_text = self._merge_text(
            state.finalized_text,
            self._finalized_prefix(hypothesis),
        )
        state.last_hypothesis_text = hypothesis_text
        return LiveTranscriptUpdate(text=state.current_text, update_previous=True, changed=changed)

    def _finalized_prefix(self, hypothesis: TranscriptionHypothesis) -> str:
        cutoff = hypothesis.audio_end_seconds - self.mutable_tail_seconds
        finalized_segments = [
            segment for segment in hypothesis.segments if segment.end_seconds <= cutoff
        ]
        return self._clean_text(" ".join(segment.text for segment in finalized_segments))

    @classmethod
    def _protect_finalized_prefix(cls, finalized_text: str, candidate_text: str) -> str:
        finalized_text = cls._clean_text(finalized_text)
        candidate_text = cls._clean_text(candidate_text)
        if not finalized_text or candidate_text.startswith(finalized_text):
            return candidate_text
        return cls._merge_text(finalized_text, candidate_text)

    @classmethod
    def _merge_text(cls, existing_text: str, hypothesis_text: str) -> str:
        existing_text = cls._clean_text(existing_text)
        hypothesis_text = cls._clean_text(hypothesis_text)
        if not existing_text:
            return hypothesis_text
        if not hypothesis_text:
            return existing_text
        if existing_text == hypothesis_text:
            return existing_text
        if hypothesis_text.startswith(existing_text):
            return hypothesis_text
        if existing_text.endswith(hypothesis_text):
            return existing_text

        existing_tokens = existing_text.split()
        hypothesis_tokens = hypothesis_text.split()
        overlap = cls._token_overlap(existing_tokens, hypothesis_tokens)
        if overlap:
            return " ".join(existing_tokens + hypothesis_tokens[overlap:])

        rolling_window_merge = cls._merge_rolling_window(existing_tokens, hypothesis_tokens)
        if rolling_window_merge:
            return rolling_window_merge

        similarity = SequenceMatcher(
            None,
            cls._normalize_for_match(existing_text),
            cls._normalize_for_match(hypothesis_text),
        ).ratio()
        if similarity >= 0.72:
            return hypothesis_text
        return f"{existing_text} {hypothesis_text}".strip()

    @classmethod
    def _merge_rolling_window(cls, existing_tokens: list[str], hypothesis_tokens: list[str]) -> str:
        """Replace an overlapping rolling-window region instead of appending it."""
        if not existing_tokens or not hypothesis_tokens:
            return ""

        matcher = SequenceMatcher(
            None,
            [cls._normalize_for_match(token) for token in existing_tokens],
            [cls._normalize_for_match(token) for token in hypothesis_tokens],
            autojunk=False,
        )
        best_match = max(matcher.get_matching_blocks(), key=lambda match: match.size)
        if best_match.size == 0:
            return ""

        hypothesis_coverage = best_match.size / len(hypothesis_tokens)
        existing_coverage = best_match.size / len(existing_tokens)
        has_substantial_overlap = best_match.size >= 5 and (
            hypothesis_coverage >= 0.35 or existing_coverage >= 0.35
        )
        if not has_substantial_overlap:
            return ""

        merged_tokens = existing_tokens[:best_match.a] + hypothesis_tokens[best_match.b:]
        return " ".join(merged_tokens)

    @staticmethod
    def _token_overlap(existing_tokens: list[str], hypothesis_tokens: list[str]) -> int:
        max_overlap = min(len(existing_tokens), len(hypothesis_tokens))
        for length in range(max_overlap, 0, -1):
            left = " ".join(existing_tokens[-length:])
            right = " ".join(hypothesis_tokens[:length])
            if LiveTranscriptManager._normalize_for_match(left) == \
                    LiveTranscriptManager._normalize_for_match(right):
                return length
        return 0

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
