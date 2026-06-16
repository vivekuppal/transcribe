"""Tests for provider response normalization."""

import unittest
from types import SimpleNamespace

from sdk.transcriber_models import (
    APIWhisperSTTModel,
    DeepgramSTTModel,
    SenseVoiceSTTModel,
    WhisperCPPSTTModel,
    WhisperSTTModel,
)


class TestTranscriptionNormalization(unittest.TestCase):
    def test_whisper_local_segments_are_normalized(self):
        model = object.__new__(WhisperSTTModel)
        response = {
            "text": "First. Second!",
            "segments": [
                {"id": 0, "start": 0.0, "end": 1.0, "text": "First."},
                {"id": 1, "start": 1.0, "end": 2.5, "text": "Second!"},
            ],
        }

        result = model.normalize_response(response, audio_start_seconds=10.0, audio_end_seconds=12.5)

        self.assertEqual(result.provider, "whisper")
        self.assertEqual(result.text, "First. Second!")
        self.assertEqual(result.segments[0].start_seconds, 10.0)
        self.assertEqual(result.segments[-1].end_seconds, 12.5)

    def test_whisper_api_text_only_response_uses_window_segment(self):
        model = object.__new__(APIWhisperSTTModel)
        response = SimpleNamespace(text="One response")

        result = model.normalize_response(response, audio_start_seconds=2.0, audio_end_seconds=5.0)

        self.assertEqual(result.provider, "whisper-api")
        self.assertEqual(result.segments[0].text, "One response")
        self.assertEqual(result.segments[0].start_seconds, 2.0)
        self.assertEqual(result.segments[0].end_seconds, 5.0)

    def test_whispercpp_offsets_are_normalized_from_milliseconds(self):
        model = object.__new__(WhisperCPPSTTModel)
        response = {
            "transcription": [
                {"offsets": {"from": 0, "to": 1200}, "text": "First."},
                {"offsets": {"from": 1200, "to": 3000}, "text": "Second."},
            ]
        }

        result = model.normalize_response(response, audio_start_seconds=4.0, audio_end_seconds=7.0)

        self.assertEqual(result.provider, "whisper.cpp")
        self.assertEqual(result.text, "First.Second.")
        self.assertEqual(result.segments[0].start_seconds, 4.0)
        self.assertEqual(result.segments[-1].end_seconds, 7.0)

    def test_sensevoice_segments_are_normalized(self):
        model = object.__new__(SenseVoiceSTTModel)
        response = {
            "text": "First. Second!",
            "segments": [
                {"id": 0, "start": 0.0, "end": 1.0, "text": "First."},
                {"id": 1, "start": 1.0, "end": 2.0, "text": "Second!"},
            ],
        }

        result = model.normalize_response(response, audio_start_seconds=1.0, audio_end_seconds=3.0)

        self.assertEqual(result.provider, "sensevoice")
        self.assertEqual([segment.text for segment in result.segments], ["First.", "Second!"])
        self.assertEqual(result.segments[0].start_seconds, 1.0)

    def test_deepgram_utterances_are_normalized(self):
        model = object.__new__(DeepgramSTTModel)
        alternative = SimpleNamespace(transcript="First. Second.")
        response = SimpleNamespace(
            results=SimpleNamespace(
                channels=[SimpleNamespace(alternatives=[alternative])],
                utterances=[
                    {"start": 0.0, "end": 1.25, "transcript": "First."},
                    {"start": 1.25, "end": 2.5, "transcript": "Second."},
                ],
            )
        )

        result = model.normalize_response(response, audio_start_seconds=8.0, audio_end_seconds=10.5)

        self.assertEqual(result.provider, "deepgram")
        self.assertEqual(result.text, "First. Second.")
        self.assertEqual(result.segments[0].start_seconds, 8.0)
        self.assertEqual(result.segments[-1].end_seconds, 10.5)


if __name__ == "__main__":
    unittest.main()
