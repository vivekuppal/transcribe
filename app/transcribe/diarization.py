"""Optional speaker diarization helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
import warnings

from sdk.transcription_result import TranscriptSegment, TranscriptionHypothesis


DEFAULT_PYANNOTE_MODEL = "pyannote/speaker-diarization-community-1"


@dataclass(frozen=True)
class DiarizationTurn:
    """A speaker-labeled time range."""

    start_seconds: float
    end_seconds: float
    speaker: str


class DiarizationService:
    """Base interface for optional diarization services."""

    enabled = False

    def warm_up(self):
        """Load any model resources needed before live transcription begins."""

    def diarize(self, wav_file_path: str, audio_start_seconds: float = 0.0) -> list[DiarizationTurn]:
        """Return speaker turns for the given WAV file."""
        return []

    def annotate_hypothesis(
        self,
        wav_file_path: str,
        hypothesis: TranscriptionHypothesis,
    ) -> TranscriptionHypothesis:
        """Attach speaker labels to a transcription hypothesis."""
        if not self.enabled or not hypothesis.segments:
            return hypothesis

        turns = self.diarize(wav_file_path, audio_start_seconds=hypothesis.audio_start_seconds)
        if not turns:
            return hypothesis

        return annotate_hypothesis_with_turns(hypothesis, turns)


class PyannoteDiarizationService(DiarizationService):
    """Pyannote.audio-backed diarization service."""

    enabled = True

    def __init__(
        self,
        model_name: str = DEFAULT_PYANNOTE_MODEL,
        auth_token: str | None = None,
        device: str = "auto",
    ):
        self.model_name = model_name
        self.auth_token = auth_token
        self.device = device
        self._pipeline = None

    def diarize(self, wav_file_path: str, audio_start_seconds: float = 0.0) -> list[DiarizationTurn]:
        pipeline = self._get_pipeline()
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"std\(\): degrees of freedom is <= 0.*",
                category=UserWarning,
            )
            warnings.filterwarnings(
                "ignore",
                message=r"Mean of empty slice",
                category=RuntimeWarning,
            )
            warnings.filterwarnings(
                "ignore",
                message=r"invalid value encountered in divide",
                category=RuntimeWarning,
            )
            diarization_output = pipeline(self._load_audio(wav_file_path))

        diarization = self._extract_annotation(diarization_output)
        if diarization is None:
            return []

        turns = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            turns.append(
                DiarizationTurn(
                    start_seconds=audio_start_seconds + float(segment.start),
                    end_seconds=audio_start_seconds + float(segment.end),
                    speaker=str(speaker),
                )
            )
        return turns

    def warm_up(self):
        """Load the pyannote pipeline and model before transcription starts."""
        self._get_pipeline()

    @staticmethod
    def _extract_annotation(diarization_output):
        """Return a pyannote Annotation from pipeline outputs across pyannote versions."""
        if hasattr(diarization_output, "itertracks"):
            return diarization_output
        if hasattr(diarization_output, "exclusive_speaker_diarization"):
            return diarization_output.exclusive_speaker_diarization
        if hasattr(diarization_output, "speaker_diarization"):
            return diarization_output.speaker_diarization
        if hasattr(diarization_output, "diarization"):
            return diarization_output.diarization
        return None

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            import torch
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"\s*torchcodec is not installed correctly.*",
                    category=UserWarning,
                )
                from pyannote.audio import Pipeline
        except ImportError as exception:
            raise RuntimeError(
                "Diarization is enabled, but pyannote.audio is not installed. "
                "Install app/transcribe/requirements-diarization.txt first."
            ) from exception

        try:
            self._pipeline = Pipeline.from_pretrained(self.model_name, token=self.auth_token)
        except TypeError:
            self._pipeline = Pipeline.from_pretrained(self.model_name, use_auth_token=self.auth_token)

        device_name = self.device
        if device_name == "auto":
            device_name = "cuda" if torch.cuda.is_available() else "cpu"
        self._pipeline.to(torch.device(device_name))
        return self._pipeline

    @staticmethod
    def _load_audio(wav_file_path: str) -> dict:
        """Load audio explicitly so pyannote does not depend on torchcodec decoding."""
        try:
            import soundfile as sf
            import torch
        except ImportError as exception:
            raise RuntimeError(
                "Diarization requires soundfile and torch. "
                "Install app/transcribe/requirements-diarization.txt first."
            ) from exception

        audio, sample_rate = sf.read(wav_file_path, always_2d=True, dtype="float32")
        waveform = torch.from_numpy(audio.T)
        return {"waveform": waveform, "sample_rate": sample_rate}


def create_diarization_service(config: dict) -> DiarizationService:
    """Create the configured optional diarization service."""
    diarization_config = config.get("Diarization", {})
    enabled = bool(diarization_config.get("enabled", False))
    if not enabled:
        return DiarizationService()

    provider = str(diarization_config.get("provider", "pyannote")).lower()
    if provider != "pyannote":
        raise ValueError(f"Unsupported diarization provider: {provider}")

    auth_token = diarization_config.get("huggingface_token") or os.environ.get("HUGGINGFACE_TOKEN")
    return PyannoteDiarizationService(
        model_name=diarization_config.get("model", DEFAULT_PYANNOTE_MODEL),
        auth_token=auth_token,
        device=diarization_config.get("device", "auto"),
    )


def annotate_hypothesis_with_turns(
    hypothesis: TranscriptionHypothesis,
    turns: list[DiarizationTurn],
) -> TranscriptionHypothesis:
    """Assign each transcript segment to the overlapping diarization speaker."""
    annotated_segments = [
        replace(segment, speaker=_best_speaker_for_segment(segment, turns))
        for segment in hypothesis.segments
    ]
    return replace(hypothesis, segments=annotated_segments)


def _best_speaker_for_segment(segment: TranscriptSegment, turns: list[DiarizationTurn]) -> str | None:
    best_speaker = None
    best_overlap = 0.0
    for turn in turns:
        overlap = min(segment.end_seconds, turn.end_seconds) - max(segment.start_seconds, turn.start_seconds)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn.speaker
    return best_speaker
