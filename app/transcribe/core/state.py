"""Core application state shared across the desktop runtime."""

from __future__ import annotations

import os
import queue
import datetime
from typing import TYPE_CHECKING

try:
    from .conversation import Conversation
except ImportError:
    from core.conversation import Conversation

from tsutils import Singleton, task_queue, utilities

try:
    from ..sdk import audio_recorder as ar
except ImportError:
    from sdk import audio_recorder as ar

if TYPE_CHECKING:
    try:
        from ..audio_player import AudioPlayer
        from ..audio_transcriber import AudioTranscriber
    except ImportError:
        from audio_player import AudioPlayer
        from audio_transcriber import AudioTranscriber


class TranscriptionGlobals(Singleton.Singleton):
    """Shared runtime state for the application."""

    audio_queue: queue.Queue = None
    user_audio_recorder: ar.MicRecorder = None
    speaker_audio_recorder: ar.SpeakerRecorder = None
    audio_player_var: "AudioPlayer" = None
    transcriber: "AudioTranscriber" = None
    responder = None
    update_response_now: bool = False
    read_response: bool = False
    previous_response: str = None
    start: datetime.datetime = None
    task_worker = None
    main_window = None
    data_dir = None
    db_file_path: str = None
    current_working_dir: str = None
    db_context: dict = None
    convo: Conversation = None
    _initialized: bool = None

    def __init__(self):
        if self._initialized:
            return

        if self.audio_queue is None:
            self.audio_queue = queue.Queue()

        self.convo = Conversation(self)
        self.start = datetime.datetime.now()
        self.task_worker = task_queue.TaskQueue()
        self.data_dir = utilities.get_data_path(app_name="Transcribe")

        zip_file_name = utilities.incrementing_filename(
            filename=f"{self.data_dir}/logs/transcript",
            extension="zip",
        )
        zip_params = {
            "task_type": task_queue.TaskQueueEnum.ZIP_TASK,
            "folder_path": f"{self.data_dir}/logs",
            "zip_file_name": zip_file_name,
            "skip_zip_files": True,
        }
        self.task_worker.add(**zip_params)
        self.current_working_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        utilities.ensure_directory_exists(f"{self.data_dir}/logs")
        db_log_file = utilities.incrementing_filename(
            filename=f"{self.data_dir}/logs/db",
            extension="log",
        )
        self.db_file_path = f"{self.data_dir}/logs/app.db"
        self.db_context = {
            "db_file_path": self.db_file_path,
            "current_working_dir": self.current_working_dir,
            "db_log_file": db_log_file,
        }
        self._initialized = True

    def set_transcriber(self, transcriber):
        """Set the transcriber used across the application."""
        self.transcriber = transcriber

    def initiate_audio_devices(self, config: dict):
        """Initialize the active microphone and speaker devices."""
        print("[INFO] Using default microphone.")
        data_dir = utilities.get_data_path(app_name="Transcribe")
        self.user_audio_recorder = ar.MicRecorder(audio_file_name=f"{data_dir}/logs/mic.wav")
        if not config["General"]["disable_mic"] and config["General"]["mic_device_index"] != -1:
            print("[INFO] Override default microphone with device specified in parameters file.")
            self.user_audio_recorder.set_device(index=int(config["General"]["mic_device_index"]))

        print("[INFO] Using default speaker.")
        self.speaker_audio_recorder = ar.SpeakerRecorder(audio_file_name=f"{data_dir}/logs/speaker.wav")
        if not config["General"]["disable_speaker"] and config["General"]["speaker_device_index"] != -1:
            print("[INFO] Override default speaker with device specified in parameters file.")
            self.speaker_audio_recorder.set_device(index=int(config["General"]["speaker_device_index"]))

    def set_read_response(self, value: bool):
        """Signal that the current response should be read aloud."""
        self.read_response = value
        if self.audio_player_var is not None:
            self.audio_player_var.read_response = value


T_GLOBALS = TranscriptionGlobals()
