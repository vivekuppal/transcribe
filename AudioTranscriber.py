import os
import queue
import time
import threading
import io
import datetime
from abc import abstractmethod
# import pprint
import wave
import tempfile
import pyaudiowpatch as pyaudio
import custom_speech_recognition as sr
import conversation
import constants
import app_logging as al
import duration


# There can be prompts for speech to text aspects as well, that have not been considered as yet.
# See the prompting section here https://platform.openai.com/docs/guides/speech-to-text/prompting

# pylint: disable=logging-fstring-interpolation
PHRASE_TIMEOUT = 3.05
root_logger = al.get_logger()
WHISPER_SEGMENT_PRUNE_THRESHOLD = 6  # Attempt to prune after these number of segments in transcription
AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS = 45  # Duration of audio (seconds) after which force pruning


class AudioTranscriber:   # pylint: disable=C0115, R0902
    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation,
                 config: dict):
        root_logger.info(AudioTranscriber.__name__)
        # Transcript_data should be replaced with the conversation object.
        # We do not need to store transcription in 2 different places.
        # self.transcript_data = {"You": [], "Speaker": []}
        self.transcript_changed_event = threading.Event()
        self.stt_model = model
        # Same mutex is used for all audio sources. In case locking becomes an issue, can consider
        # using separate mutex for each audio source
        self.mutex = threading.Lock()
        self.config = config
        self.clear_transcript_periodically: bool = \
            self.config['General']['clear_transcript_periodically']
        self.clear_transcript_interval_seconds: int = \
            self.config['General']['clear_transcript_interval_seconds']
        # Determines if transcription is enabled for the application. By default it is enabled.
        self.transcribe = True
        self.audio_sources = {
            "You": {
                # int
                "sample_rate": mic_source.SAMPLE_RATE,
                # int
                "sample_width": mic_source.SAMPLE_WIDTH,
                # int
                "channels": mic_source.channels,
                "last_sample": bytes(),  # Raw bytes for wav format data
                # Timestamp (UTC) for when the last transcribed audio record was put in queue
                "last_spoken": None,
                # bool
                "new_phrase": True,
                # function pointers
                "process_data_func": self.process_mic_data,
                # mutex
                "mutex": self.mutex
            },
            "Speaker": {
                # int
                "sample_rate": speaker_source.SAMPLE_RATE,
                # int
                "sample_width": speaker_source.SAMPLE_WIDTH,
                # int
                "channels": speaker_source.channels,
                "last_sample": bytes(),  # Raw bytes for wav format data
                # Timestamp (UTC) for when the last transcribed audio record was put in queue
                "last_spoken": None,
                # bool
                "new_phrase": True,
                # function pointer
                "process_data_func": self.process_speaker_data,
                # mutex
                "mutex": self.mutex
            }
        }
        self.conversation = convo

    def transcribe_audio_queue(self, audio_queue: queue.Queue):
        """Transcribe data from audio sources. In this case we have 2 sources, microphone, speaker.
        Args:
          audio_queue: queue object with reference to audio files
        """
        root_logger.info(AudioTranscriber.transcribe_audio_queue)
        while True:
            who_spoke, data, time_spoken = audio_queue.get()
            root_logger.info(f'Transcribe Audio Queue. Current time: {datetime.datetime.utcnow()} '
                             f'- Time Spoken: {time_spoken} by : {who_spoke}, queue_backlog - '
                             f'{audio_queue.qsize()}')
            self._update_last_sample_and_phrase_status(who_spoke, data, time_spoken)
            source_info = self.audio_sources[who_spoke]

            text = ''
            try:
                file_descritor, path = tempfile.mkstemp(suffix=".wav")
                os.close(file_descritor)
                source_info["process_data_func"](source_info["last_sample"], path)
                if self.transcribe:
                    with duration.Duration('Transcription (Speech to Text)'):
                        root_logger.info(f'{datetime.datetime.now()} - Begin transcription')
                        response = self.stt_model.get_transcription(path)
                        text = self.stt_model.process_response(response)
                        # print(f'Transcript: {text}')
                        if text != '':
                            self._prune_audio_file(response, who_spoke, time_spoken, path)

                        root_logger.info(f'{datetime.datetime.utcnow()} = Transcribed text: {text}')
                        root_logger.info(f'{datetime.datetime.utcnow()} - End transcription')

            except Exception as exception:
                print(exception)
            finally:
                os.unlink(path)

            if text != '' and text.lower() != 'you':
                self.update_transcript(who_spoke, text, time_spoken)
                self.transcript_changed_event.set()

    def _prune_audio_file(self, results, who_spoke, time_spoken, path):
        """Checks if pruning of Audio Source is required based on transcriber
        parameters, and prunes appropriately."""
        source_info = self.audio_sources[who_spoke]
        with source_info["mutex"]:
            original_data_size = len(source_info["last_sample"])

        prune, prune_id, prune_percent = self.check_for_latency(results)
        # print(f'Prune: {prune}. prune_id: {prune_id}. prune_percent: {prune_percent}')
        if prune:
            # print('Attempted to prune.')
            first, second = self.prune_for_latency(who_spoke=who_spoke,
                                                   original_data_size=original_data_size,
                                                   prune_percent=prune_percent,
                                                   results=results,
                                                   prune_id=prune_id,
                                                   file_path=path)
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=first, pop=True)
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=second, pop=False)

    @abstractmethod
    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Latency check is specific to each transcriber because of the difference
        in format of results. It is implemented in each transcriber specific class.
        Return values are
          prune: bool: Whether to prune or not
          prune_segment_id: int: Prune everything before this segment
          prune_percent: float: % of audio clip (by size) to be pruned
        """

    @abstractmethod
    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int) -> tuple[str, str]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Latency check is specific to each transcriber because of the difference
        in format of results. It is implemented in each transcriber specific class.
        """

    def _update_last_sample_and_phrase_status(self, who_spoke, data, time_spoken):
        root_logger.info(AudioTranscriber._update_last_sample_and_phrase_status.__name__)
        if not self.transcribe:
            return
        source_info = self.audio_sources[who_spoke]

        with source_info["mutex"]:
            # time_spoken - when current audio record was put into the queue (utc)
            if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] \
                    > datetime.timedelta(seconds=PHRASE_TIMEOUT):
                source_info["last_sample"] = bytes()
                source_info["new_phrase"] = True
            else:
                source_info["new_phrase"] = False

            source_info["last_sample"] += data
            source_info["last_spoken"] = time_spoken

    def process_mic_data(self, data, temp_file_name):
        """Processes audio data received from the microphone
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        root_logger.info(AudioTranscriber.process_mic_data.__name__)
        if not self.transcribe:
            return
        audio_data = sr.AudioData(data, self.audio_sources["You"]["sample_rate"],
                                  self.audio_sources["You"]["sample_width"])
        wav_data = io.BytesIO(audio_data.get_wav_data())
        with open(temp_file_name, 'w+b') as file_handle:
            # print(f'{datetime.datetime.now()} - Writing mic data into file: {temp_file_name}')
            file_handle.write(wav_data.read())
        # print(f'filesize: {os.path.getsize(temp_file_name)}')

    def process_speaker_data(self, data, temp_file_name):
        """Processes audio data received from the speaker
        Args:
            temp_file_name: Name of .wav file to store the data
        """
        root_logger.info(AudioTranscriber.process_speaker_data.__name__)
        if not self.transcribe:
            return
        # print(f'filesize: {os.path.getsize(temp_file_name)}')
        with wave.open(temp_file_name, 'wb') as wf:
            # print(f'{datetime.datetime.now()} - Writing speaker data into file: {temp_file_name}')
            wf.setnchannels(self.audio_sources["Speaker"]["channels"])    # pylint: disable=E1101
            p = pyaudio.PyAudio()
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))    # pylint: disable=E1101
            wf.setframerate(self.audio_sources["Speaker"]["sample_rate"])    # pylint: disable=E1101
            wf.writeframes(data)    # pylint: disable=E1101
            # print(f'datasize: {len(data)}')
        # print(f'filesize: {os.path.getsize(temp_file_name)}')

    def update_transcript(self, who_spoke, text, time_spoken):
        """Update transcript with new data
        Args:
        who_spoke: Person this audio is attributed to
        text: Actual spoken words
        time_spoken: Time at which audio was taken, relative to start time
        """
        source_info = self.audio_sources[who_spoke]

        # if source_info["new_phrase"] or len(transcript) == 0:
        if source_info["new_phrase"]:
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text)
        else:
            self.conversation.update_conversation(persona=who_spoke,
                                                  time_spoken=time_spoken,
                                                  text=text, pop=True)

    def get_transcript(self, length: int = 0):
        """Get the audio transcript
        Args:
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript
        """
        sources = [
            constants.PERSONA_YOU,
            constants.PERSONA_SPEAKER
            ]
        convo_object_return_value = self.conversation.get_conversation(
            sources=sources, length=length)
        return convo_object_return_value

    def clear_transcript_data_loop(self, audio_queue: queue.Queue):
        """Clear transcript data at a specified interval if needed.
        Args:
          audio_queue: queue object with reference to audio files
        """
        while True:
            if self.clear_transcript_periodically:
                self.clear_transcriber_context(audio_queue=audio_queue)
            time.sleep(self.clear_transcript_interval_seconds)

    def clear_transcriber_context(self, audio_queue: queue.Queue):
        """Reset the transcriber
        Args:
          textbox: textbox to be updated
          text: updated text
    """
        with self.mutex:
            # This method can be invoked from 2 different contexts.
            # Mutex ensures integrity of data for race conditions.
            root_logger.info(AudioTranscriber.clear_transcriber_context.__name__)
            self.clear_transcript_data()
            with audio_queue.mutex:
                audio_queue.queue.clear()

    def clear_transcript_data(self):
        """Clears all internal data associated with the transcript
        """
        self.audio_sources["You"]["last_sample"] = bytes()
        self.audio_sources["Speaker"]["last_sample"] = bytes()

        self.audio_sources["You"]["new_phrase"] = True
        self.audio_sources["Speaker"]["new_phrase"] = True

        self.conversation.clear_conversation_data()


class WhisperTranscriber(AudioTranscriber):
    """Does local application specific processing related to WhisperTranscriber.
    Also processes the local application state as it relates to Whisper.
    Does not interact with the Whisper API or Local Whisper SDK.
    """
    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Very long audio clips can result in latency of transcription.
        Prune long audio clips based on number of segments, audio duration.
        Return values are
          prune: bool: Whether to prune or not
          prune_segment_id: int: Prune everything before this segment
          prune_percent: float: % of audio clip (by size) to be pruned
        """
        root_logger.info(WhisperTranscriber.check_for_latency)
        try:
            len_segments = len(results["segments"])
        except KeyError:
            return (False, 0, 0)

        if len_segments == 0:
            return (False, 0, 0)

        len_speech = float(results["segments"][len_segments-1]['end'])
        root_logger.info(f'Segments: {len_segments}. Speech length: {len_speech} seconds.')
        if len_segments > WHISPER_SEGMENT_PRUNE_THRESHOLD:
            root_logger.info(f'Attempt Prune segments: {len_segments - WHISPER_SEGMENT_PRUNE_THRESHOLD}.')
        else:
            return (False, 0, 0)

        prune_percent = 0
        original_duration = results["segments"][len_segments-1]["end"]

        # Determine how many segments to keep based on sentence ending.
        # Start with len - max segments and determine which one is the last one that
        # can be kept based on end of sentence.
        for rev_segment in reversed(results["segments"]):
            if int(rev_segment['id']) > len_segments - 3:
                continue
            text = rev_segment["text"].strip()
            if text.endswith('.') or text.endswith('!') or text.endswith('?'):
                prune_segment_id = int(rev_segment['id'])
                prune_seconds = float(rev_segment['end'])
                prune_percent = prune_seconds / original_duration
                root_logger.info(f'Prune till segment id : {prune_segment_id}.'
                                 f' Prune duration: {prune_seconds}.')
                root_logger.info(f'Prune {prune_percent}% of data.')
                break

        # for segment in results["segments"]:
        #     print(f'id: {segment["id"]} start: {segment["start"]} end: {segment["end"]} ' +
        #           f'text: {segment["text"].strip()}')

        if prune_percent == 0:
            root_logger.info(f'Total segments ({len_segments}) is more than prune threshold'
                             f' ({WHISPER_SEGMENT_PRUNE_THRESHOLD}), but could not find segment endings.')

            # Attempt to determine prune percent based on audio duration
            if original_duration > AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS:
                # Prune the first prunes_seconds of audio.
                prune_seconds = original_duration - AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS + 5
                # Find the segment that corresponds to prune_seconds
                for segment in results["segments"]:
                    if float(segment['end']) > prune_seconds:
                        prune_segment_id = int(segment['id'])
                        prune_percent = prune_seconds / original_duration
                        root_logger.info(f'Prune till segment id : {prune_segment_id}.'
                                         f' Prune duration: {prune_seconds}.')
                        root_logger.info(f'Prune {prune_percent}% of data.')
                        break

        if prune_percent == 0:
            return (False, 0, 0)

        return True, prune_segment_id, prune_percent

    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int):
        """Prune Audio clip to a smaller size based on size.
        Adjusts the application context based on pruning to reflect pruning.
        """
        # If original_data_size and current size of data do not match, do nothing
        # print('Prune for latency')
        segments = results["segments"]
        root_logger.info(f'prune_for_latency: Prune source data by {prune_percent}%. ')
        source_info = self.audio_sources[who_spoke]

        with source_info["mutex"]:
            # Concurrency check
            if len(source_info["last_sample"]) != original_data_size:
                root_logger.info(f'Aborting pruning. Data Size has changed from '
                                 f'{original_data_size} to '
                                 f'{len(source_info["last_sample"])}')
                return

            # Open the wav file
            with wave.open(file_path, 'rb') as wavfile:

                # Get the number of frames
                num_frames = wavfile.getnframes()
                save_frames = int(num_frames * prune_percent)
                root_logger.info(f'File {file_path} has {num_frames} frames.'
                                 f' We will save the last {save_frames} frames.')
                new_data = b""

                with io.BytesIO() as temp_wav_file:
                    with wave.open(temp_wav_file, "wb") as wav_writer:
                        wav_writer.setnchannels(wavfile.getnchannels())  # pylint: disable=E1101
                        wav_writer.setsampwidth(wavfile.getsampwidth())  # pylint: disable=E1101
                        wav_writer.setframerate(wavfile.getframerate())  # pylint: disable=E1101
                        wavfile.setpos(save_frames)
                        data = wavfile.readframes(num_frames - int(save_frames))
                        new_data = new_data + data
                        wav_writer.writeframes(data)  # pylint: disable=E1101

            source_info["last_sample"] = new_data

        # print(f'Prune convo object until prune id: {prune_id}')
        # root_logger.info(f'Prune convo object until prune id: {prune_id}')
        try:
            first_string = ''
            second_string = ''
            for segment in segments:
                if int(segment["id"]) <= prune_id:
                    first_string += segment["text"]
                else:
                    second_string += segment["text"]
        except Exception as ex:
            print(f'Exception while pruning: {ex}')

        root_logger.info(f'First string: {first_string}')
        root_logger.info(f'Second string: {second_string}')

        return first_string, second_string


DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD = 2  # Prune anything more than 2 paragraphs


class DeepgramTranscriber(AudioTranscriber):
    """Does local application specific processing related to Deepgram.
    Also processes the local application state as it relates to Deepgram.
    Does not interact with the Deepgram API.
    """

    def check_for_latency(self, results: dict) -> tuple[bool, int, float]:
        """Determine if the response can be pruned to optimize STT processing
        Prune when
            - More than 2 paragraphs
            - Keep atleast 4 sentences
        Return values are
            prune: bool: Whether or not to prune
            num_paragraphs_to_keep: Prune everything up to this paragraph
            prune_percent: float: % of audio clip (by size) to be pruned
        """
        # check for existence of paragraphs
        root_logger.info(WhisperTranscriber.check_for_latency)
        try:
            outer_paragraphs = results["results"]["channels"][0]["alternatives"][0]["paragraphs"]
        except KeyError as ke:
            print('Error when attempting to get paragraphs from Deepgram response.')
            print(f'Key Error: {ke}')
            return [False, 0, 0]

        speech_duration = float(results["metadata"]["duration"])
        # print(f'Total speech length: {speech_duration}')

        para_list = outer_paragraphs["paragraphs"]
        num_paragraphs = len(para_list)
        # print(f'There are {num_paragraphs} paragraphs')
        # i = 1
        # for para in para_list:
        #    len_sentences = len(para["sentences"])
        #    # print(f'Paragraph: {i}, {len_sentences} sentences.')
        #    i += 1

        if num_paragraphs > DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD:
            # Keep the last 2 paragraphs. Prune everything else
            num_paragraphs_to_keep = DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD
        else:
            # print(f'Number of paras {num_paragraphs} less than or equal to threshold {DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD}. Skip pruning.')
            return [False, 0, 0]

        # determine prune percent based on how much speech we need to keep
        # First paragraph we will keep is
        beginning_para = para_list[-DEEPGRAM_PARAGRAPH_PRUNE_THRESHOLD]
        start_time = float(beginning_para["sentences"][0]["start"])
        # print(f"First para to keep, start time: {start_time}. Para text: {beginning_para['sentences'][0]['text']}.")
        prune_percent = start_time / speech_duration

        # Incorporate AUDIO_LENGTH_PRUNE_THRESHOLD_SECONDS into pruning calculations

        return [True, num_paragraphs_to_keep, prune_percent]

    def prune_for_latency(self, who_spoke: str, original_data_size: int,
                          results: dict, prune_id: int,
                          file_path: str, prune_percent: int):
        """Prune Audio clip to a smaller size based on size.
        Adjusts the application context based on pruning to reflect pruning.
        """
        # If original_data_size and current size of data do not match, do nothing
        # print('Prune for latency')
        root_logger.info(f'prune_for_latency: Prune source data by {prune_percent}%. ')
        source_info = self.audio_sources[who_spoke]

        with source_info["mutex"]:
            # Concurrency check
            if len(source_info["last_sample"]) != original_data_size:
                root_logger.info(f'Aborting pruning. Data Size has changed from '
                                 f'{original_data_size} to '
                                 f'{len(source_info["last_sample"])}')
                return

            # Open the wav file
            with wave.open(file_path, 'rb') as wavfile:

                # Get the number of frames
                num_frames = wavfile.getnframes()
                save_frames = int(num_frames * prune_percent)
                root_logger.info(f'File {file_path} has {num_frames} frames.'
                                 f' We will save the last {save_frames} frames.')
                new_data = b""

                with io.BytesIO() as temp_wav_file:
                    with wave.open(temp_wav_file, "wb") as wav_writer:
                        wav_writer.setnchannels(wavfile.getnchannels())  # pylint: disable=E1101
                        wav_writer.setsampwidth(wavfile.getsampwidth())  # pylint: disable=E1101
                        wav_writer.setframerate(wavfile.getframerate())  # pylint: disable=E1101
                        wavfile.setpos(save_frames)
                        data = wavfile.readframes(num_frames - int(save_frames))
                        new_data = new_data + data
                        wav_writer.writeframes(data)  # pylint: disable=E1101

            source_info["last_sample"] = new_data

        try:
            root_logger.info(f'Prune convo object until prune id: {prune_id}')
            first_string = ''
            second_string = ''
            para_list = results["results"]["channels"][0]["alternatives"][0]["paragraphs"]["paragraphs"]
            for para in para_list[0:-prune_id]:
                for sentence in para["sentences"]:
                    first_string += sentence["text"]
            for para in para_list[-prune_id:]:
                for sentence in para["sentences"]:
                    second_string += sentence["text"]
        except Exception as ex:
            print(f'Exception while pruning: {ex}')

        # print(f'Pruning, till end of string: {first_string}')
        # print(f'Start new segment with this string: {second_string}')

        return first_string, second_string
