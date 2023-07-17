import queue
from AudioTranscriber import AudioTranscriber
from GPTResponder import GPTResponder
import AudioRecorder
import customtkinter as ctk


class TranscriptionGlobals(object):
    # Global constants for audio processing. It is implemented as a singleton

    audio_queue: queue.Queue = None
    user_audio_recorder: AudioRecorder.DefaultMicRecorder = None
    speaker_audio_recorder: AudioRecorder.DefaultSpeakerRecorder = None
    # Global for transcription from speaker, microphone
    transcriber: AudioTranscriber = None
    # Global for responses from openAI API
    responder: GPTResponder = None
    # Global for determining whether to seek responses from openAI API
    freeze_state: list = None
    freeze_button: ctk.CTkButton = None
    transcript_button: ctk.CTkButton = None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TranscriptionGlobals, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.audio_queue = queue.Queue()
        self.user_audio_recorder = AudioRecorder.DefaultMicRecorder()
        self.speaker_audio_recorder = AudioRecorder.DefaultSpeakerRecorder()
