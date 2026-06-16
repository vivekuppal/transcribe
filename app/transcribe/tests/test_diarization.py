"""Unit tests for optional diarization helpers."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from app.transcribe.diarization import (
    DiarizationTurn,
    PyannoteDiarizationService,
    annotate_hypothesis_with_turns,
    create_diarization_service,
)
from sdk.transcription_result import TranscriptSegment, TranscriptionHypothesis


class TestDiarizationHelpers(unittest.TestCase):
    def test_create_diarization_service_defaults_to_disabled(self):
        service = create_diarization_service({})

        self.assertFalse(service.enabled)

    def test_annotate_hypothesis_assigns_largest_overlap_speaker(self):
        hypothesis = TranscriptionHypothesis(
            provider="test",
            text="first second",
            segments=[
                TranscriptSegment(0, 0.0, 1.0, "first"),
                TranscriptSegment(1, 1.0, 2.0, "second"),
            ],
            audio_start_seconds=0.0,
            audio_end_seconds=2.0,
        )
        turns = [
            DiarizationTurn(0.0, 1.2, "SPEAKER_00"),
            DiarizationTurn(1.2, 2.0, "SPEAKER_01"),
        ]

        annotated = annotate_hypothesis_with_turns(hypothesis, turns)

        self.assertEqual([segment.speaker for segment in annotated.segments], ["SPEAKER_00", "SPEAKER_01"])
        self.assertEqual(hypothesis.segments[0].speaker, None)

    def test_pyannote_warm_up_loads_pipeline(self):
        class FakePyannoteService(PyannoteDiarizationService):
            def __init__(self):
                super().__init__()
                self.load_count = 0

            def _get_pipeline(self):
                self.load_count += 1
                return object()

        service = FakePyannoteService()

        service.warm_up()

        self.assertEqual(service.load_count, 1)

    def test_pyannote_diarize_passes_preloaded_audio_to_pipeline(self):
        class FakeSegment:
            start = 0.0
            end = 1.0

        class FakeAnnotation:
            def __init__(self, speaker):
                self.speaker = speaker

            def itertracks(self, yield_label=False):
                yield FakeSegment(), None, self.speaker

        class FakeDiarizationOutput:
            speaker_diarization = FakeAnnotation("SPEAKER_00")
            exclusive_speaker_diarization = FakeAnnotation("SPEAKER_01")

        class FakePipeline:
            def __init__(self):
                self.input = None

            def __call__(self, audio):
                self.input = audio
                return FakeDiarizationOutput()

        class FakePyannoteService(PyannoteDiarizationService):
            def __init__(self, pipeline):
                super().__init__()
                self.pipeline = pipeline

            def _get_pipeline(self):
                return self.pipeline

        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "sample.wav"
            sf.write(wav_path, np.zeros(1600, dtype=np.float32), 16000)
            pipeline = FakePipeline()
            service = FakePyannoteService(pipeline)

            turns = service.diarize(str(wav_path), audio_start_seconds=5.0)

        self.assertIn("waveform", pipeline.input)
        self.assertIn("sample_rate", pipeline.input)
        self.assertEqual(pipeline.input["sample_rate"], 16000)
        self.assertEqual(turns, [DiarizationTurn(5.0, 6.0, "SPEAKER_01")])

    def test_extract_annotation_supports_legacy_annotation_output(self):
        class FakeAnnotation:
            def itertracks(self, yield_label=False):
                return iter(())

        annotation = FakeAnnotation()

        self.assertIs(PyannoteDiarizationService._extract_annotation(annotation), annotation)

    def test_load_audio_returns_channel_first_waveform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "sample.wav"
            sf.write(wav_path, np.zeros((1600, 2), dtype=np.float32), 16000)

            audio = PyannoteDiarizationService._load_audio(str(wav_path))

        self.assertEqual(audio["sample_rate"], 16000)
        self.assertEqual(tuple(audio["waveform"].shape), (2, 1600))


if __name__ == "__main__":
    unittest.main()
