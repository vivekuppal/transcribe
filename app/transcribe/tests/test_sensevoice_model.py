"""Tests for the optional SenseVoiceSmall STT adapter."""

import os
import sys
import tempfile
import types
import unittest
import wave
from unittest.mock import MagicMock, patch

from sdk.transcriber_models import SenseVoiceSTTModel


class TestSenseVoiceSTTModel(unittest.TestCase):
    def test_normalize_language_falls_back_to_auto(self):
        self.assertEqual(SenseVoiceSTTModel._normalize_language("English"), "en")
        self.assertEqual(SenseVoiceSTTModel._normalize_language("French"), "auto")

    def test_sentence_segments_cover_full_audio_duration(self):
        segments = SenseVoiceSTTModel._sentence_segments("First. Second!", 12.0)

        self.assertEqual([segment["text"] for segment in segments], ["First.", "Second!"])
        self.assertEqual(segments[0]["start"], 0.0)
        self.assertEqual(segments[-1]["end"], 12.0)

    def test_lazy_optional_import_and_response_normalization(self):
        auto_model = MagicMock()
        audio_model = auto_model.return_value
        audio_model.generate.return_value = [{"text": "<|en|>Hello world."}]

        funasr_module = types.ModuleType("funasr")
        funasr_module.AutoModel = auto_model
        utils_module = types.ModuleType("funasr.utils")
        postprocess_module = types.ModuleType("funasr.utils.postprocess_utils")
        postprocess_module.rich_transcription_postprocess = lambda text: text.replace("<|en|>", "")

        with patch.dict(
            sys.modules,
            {
                "funasr": funasr_module,
                "funasr.utils": utils_module,
                "funasr.utils.postprocess_utils": postprocess_module,
            },
        ):
            model = SenseVoiceSTTModel(
                {"audio_lang": "English", "device": "cpu", "use_itn": True}
            )

        auto_model.assert_called_once_with(
            model="FunAudioLLM/SenseVoiceSmall",
            vad_model="fsmn-vad",
            hub="hf",
            disable_pbar=True,
            vad_kwargs={"max_single_segment_time": 30000},
            device="cpu",
        )

        file_descriptor, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(file_descriptor)
        try:
            with wave.open(wav_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 16000)

            response = model.get_transcription(wav_path)
        finally:
            os.unlink(wav_path)

        self.assertEqual(response["text"], "Hello world.")
        self.assertEqual(response["segments"][0]["end"], 1.0)
        audio_model.generate.assert_called_once_with(
            input=wav_path,
            cache={},
            language="en",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )


if __name__ == "__main__":
    unittest.main()
