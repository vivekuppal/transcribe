import queue
import datetime
import tkinter as tk
import customtkinter as ctk
from AudioTranscriber import AudioTranscriber
from audio_player import AudioPlayer
import AudioRecorder
from tsutils import Singleton, task_queue, utilities
import app_logging as al
import conversation


root_logger = al.get_logger()


class TranscriptionGlobals(Singleton.Singleton):
    """Global constants for audio processing. It is implemented as a Singleton class.
    """

    audio_queue: queue.Queue = None
    user_audio_recorder: AudioRecorder.MicRecorder = None
    speaker_audio_recorder: AudioRecorder.SpeakerRecorder = None
    audio_player: AudioPlayer = None
    # Global for transcription from speaker, microphone
    transcriber: AudioTranscriber = None
    # Global for responses from openAI API
    responder = None
    freeze_button: ctk.CTkButton = None
    # Update_response_now is true when we are waiting for a one time immediate response to query
    update_response_now: bool = False
    # Read response in voice
    read_response: bool = False
    editmenu: tk.Menu = None
    filemenu: tk.Menu = None
    update_interval_slider_label: ctk.CTkLabel = None
    response_textbox: ctk.CTkTextbox = None
    start: datetime.datetime = None
    task_worker = None

    convo: conversation.Conversation = None
    _initialized: bool = None

    def __init__(self):
        root_logger.info(TranscriptionGlobals.__name__)
        if self._initialized:
            return
        if self.audio_queue is None:
            self.audio_queue = queue.Queue()
        if self.user_audio_recorder is None:
            self.user_audio_recorder = AudioRecorder.MicRecorder()
        if self.speaker_audio_recorder is None:
            self.speaker_audio_recorder = AudioRecorder.SpeakerRecorder()
        self.start = datetime.datetime.now()
        self.task_worker = task_queue.TaskQueue()
        zip_file_name = utilities.incrementing_filename(filename='logs/transcript', extension='zip')
        zip_params = {
            'task_type': task_queue.TaskQueueEnum.ZIP_TASK,
            'folder_path': './logs',
            'zip_file_name': zip_file_name,
            'skip_zip_files': True
        }
        self.task_worker.add(**zip_params)

        self._initialized = True
