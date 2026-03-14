"""Desktop runtime orchestration for the Windows application."""

from __future__ import annotations

import threading
import time

try:
    from .. import interactions
    from ..audio_player import AudioPlayer
    from ..db.app_db import AppDB
    from ..providers.llm import create_responder
    from ..providers.stt import create_transcriber, ensure_ffmpeg_available
except ImportError:
    import interactions
    from audio_player import AudioPlayer
    from db.app_db import AppDB
    from providers.llm import create_responder
    from providers.stt import create_transcriber, ensure_ffmpeg_available

from tsutils import utilities


def initialize_desktop_runtime(runtime, config: dict):
    """Initialize the desktop runtime state without launching the UI."""
    ensure_ffmpeg_available()
    initiate_db(runtime)
    runtime.initiate_audio_devices(config)
    create_transcriber(
        name=config["General"]["stt"],
        config=config,
        api=bool(config["General"]["use_api"]),
        runtime=runtime,
    )
    runtime.transcriber.set_source_properties(
        mic_source=runtime.user_audio_recorder.source,
        speaker_source=runtime.speaker_audio_recorder.source,
    )

    data_dir = utilities.get_data_path(app_name="Transcribe")
    utilities.delete_files(
        [
            f"{data_dir}/logs/speaker.wav",
            f"{data_dir}/logs/speaker.wav.bak",
            f"{data_dir}/logs/mic.wav",
            f"{data_dir}/logs/mic.wav.bak",
        ]
    )


def start_audio_capture(runtime):
    """Start microphone and speaker capture threads."""
    user_stop_func = runtime.user_audio_recorder.record_audio(runtime.audio_queue)
    runtime.user_audio_recorder.stop_record_func = user_stop_func
    time.sleep(2)
    speaker_stop_func = runtime.speaker_audio_recorder.record_audio(runtime.audio_queue)
    runtime.speaker_audio_recorder.stop_record_func = speaker_stop_func


def initiate_app_threads(runtime, config: dict):
    """Start all background threads required by the desktop app."""
    runtime.audio_player_var = AudioPlayer(convo=runtime.convo)

    transcribe_thread = threading.Thread(
        target=runtime.transcriber.transcribe_audio_queue,
        name="Transcribe",
        args=(runtime.audio_queue,),
        daemon=True,
    )
    transcribe_thread.start()

    save_llm_response_to_file: bool = config["General"]["save_llm_response_to_file"]
    data_dir = utilities.get_data_path(app_name="Transcribe")
    llm_response_file = f"{data_dir}/{config['General']['llm_response_file']}"
    chat = config["General"]["chat_inference_provider"]
    runtime.responder = create_responder(
        provider_name=chat,
        config=config,
        convo=runtime.convo,
        save_to_file=save_llm_response_to_file,
        response_file_name=llm_response_file,
    )
    if runtime.responder is None:
        print(f"FATAL: Could not create Chat Reponder for {chat}")
        raise SystemExit(1)
    runtime.responder.enabled = bool(config["General"]["continuous_response"])

    respond_thread = threading.Thread(
        target=runtime.responder.respond_to_transcriber,
        name="Respond",
        args=(runtime.transcriber,),
        daemon=True,
    )
    respond_thread.start()

    audio_response_thread = threading.Thread(
        target=runtime.audio_player_var.play_audio_loop,
        name="AudioResponse",
        args=(config,),
        daemon=True,
    )
    audio_response_thread.start()

    host_config_thread = threading.Thread(
        target=interactions.HostConfig(runtime).host_config_loop,
        name="HostConfig",
        daemon=True,
    )
    host_config_thread.start()

    clear_transcript_thread = threading.Thread(
        target=runtime.transcriber.clear_transcript_data_loop,
        name="ClearTranscript",
        args=(runtime.audio_queue,),
        daemon=True,
    )
    clear_transcript_thread.start()

    work_queue_thread = threading.Thread(
        target=runtime.task_worker.task_exec_thread,
        name="WorkQueue",
        daemon=True,
    )
    work_queue_thread.start()


def initiate_db(runtime):
    """Set up the application database and initialize the current invocation."""
    adb = AppDB()
    adb.initialize_db(db_context=runtime.db_context)
    adb.initialize_app()


def shutdown(runtime):
    """Activities to be performed right before application shutdown."""
    runtime.user_audio_recorder.write_wav_data_to_file()
    runtime.speaker_audio_recorder.write_wav_data_to_file()
    AppDB().shutdown_app()
