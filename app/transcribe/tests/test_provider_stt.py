"""Unit tests for STT provider composition."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.transcribe.providers import stt


class TestSTTProviders(unittest.TestCase):
    @patch("app.transcribe.providers.stt.tm.STTModelFactory")
    def test_create_deepgram_model_uses_configured_nova3_model(self, mock_factory_class):
        factory = mock_factory_class.return_value
        factory.get_stt_model_instance.return_value = "deepgram-model"
        config = {
            "OpenAI": {"audio_lang": "English"},
            "Deepgram": {
                "api_key": "key",
                "model": "nova-3",
            },
        }

        model = stt.create_stt_model(name="deepgram", config=config, api=True)

        self.assertEqual(model, "deepgram-model")
        factory.get_stt_model_instance.assert_called_once_with(
            stt_model=stt.tm.STTEnum.DEEPGRAM_API,
            stt_model_config={
                "api_key": "key",
                "model": "nova-3",
                "audio_lang": "en",
            },
        )

    @patch("app.transcribe.providers.stt.tm.STTModelFactory")
    def test_create_deepgram_model_defaults_to_nova3(self, mock_factory_class):
        factory = mock_factory_class.return_value
        factory.get_stt_model_instance.return_value = "deepgram-model"
        config = {
            "OpenAI": {"audio_lang": "English"},
            "Deepgram": {"api_key": "key"},
        }

        stt.create_stt_model(name="deepgram", config=config, api=True)

        factory.get_stt_model_instance.assert_called_once_with(
            stt_model=stt.tm.STTEnum.DEEPGRAM_API,
            stt_model_config={
                "api_key": "key",
                "model": "nova-3",
                "audio_lang": "en",
            },
        )

    @patch("app.transcribe.providers.stt.tm.STTModelFactory")
    def test_create_sensevoice_model_uses_optional_configuration(self, mock_factory_class):
        factory = mock_factory_class.return_value
        factory.get_stt_model_instance.return_value = "sensevoice-model"
        config = {
            "OpenAI": {"audio_lang": "English"},
            "SenseVoice": {
                "model": "FunAudioLLM/SenseVoiceSmall",
                "device": "cpu",
                "use_itn": False,
            },
        }

        model = stt.create_stt_model(name="sensevoice", config=config, api=False)

        self.assertEqual(model, "sensevoice-model")
        factory.get_stt_model_instance.assert_called_once_with(
            stt_model=stt.tm.STTEnum.SENSEVOICE_LOCAL,
            stt_model_config={
                "model": "FunAudioLLM/SenseVoiceSmall",
                "device": "cpu",
                "use_itn": False,
                "audio_lang": "en",
            },
        )

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
