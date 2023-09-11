import os
import queue
from heapq import merge
import threading
import platform
import io
import datetime
# import pprint
import wave
import tempfile
import conversation
import constants
import app_logging as al

os_name = platform.system()
if os_name == 'Windows':
    import custom_speech_recognition as csr
    import pyaudiowpatch as pyaudio
if os_name == 'Darwin':
    import speech_recognition as sr
    import pyaudio


PHRASE_TIMEOUT = 3.05
root_logger = al.get_logger()


class AudioTranscriber:
    def __init__(self, mic_source, speaker_source, model, convo: conversation.Conversation):
        root_logger.info(AudioTranscriber.__name__)
        # Transcript_data should be replaced with the conversation object.
        # We do not need to store transcription in 2 different places.
        self.transcript_data = {"You": [], "Speaker": []}
        self.transcript_changed_event = threading.Event()
        self.audio_model = model
        # Determines if transcription is enabled for the application. By default it is enabled.
        self.transcribe = True
        self.os_name = platform.system()

        if self.os_name == 'Windows':
            self.audio_sources = {
                "You": {
                    "sample_rate": mic_source.SAMPLE_RATE,
                    "sample_width": mic_source.SAMPLE_WIDTH,
                    "channels": mic_source.channels,
                    "last_sample": bytes(),
                    "last_spoken": None,
                    "new_phrase": True,
                    "process_data_func": self.process_mic_data
                },
                "Speaker": {
                    "sample_rate": speaker_source.SAMPLE_RATE,
                    "sample_width": speaker_source.SAMPLE_WIDTH,
                    "channels": speaker_source.channels,
                    "last_sample": bytes(),
                    "last_spoken": None,
                    "new_phrase": True,
                    "process_data_func": self.process_speaker_data
                }
            }
        elif self.os_name == 'Darwin':
            self.audio_sources = {
                "You": {
                    "sample_rate": mic_source.SAMPLE_RATE,
                    "sample_width": mic_source.SAMPLE_WIDTH,
                    # "channels": mic_source.channels,
                    "last_sample": bytes(),
                    "last_spoken": None,
                    "new_phrase": True,
                    "process_data_func": self.process_mic_data
                },
                "Speaker": {
                    "sample_rate": speaker_source.SAMPLE_RATE,
                    "sample_width": speaker_source.SAMPLE_WIDTH,
                    # "channels": speaker_source.channels,
                    "last_sample": bytes(),
                    "last_spoken": None,
                    "new_phrase": True,
                    "process_data_func": self.process_speaker_data
                }
            }

        self.conversation = convo

    def transcribe_audio_queue(self, audio_queue: queue.Queue):
        """Transcribe data from audio sources. In this case we have 2 sources, microphone, speaker.
        Args:
          audio_queue: queue object with reference to audio files

        """
        while True:
            who_spoke, data, time_spoken = audio_queue.get()
            self.update_last_sample_and_phrase_status(who_spoke, data, time_spoken)
            source_info = self.audio_sources[who_spoke]

            text = ''
            try:
                file_descritor, path = tempfile.mkstemp(suffix=".wav")
                os.close(file_descritor)
                source_info["process_data_func"](source_info["last_sample"], path)
                if self.transcribe:
                    text = self.audio_model.get_transcription(path)
            except Exception as exception:
                print(exception)
            finally:
                os.unlink(path)

            if text != '' and text.lower() != 'you':
                self.update_transcript(who_spoke, text, time_spoken)
                self.transcript_changed_event.set()

    def update_last_sample_and_phrase_status(self, who_spoke, data, time_spoken):
        root_logger.info(AudioTranscriber.update_last_sample_and_phrase_status.__name__)
        if not self.transcribe:
            return
        source_info = self.audio_sources[who_spoke]
        if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] > datetime.timedelta(seconds=PHRASE_TIMEOUT):
            source_info["last_sample"] = bytes()
            source_info["new_phrase"] = True
        else:
            source_info["new_phrase"] = False

        source_info["last_sample"] += data
        source_info["last_spoken"] = time_spoken

    def process_mic_data(self, data, temp_file_name):
        root_logger.info(AudioTranscriber.process_mic_data.__name__)
        if not self.transcribe:
            return
        if self.os_name == 'Windows':
            audio_data = csr.AudioData(data, self.audio_sources["You"]["sample_rate"], self.audio_sources["You"]["sample_width"])
        elif self.os_name == 'Darwin':
            audio_data = sr.AudioData(data, self.audio_sources["You"]["sample_rate"], self.audio_sources["You"]["sample_width"])
        wav_data = io.BytesIO(audio_data.get_wav_data())
        with open(temp_file_name, 'w+b') as file_handle:
            file_handle.write(wav_data.read())

    def process_speaker_data(self, data, temp_file_name):
        root_logger.info(AudioTranscriber.process_speaker_data.__name__)
        if not self.transcribe:
            return
        with wave.open(temp_file_name, 'wb') as wf:
            if self.os_name == 'Windows':
                wf.setnchannels(self.audio_sources["Speaker"]["channels"])
                p = pyaudio.PyAudio()
            if self.os_name == 'Darwin':
                p = pyaudio.PyAudio()

            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.audio_sources["Speaker"]["sample_rate"])
            wf.writeframes(data)

    def update_transcript(self, who_spoke, text, time_spoken):
        """Update transcript with new data
        Args:
        who_spoke: Person this audio is attributed to
        text: Actual spoken words
        time_spoken: Time at which audio was taken, relative to start time
        """
        source_info = self.audio_sources[who_spoke]
        transcript = self.transcript_data[who_spoke]

        if source_info["new_phrase"] or len(transcript) == 0:
            transcript.append((f"{who_spoke}: [{text}]\n\n", time_spoken))
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text)
        else:
            transcript.pop()
            transcript.append((f"{who_spoke}: [{text}]\n\n", time_spoken))
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text, pop=True)

    def get_transcript(self, length: int = 0):
        """Get the audio transcript
        Args:
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript
        """
        # This data should be retrieved from the conversation object.
        combined_transcript = list(merge(
            self.transcript_data["You"], self.transcript_data["Speaker"],
            key=lambda x: x[1], reverse=False))
        combined_transcript = combined_transcript[-length:]
        # current_return_val = "".join([t[0] for t in combined_transcript])
        sources = [
            constants.PERSONA_YOU,
            constants.PERSONA_SPEAKER
            ]
        convo_object_return_value = self.conversation.get_conversation(sources=sources)
        # print('---------- AudioTranscriber.py get_transcript convo object----------')
        # pprint.pprint(convo_object_return_value, width=120)

        # print('---------- AudioTranscriber.py get_transcript current implementation----------')
        # pprint.pprint(current_return_val, width=120)

        return convo_object_return_value

    def clear_transcript_data(self):
        """
        Args:
        length: Clear all data stored internally for audio transcript
        """
        self.transcript_data["You"].clear()
        self.transcript_data["Speaker"].clear()

        self.audio_sources["You"]["last_sample"] = bytes()
        self.audio_sources["Speaker"]["last_sample"] = bytes()

        self.audio_sources["You"]["new_phrase"] = True
        self.audio_sources["Speaker"]["new_phrase"] = True

        self.conversation.clear_conversation_data()
