"""Optional real-provider smoke tests for normalized live transcription output."""

from pathlib import Path
import os
import unittest


RUN_SMOKE = os.environ.get("TRANSCRIBE_REAL_STT_SMOKE") == "1"
ROOT_DIR = Path(__file__).resolve().parents[3]
FIXTURE_WAV = ROOT_DIR / "tests" / "english.wav"


@unittest.skipUnless(RUN_SMOKE, "Set TRANSCRIBE_REAL_STT_SMOKE=1 to run real STT smoke tests.")
class TestOptionalRealProviderSmoke(unittest.TestCase):
    def _assert_sane_hypothesis(self, hypothesis):
        self.assertTrue(hypothesis.text.strip())
        self.assertGreaterEqual(hypothesis.audio_end_seconds, hypothesis.audio_start_seconds)
        self.assertTrue(hypothesis.segments)
        self.assertGreaterEqual(hypothesis.segments[-1].end_seconds, hypothesis.segments[0].start_seconds)

    def test_whisper_local_smoke(self):
        from sdk import transcriber_models as tm

        model_file = tm.MODELS_DIR + "base.pt"
        if not Path(model_file).exists():
            self.skipTest("Whisper base model is not available locally.")

        model = tm.WhisperSTTModel(
            {
                "local_transcripton_model_file": "base",
                "audio_lang": "en",
                "api_key": "",
            }
        )
        response = model.get_transcription(str(FIXTURE_WAV))
        self._assert_sane_hypothesis(model.normalize_response(response, 0.0, 3.0))

    def test_whispercpp_smoke(self):
        from sdk import transcriber_models as tm
        from app.transcribe.providers.stt import convert_audio_to_16khz

        if not (ROOT_DIR / "bin" / "main.exe").exists():
            self.skipTest("whisper.cpp binary is not available.")
        model_file = tm.MODELS_DIR + "ggml-base.bin"
        if not Path(model_file).exists():
            self.skipTest("whisper.cpp base model is not available locally.")

        model = tm.WhisperCPPSTTModel(
            {
                "local_transcripton_model_file": "ggml-base",
                "audio_lang": "en",
            }
        )
        converted_path = convert_audio_to_16khz(str(FIXTURE_WAV))
        try:
            response = model.get_transcription(converted_path)
            self._assert_sane_hypothesis(model.normalize_response(response, 0.0, 3.0))
        finally:
            converted_file = Path(converted_path)
            if converted_file.exists():
                converted_file.unlink()
            json_file = Path(converted_path + ".json")
            if json_file.exists():
                json_file.unlink()

    def test_sensevoice_smoke(self):
        from sdk import transcriber_models as tm

        try:
            import funasr  # pylint: disable=import-outside-toplevel, unused-import
        except ImportError:
            self.skipTest("SenseVoice optional dependencies are not installed.")

        model = tm.SenseVoiceSTTModel(
            {
                "model": "FunAudioLLM/SenseVoiceSmall",
                "device": "cpu",
                "use_itn": True,
                "audio_lang": "en",
            }
        )
        response = model.get_transcription(str(FIXTURE_WAV))
        self._assert_sane_hypothesis(model.normalize_response(response, 0.0, 3.0))

    def test_whisper_api_smoke(self):
        from sdk import transcriber_models as tm

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.skipTest("OPENAI_API_KEY is not set.")

        model = tm.APIWhisperSTTModel(
            {
                "api_key": api_key,
                "timeout": 30,
                "audio_lang": "en",
            }
        )
        response = model.get_transcription(str(FIXTURE_WAV))
        self._assert_sane_hypothesis(model.normalize_response(response, 0.0, 3.0))

    def test_deepgram_smoke(self):
        from sdk import transcriber_models as tm

        api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not api_key:
            self.skipTest("DEEPGRAM_API_KEY is not set.")

        model = tm.DeepgramSTTModel(
            {
                "api_key": api_key,
                "audio_lang": "en",
            }
        )
        response = model.get_transcription(str(FIXTURE_WAV))
        self._assert_sane_hypothesis(model.normalize_response(response, 0.0, 3.0))


if __name__ == "__main__":
    unittest.main()
