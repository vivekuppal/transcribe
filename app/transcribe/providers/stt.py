"""Speech-to-text provider composition and batch helpers."""

from __future__ import annotations

import os
import subprocess  # nosec
import tempfile
from sdk import transcriber_models as tm

from ..audio_transcriber import DeepgramTranscriber, WhisperCPPTranscriber, WhisperTranscriber
from ..openai_realtime_transcriber import OpenAIRealtimeTranscriber

from tsutils import language, utilities


def get_language_code(lang: str) -> str:
    """Get the language code from the configured language label."""
    lang_lower = lang.lower()
    try:
        return next(key for key, value in language.LANGUAGES_DICT.items() if value == lang_lower)
    except StopIteration:
        return "en"


def ensure_ffmpeg_available():
    """Ensure ffmpeg is installed and available on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],  # nosec
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except FileNotFoundError:
        print("ERROR: The ffmpeg library is not installed. Please install ffmpeg and try again.")
        raise SystemExit(1)


def create_stt_model(name: str, config: dict, api: bool):
    """Create the STT model instance for the selected provider."""
    model_factory = tm.STTModelFactory()

    if name.lower() == "deepgram":
        stt_model_config = {
            "api_key": config["Deepgram"]["api_key"],
            "model": config["Deepgram"].get("model", "nova-3"),
            "audio_lang": get_language_code(config["OpenAI"]["audio_lang"]),
        }
        return model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.DEEPGRAM_API,
            stt_model_config=stt_model_config,
        )

    if name.lower() == "whisper.cpp":
        stt_model_config = {
            "local_transcripton_model_file": "ggml-" + config["WhisperCpp"]["local_transcripton_model_file"],
            "audio_lang": get_language_code(config["OpenAI"]["audio_lang"]),
        }
        return model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_CPP,
            stt_model_config=stt_model_config,
        )

    if name.lower() == "sensevoice":
        sensevoice_config = config.get("SenseVoice", {})
        stt_model_config = {
            "model": sensevoice_config.get("model", "FunAudioLLM/SenseVoiceSmall"),
            "device": sensevoice_config.get("device", "auto"),
            "use_itn": sensevoice_config.get("use_itn", True),
            "audio_lang": get_language_code(config["OpenAI"]["audio_lang"]),
        }
        return model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.SENSEVOICE_LOCAL,
            stt_model_config=stt_model_config,
        )

    if name.lower() == "whisper" and not api:
        stt_model_config = {
            "api_key": config["OpenAI"]["api_key"],
            "local_transcripton_model_file": config["OpenAI"]["local_transcripton_model_file"],
            "audio_lang": get_language_code(config["OpenAI"]["audio_lang"]),
            "local_engine": config["General"].get("local_engine", "auto"),
        }
        return model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_LOCAL,
            stt_model_config=stt_model_config,
        )

    if name.lower() == "whisper" and api:
        stt_model_config = {
            "api_key": config["OpenAI"]["api_key"],
            "timeout": config["OpenAI"]["response_request_timeout_seconds"],
            "model": config["OpenAI"].get("stt_model") or "whisper-1",
            "audio_lang": get_language_code(config["OpenAI"]["audio_lang"]),
        }
        return model_factory.get_stt_model_instance(
            stt_model=tm.STTEnum.WHISPER_API,
            stt_model_config=stt_model_config,
        )

    raise ValueError(f"Unknown transcriber: {name}")


def create_transcriber(name: str, config: dict, api: bool, runtime):
    """Create the application transcriber for the selected STT provider."""
    if name.lower() == "openai-realtime":
        transcriber = OpenAIRealtimeTranscriber(
            runtime.user_audio_recorder.source,
            runtime.speaker_audio_recorder.source,
            convo=runtime.convo,
            config=config,
        )
        runtime.set_transcriber(transcriber)
        return transcriber

    model = create_stt_model(name=name, config=config, api=api)

    if name.lower() == "deepgram":
        transcriber = DeepgramTranscriber(
            runtime.user_audio_recorder.source,
            runtime.speaker_audio_recorder.source,
            model,
            convo=runtime.convo,
            config=config,
        )
    elif name.lower() == "whisper.cpp":
        transcriber = WhisperCPPTranscriber(
            runtime.user_audio_recorder.source,
            runtime.speaker_audio_recorder.source,
            model,
            convo=runtime.convo,
            config=config,
        )
    else:
        transcriber = WhisperTranscriber(
            runtime.user_audio_recorder.source,
            runtime.speaker_audio_recorder.source,
            model,
            convo=runtime.convo,
            config=config,
        )

    runtime.set_transcriber(transcriber)
    return transcriber


def convert_audio_to_16khz(file_path: str) -> str:
    """Convert an input wav file to the format required by whisper.cpp."""
    ensure_ffmpeg_available()
    file_descriptor, mod_file_path = tempfile.mkstemp(suffix=".wav")
    os.close(file_descriptor)
    log_file = f"{utilities.get_data_path(app_name='Transcribe')}/logs/ffmpeg.txt"
    with open(file=log_file, mode="a", encoding="utf-8") as log_handle:
        subprocess.call(
            ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-y", mod_file_path],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
    return mod_file_path
