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


def initialize_desktop_runtime(global_vars, config: dict):
    """Initialize the desktop runtime state without launching the UI."""
    ensure_ffmpeg_available()
    initiate_db(global_vars)
    global_vars.initiate_audio_devices(config)
    create_transcriber(
        name=config["General"]["stt"],
        config=config,
        api=bool(config["General"]["use_api"]),
        global_vars=global_vars,
    )
    global_vars.transcriber.set_source_properties(
        mic_source=global_vars.user_audio_recorder.source,
        speaker_source=global_vars.speaker_audio_recorder.source,
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


def start_audio_capture(global_vars):
    """Start microphone and speaker capture threads."""
    user_stop_func = global_vars.user_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.user_audio_recorder.stop_record_func = user_stop_func
    time.sleep(2)
    speaker_stop_func = global_vars.speaker_audio_recorder.record_audio(global_vars.audio_queue)
    global_vars.speaker_audio_recorder.stop_record_func = speaker_stop_func


def initiate_app_threads(global_vars, config: dict):
    """Start all background threads required by the desktop app."""
    global_vars.audio_player_var = AudioPlayer(convo=global_vars.convo)

    transcribe_thread = threading.Thread(
        target=global_vars.transcriber.transcribe_audio_queue,
        name="Transcribe",
        args=(global_vars.audio_queue,),
        daemon=True,
    )
    transcribe_thread.start()

    save_llm_response_to_file: bool = config["General"]["save_llm_response_to_file"]
    data_dir = utilities.get_data_path(app_name="Transcribe")
    llm_response_file = f"{data_dir}/{config['General']['llm_response_file']}"
    chat = config["General"]["chat_inference_provider"]
    global_vars.responder = create_responder(
        provider_name=chat,
        config=config,
        convo=global_vars.convo,
        save_to_file=save_llm_response_to_file,
        response_file_name=llm_response_file,
    )
    if global_vars.responder is None:
        print(f"FATAL: Could not create Chat Reponder for {chat}")
        raise SystemExit(1)
    global_vars.responder.enabled = bool(config["General"]["continuous_response"])

    respond_thread = threading.Thread(
        target=global_vars.responder.respond_to_transcriber,
        name="Respond",
        args=(global_vars.transcriber,),
        daemon=True,
    )
    respond_thread.start()

    audio_response_thread = threading.Thread(
        target=global_vars.audio_player_var.play_audio_loop,
        name="AudioResponse",
        args=(config,),
        daemon=True,
    )
    audio_response_thread.start()

    host_config_thread = threading.Thread(
        target=interactions.HostConfig().host_config_loop,
        name="HostConfig",
        daemon=True,
    )
    host_config_thread.start()

    clear_transcript_thread = threading.Thread(
        target=global_vars.transcriber.clear_transcript_data_loop,
        name="ClearTranscript",
        args=(global_vars.audio_queue,),
        daemon=True,
    )
    clear_transcript_thread.start()

    work_queue_thread = threading.Thread(
        target=global_vars.task_worker.task_exec_thread,
        name="WorkQueue",
        daemon=True,
    )
    work_queue_thread.start()


def initiate_db(global_vars):
    """Set up the application database and initialize the current invocation."""
    adb = AppDB()
    adb.initialize_db(db_context=global_vars.db_context)
    adb.initialize_app()


def shutdown(global_vars):
    """Activities to be performed right before application shutdown."""
    global_vars.user_audio_recorder.write_wav_data_to_file()
    global_vars.speaker_audio_recorder.write_wav_data_to_file()
    AppDB().shutdown_app()
