import sys
import os
import datetime
import json
import re
import subprocess
import wave
from enum import Enum
from abc import abstractmethod
import openai
import whisper
import torch
from deepgram import (DeepgramClient, FileSource, PrerecordedOptions)
from tsutils import utilities
# import pprint


class STTEnum(Enum):
    """Supported Speech To Text Models
    """
    WHISPER_LOCAL = 1
    WHISPER_API = 2
    WHISPER_CPP = 3
    DEEPGRAM_API = 4
    SENSEVOICE_LOCAL = 5


MODELS_DIR = f"{utilities.get_data_path(app_name='Transcribe')}/models/"


class STTModelFactory:
    """Factory class to get the appropriate STT Model
    """
    def get_stt_model_instance(self, stt_model: STTEnum, stt_model_config: dict):
        """Get the appropriate STT model class instance
        Args:
          stt_model: Speech to Text Model
          config: dict: Used to pass all configuration parameters
          model_file: str: OpenAI Transcription model for local transcription
        """
        if not isinstance(stt_model, STTEnum):
            raise TypeError('STTModelFactory: stt_model should be an instance of STTEnum')

        if stt_model == STTEnum.WHISPER_LOCAL:
            # How do we get a different model for whisper, tiny vs base vs medium
            # Model value is derived from command line args
            return WhisperSTTModel(stt_model_config=stt_model_config)
        elif stt_model == STTEnum.WHISPER_API:
            return APIWhisperSTTModel(stt_model_config=stt_model_config)
        elif stt_model == STTEnum.WHISPER_CPP:
            return WhisperCPPSTTModel(stt_model_config=stt_model_config)
        elif stt_model == STTEnum.DEEPGRAM_API:
            return DeepgramSTTModel(stt_model_config=stt_model_config)
        elif stt_model == STTEnum.SENSEVOICE_LOCAL:
            return SenseVoiceSTTModel(stt_model_config=stt_model_config)
        raise ValueError("Unknown Speech to Text Model Type")


class STTModelInterface:
    """Interface all Speech To Text Models must adhere to
    """

    @abstractmethod
    def get_transcription(self, wav_file_path: str):
        """Get transcription from the provided audio file
        """
        pass  # pylint: disable=W0107

    @abstractmethod
    def get_sentences(self, wav_file_path: str):
        """Get transcription from the provided audio file
           as individual sentences
        """
        pass  # pylint: disable=W0107

    @abstractmethod
    def process_response(self, response) -> str:
        """Extract transcription from the response of the specific STT Model
        """
        pass  # pylint: disable=W0107


class SenseVoiceSTTModel(STTModelInterface):
    """Optional Windows-only SenseVoiceSmall transcription backend."""

    SUPPORTED_LANGUAGES = {"zh", "en", "yue", "ja", "ko", "auto"}
    LANGUAGE_NAMES = {
        "chinese": "zh",
        "english": "en",
        "cantonese": "yue",
        "japanese": "ja",
        "korean": "ko",
        "auto": "auto",
    }

    def __init__(self, stt_model_config: dict):
        if sys.platform != "win32":
            raise RuntimeError("The experimental SenseVoice backend currently supports Windows only.")

        try:
            from funasr import AutoModel  # pylint: disable=import-outside-toplevel
            from funasr.utils.postprocess_utils import (  # pylint: disable=import-outside-toplevel
                rich_transcription_postprocess,
            )
        except ImportError as exception:
            raise RuntimeError(
                "SenseVoice dependencies are not installed. Run "
                "'pip install -r requirements-sensevoice.txt' from app\\transcribe."
            ) from exception

        self.lang = self._normalize_language(stt_model_config.get("audio_lang", "auto"))
        self.use_itn = bool(stt_model_config.get("use_itn", True))
        self.postprocess = rich_transcription_postprocess
        model_name = stt_model_config.get("model", "FunAudioLLM/SenseVoiceSmall")
        device = stt_model_config.get("device", "auto")
        if device == "auto":
            device = "cuda:0" if torch.cuda.is_available() else "cpu"

        print(f"[INFO] Using SenseVoiceSmall for transcription on {device}.")
        self.audio_model = AutoModel(
            model=model_name,
            vad_model="fsmn-vad",
            hub="hf",
            disable_pbar=True,
            vad_kwargs={"max_single_segment_time": 30000},
            device=device,
        )

    @classmethod
    def _normalize_language(cls, lang: str) -> str:
        normalized = str(lang).strip().lower()
        normalized = cls.LANGUAGE_NAMES.get(normalized, normalized)
        return normalized if normalized in cls.SUPPORTED_LANGUAGES else "auto"

    def set_lang(self, lang: str):
        """Set the recognition language, falling back to automatic detection."""
        self.lang = self._normalize_language(lang)

    @staticmethod
    def _audio_duration(wav_file_path: str) -> float:
        with wave.open(wav_file_path, "rb") as wav_file:
            return wav_file.getnframes() / float(wav_file.getframerate())

    @staticmethod
    def _sentence_segments(text: str, duration_seconds: float) -> list[dict]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s*", text) if part.strip()]
        if not sentences:
            return []

        total_chars = sum(len(sentence) for sentence in sentences)
        start = 0.0
        segments = []
        for segment_id, sentence in enumerate(sentences):
            fraction = len(sentence) / total_chars if total_chars else 1 / len(sentences)
            end = duration_seconds if segment_id == len(sentences) - 1 else start + duration_seconds * fraction
            segments.append({"id": segment_id, "start": start, "end": end, "text": sentence})
            start = end
        return segments

    def get_transcription(self, wav_file_path: str) -> dict:
        """Transcribe a WAV file and normalize the result for the application."""
        raw_response = self.audio_model.generate(
            input=wav_file_path,
            cache={},
            language=self.lang,
            use_itn=self.use_itn,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )
        text = " ".join(
            self.postprocess(item.get("text", "")).strip()
            for item in raw_response
            if item.get("text")
        ).strip()
        return {
            "text": text,
            "segments": self._sentence_segments(text, self._audio_duration(wav_file_path)),
            "raw_response": raw_response,
        }

    def process_response(self, response) -> str:
        """Extract normalized transcription text."""
        return response.get("text", "").strip() if response else ""

    def get_sentences(self, wav_file_path: str) -> list[str]:
        """Return timestamped sentences for batch file transcription."""
        response = self.get_transcription(wav_file_path)
        return [
            f"{datetime.timedelta(seconds=int(segment['start']))} - "
            f"{datetime.timedelta(seconds=int(segment['end']))}: {segment['text']}"
            for segment in response["segments"]
        ]

class WhisperSTTModel(STTModelInterface):
    """Speech to Text using the Whisper Local model
    """
    def __init__(self, stt_model_config: dict):
        self.model = stt_model_config['local_transcripton_model_file']
        self.lang = stt_model_config['audio_lang']
        model_filename = MODELS_DIR + self.model + ".pt"
        self.model_name = self.model + ".pt"
        self.model_filename = os.path.join(MODELS_DIR, model_filename)
        self.download_model()
        self.audio_model: whisper.Whisper = whisper.load_model(self.model_filename)
        print(f'[INFO] Speech To Text - Whisper using GPU: {str(torch.cuda.is_available())}')
        openai.api_key = stt_model_config["api_key"]

    def download_model(self):
        """Download the appropriate OpenAI model if needed"""

        if os.path.exists(self.model_filename):
            return
        print(f'Could not find the transcription model file: {self.model_filename}')
        utilities.ensure_directory_exists(MODELS_DIR)
        if self.model == 'tiny':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'base':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'small':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'medium':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'large':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'large-v1':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'large-v2':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        elif self.model == 'large-v3':
            file_url = 'https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/' + self.model_name
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)
        else:
            print('Could not find the correct model file')
            sys.exit()

    def get_sentences(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file as individual sentences
        """
        result = self.audio_model.transcribe(wav_file_path,
                                             fp16=False,
                                             language=self.lang,
                                             temperature=0)
        sentences = []
        for segment in result['segments']:
            start = str(datetime.timedelta(seconds=int(segment['start'])))
            end = str(datetime.timedelta(seconds=int(segment['end'])))
            sentences.append(f"{start} - {end}: {segment['text']}")
        return sentences

    def get_transcription(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file
        """
        try:
            # For translation provide a decode_option for task=translate
            # options = {}
            # options['task'] = 'translate'
            result = self.audio_model.transcribe(wav_file_path,
                                                 fp16=False,
                                                 language=self.lang,
                                                 temperature=0)
        except Exception as exception:
            print('WhisperSTTModel:get_transcription - Encountered error')
            print(exception)
            return ''
        # print('-----------------------------------------------------------------------------')
        # pprint.pprint(result)
        # print('-----------------------------------------------------------------------------')
        # return result['text'].strip()
        return result

    def set_lang(self, lang: str):
        """Set Language for STT
        """
        self.lang = lang
        self.download_model()
        self._load_model()

    def _load_model(self):
        """Load Model for STT
        """
        self.audio_model = whisper.load_model(self.model_filename)

    def process_response(self, response) -> str:
        """
        Returns transcription from the response of transcription.
        """
        # response['text'] = transcription text
        # response['language'] = language of transcription
        # response['segments'] = list of segments.
        # response['segments']['text'] = text of the segment.
        # response['segments']['start'] = start time of segment.
        # response['segments']['end'] = end time of segment.
        # Each segment is a dict
        #
        # for segment in response['segments']:
        #     start = str(datetime.timedelta(seconds=int(segment['start'])))
        #     end = str(datetime.timedelta(seconds=int(segment['end'])))
        #     print(f"{start} - {end}: {segment['text']}")
        # pprint.pprint(response)
        return response['text'].strip()


class APIWhisperSTTModel(STTModelInterface):
    """Speech to Text using the Whisper API
    """
    def __init__(self, stt_model_config: dict):
        # Check for api_key
        if stt_model_config["api_key"] is None:
            raise Exception("Attempt to create Open AI Whisper STT Model without an api key.")  # pylint: disable=W0719
        print('[INFO] Using Open AI Whisper API for transcription.')
        self.stt_client = openai.OpenAI(api_key=stt_model_config['api_key'], base_url=None)
        self.timeout = stt_model_config['timeout']
        # lang parameter is not required for API invocation. This exists solely
        # to support --api option from command line.
        # A better solution is to create a base class for APIWhisperSTTModel,
        # WhisperSTTModel and create set_lang method there and remove it from
        # this class
        self.lang = stt_model_config['audio_lang']

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                result = self.stt_client.audio.transcriptions.create(model='whisper-1', file=audio_file)
        except Exception as exception:
            print('Exception in transcribing audio using whisper API.')
            print(exception)
            return ''

        return result

    def process_response(self, response) -> str:
        """
        Returns transcription from the response of transcription.
        """
        # response['text'] = transcription text
        # response['language'] = language of transcription
        # response['segments'] = list of segments.
        # response['segments']['text'] = text of the segment.
        # response['segments']['start'] = start time of segment.
        # response['segments']['end'] = end time of segment.
        # Each segment is a dict
        #
        # for segment in response['segments']:
        #     start = str(datetime.timedelta(seconds=int(segment['start'])))
        #     end = str(datetime.timedelta(seconds=int(segment['end'])))
        #     print(f"{start} - {end}: {segment['text']}")
        # pprint.pprint(response)
        return response.text.strip()

    def get_sentences(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file as individual sentences
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                result = self.stt_client.audio.transcriptions.create(model='whisper-1', file=audio_file,
                                                                     language=self.lang)
        except Exception as exception:
            print('Exception in transcribing audio using whisper API.')
            print(exception)
            return ''

        return [result.text]


class WhisperCPPSTTModel(STTModelInterface):
    """Speech to Text using the local whisper cpp exes.
    It primarily deals with interacting with the whisper CPP API model.
    This model works best when used with GPU
    """
    def __init__(self, stt_model_config: dict):
        self.lang = stt_model_config['audio_lang']
        model = stt_model_config['local_transcripton_model_file']
        self.model_filename = MODELS_DIR + model + ".bin"
        self.model = model

        if not os.path.isfile(self.model_filename):
            print(f'Could not find the transcription model file: {self.model_filename}')
            utilities.ensure_directory_exists(MODELS_DIR)
            file_url = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/' + model + '.bin'
            utilities.download_using_bits(file_url=file_url, file_path=self.model_filename)

        print('[INFO] Using Whisper CPP for transcription.')
        self.model = 'base'

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path: str):
        """Get text using STT
        """
        mod_file_path = wav_file_path
        try:
            log_file = f"{utilities.get_data_path(app_name='Transcribe')}/logs/whisper.cpp.txt"
            # main.exe <filename> -oj
            if os.path.isfile("../../bin/main.exe"):
                subprocess.call(["../../bin/main.exe", mod_file_path, '-oj', '-m',
                                 self.model_filename, '-l', self.lang],
                                stdout=open(file=log_file, mode='a', encoding='utf-8'),
                                stderr=subprocess.STDOUT)
            else:
                # This path is used in case of binary.
                subprocess.call(["./bin/main.exe", mod_file_path, '-oj', '-m', self.model_filename,
                                 '-l', self.lang],
                                stdout=open(file=log_file, mode='a', encoding='utf-8'),
                                stderr=subprocess.STDOUT)
        except Exception as ex:
            print(f'ERROR: converting wav file {wav_file_path} to text using whisper.cpp.')
            print('Ensure that the file ../../bin/main.exe exists.')
            print(ex)

        try:
            # Output is produced in json file wav_file_path.json
            json_file_path = mod_file_path+".json"
            with open(json_file_path, mode="r", encoding='utf-8') as text_file:
                response = json.loads(text_file.read())
                return response
        except Exception as exception:
            print(f'Error reading json file: {json_file_path}')
            print(exception)

        os.unlink(json_file_path)
        os.unlink(mod_file_path)

        return None

    def process_response(self, response) -> str:
        # response is of type PrerecordedTranscriptionResponse
        # convert result to the appropriate dict format
        text = ''
        for segment in response["transcription"]:
            if segment["text"].strip() == '[BLANK_AUDIO]':
                continue
            text += segment["text"]
        # print(f'Transcript: {text}')
        return text

    def get_sentences(self, wav_file_path: str):
        """Not Implemented
        """
        transcript = ''
        response = self.get_transcription(wav_file_path=wav_file_path)
        for segment in response["transcription"]:
            if segment["text"].strip() == '[BLANK_AUDIO]':
                continue
            transcript += segment["text"]
        return transcript

        # raise Exception('Method not implemnted')  # pylint: disable=W0719


class DeepgramSTTModel(STTModelInterface):
    """Speech to Text using the Deepgram API.
    It primarily deals with interacting with the Deepgram API.
    """
    def __init__(self, stt_model_config: dict):
        # Check for api_key
        if stt_model_config["api_key"] is None:
            raise Exception("Attempt to create Deepgram STT Model without an api key.")  # pylint: disable=W0719

        # This parameter exists primarily to adhere to the interface.
        # Deepgram does auto language detection.
        # self.lang = 'en-US'
        self.lang = stt_model_config['audio_lang']

        print('[INFO] Using Deepgram API for transcription.')
        self.audio_model = DeepgramClient(stt_model_config["api_key"])

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path: str):
        """Get text using STT
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                buffer_data = audio_file.read()

            payload: FileSource = {
                "buffer": buffer_data
                }

            options = PrerecordedOptions(
                model="nova",
                smart_format=True,
                utterances=True,
                punctuate=True,
                paragraphs=True,
                detect_language=True)

            response = self.audio_model.listen.prerecorded.v("1").transcribe_file(payload, options)
            # This is not necessary and just a debugging aid
            with open('logs/deep.json', mode='a', encoding='utf-8') as deep_log:
                deep_log.write(response.to_json(indent=4))

            return response
        except Exception as exception:
            print(exception)

        return None

    def get_sentences(self, wav_file_path: str):
        """Get transcription from the provided audio file as individual sentences
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                buffer_data = audio_file.read()

            payload: FileSource = {
                "buffer": buffer_data
                }
            if self.lang.startswith('en'):
                options = PrerecordedOptions(
                    model="nova",
                    smart_format=True,
                    utterances=True,
                    punctuate=True,
                    paragraphs=True,
                    detect_language=True,
                    language=self.lang)
            else:
                options = PrerecordedOptions(
                    model="general",
                    smart_format=True,
                    utterances=True,
                    punctuate=True,
                    paragraphs=True,
                    detect_language=True,
                    language=self.lang)

            response = self.audio_model.listen.prerecorded.v("1").transcribe_file(payload, options)
            # This is not necessary and just a debugging aid
            log_file = f"{utilities.get_data_path(app_name='Transcribe')}/logs/deep.json"
            with open(log_file, mode='a', encoding='utf-8') as deep_log:
                deep_log.write(response.to_json(indent=4))
            results = []
            for utterance in response.results.utterances:
                start = str(datetime.timedelta(seconds=int(utterance['start'])))
                end = str(datetime.timedelta(seconds=int(utterance['end'])))
                results.append(f"{start} - {end} : {utterance['transcript']}")

            return results
        except Exception as exception:
            print(exception)

        return None

    def process_response(self, response) -> str:
        # response is of type PrerecordedTranscriptionResponse
        # convert result to the appropriate dict format
        text = response.results.channels[0].alternatives[0].transcript
        # print(f'Transcript: {text}')
        return text
