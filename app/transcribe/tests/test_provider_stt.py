"""Unit tests for STT provider composition."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.transcribe.providers import stt


class TestSTTProviders(unittest.TestCase):
    @patch("app.transcribe.providers.stt.WhisperCPPTranscriber")
    @patch("app.transcribe.providers.stt.create_stt_model")
    def test_create_transcriber_injects_whispercpp_preprocessor(self, mock_create_stt_model, mock_transcriber):
        runtime = SimpleNamespace(
            user_audio_recorder=SimpleNamespace(source="mic"),
            speaker_audio_recorder=SimpleNamespace(source="speaker"),
            convo="conversation",
            set_transcriber=MagicMock(),
        )
        transcriber_instance = MagicMock()
        mock_transcriber.return_value = transcriber_instance
        mock_create_stt_model.return_value = "model"

        created = stt.create_transcriber(
            name="whisper.cpp",
            config={"General": {}, "WhisperCpp": {}, "OpenAI": {}},
            api=False,
            runtime=runtime,
        )

        kwargs = mock_transcriber.call_args.kwargs
        self.assertIs(created, transcriber_instance)
        self.assertIn("audio_chunk_preprocessor", kwargs)
        self.assertIsInstance(kwargs["audio_chunk_preprocessor"], stt.WhisperCppAudioPreprocessor)
        runtime.set_transcriber.assert_called_once_with(transcriber_instance)

    @patch("app.transcribe.providers.stt.WhisperTranscriber")
    @patch("app.transcribe.providers.stt.create_stt_model")
    def test_create_transcriber_does_not_inject_preprocessor_for_whisper(self, mock_create_stt_model, mock_transcriber):
        runtime = SimpleNamespace(
            user_audio_recorder=SimpleNamespace(source="mic"),
            speaker_audio_recorder=SimpleNamespace(source="speaker"),
            convo="conversation",
            set_transcriber=MagicMock(),
        )
        transcriber_instance = MagicMock()
        mock_transcriber.return_value = transcriber_instance
        mock_create_stt_model.return_value = "model"

        stt.create_transcriber(
            name="whisper",
            config={"General": {}, "OpenAI": {}},
            api=False,
            runtime=runtime,
        )

        kwargs = mock_transcriber.call_args.kwargs
        self.assertNotIn("audio_chunk_preprocessor", kwargs)


if __name__ == "__main__":
    unittest.main()
