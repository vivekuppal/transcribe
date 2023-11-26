import sys
import os
import json
import subprocess
import tempfile
from enum import Enum
from abc import abstractmethod
import openai
import whisper
import torch
# import pprint


class STTEnum(Enum):
    """Supported Speech To Text Models
    """
    WHISPER_LOCAL = 1
    WHISPER_API = 2
    WHISPER_CPP = 3
    DEEPGRAM_API = 4


class STTModelFactory:
    """Factory class to get the appropriate STT Model
    """
    def get_stt_model_instance(self, stt_model: STTEnum, config: dict):
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
            return WhisperSTTModel(config=config)
        elif stt_model == STTEnum.WHISPER_API:
            return APIWhisperSTTModel(config=config)
        elif stt_model == STTEnum.WHISPER_CPP:
            return WhisperCPPSTTModel(config=config)
        elif stt_model == STTEnum.DEEPGRAM_API:
            return DeepgramSTTModel(config=config)
        raise ValueError("Unknown SPeech to Text Model Type")


class STTModelInterface:
    """Interface all Speech To Text Models must adhere to
    """

    @abstractmethod
    def get_transcription(self, wav_file_path: str):
        """Get transcription from the provided audio file
        """
        pass

    @abstractmethod
    def process_response(self, response) -> str:
        """Extract transcription from the response of the specific STT Model
        """
        pass


# TODO: Download the necessary models for whisper automatically
# TODO: Move whisper models to model folder as well instead of placing them in the base folder
#       Update readme for the models change
class WhisperSTTModel(STTModelInterface):
    """Speech to Text using the Whisper Local model
    """
    def __init__(self, config: dict):
        model = config['local_transcripton_model_file']
        self.lang = 'en'
        model_filename = model + ".en.pt"
        self.model = model

        if not os.path.isfile(model_filename):
            print(f'Could not find the transcription model file: {model_filename}')
            print(f'Download the transcription model file and add it to the directory: \
                  {os.getcwd()}')
            print('tiny multi-lingual model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt')  # noqa: E501  pylint: disable=C0115
            print('base english model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt')  # noqa: E501  pylint: disable=C0115
            print('base multi-lingual model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt')  # noqa: E501  pylint: disable=C0115
            print('small english model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt')  # noqa: E501  pylint: disable=C0115
            print('small multi-lingual model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt')  # noqa: E501  pylint: disable=C0115
            print('medium english model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt')  # noqa: E501  pylint: disable=C0115
            print('medium multi-lingual model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt')  # noqa: E501  pylint: disable=C0115
            print('large model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt')  # noqa: E501  pylint: disable=C0115
            print('large-v1 model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt')  # noqa: E501  pylint: disable=C0115
            print('large-v2 model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt')  # noqa: E501  pylint: disable=C0115
            print('large-v3 model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt')  # noqa: E501  pylint: disable=C0115
            sys.exit()

        self.model_filename = os.path.join(os.getcwd(), model_filename)
        self.audio_model = whisper.load_model(self.model_filename)
        print(f'[INFO] Whisper using GPU: {str(torch.cuda.is_available())}')
        openai.api_key = config["api_key"]

    def get_transcription(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file
        """
        try:
            result = self.audio_model.transcribe(wav_file_path,
                                                 fp16=torch.cuda.is_available(), language=self.lang)
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
        self._load_model()

    def _load_model(self):
        """Set Model for STT
        """
        if self.lang == "en":
            self.audio_model = whisper.load_model(os.path.join(os.getcwd(), self.model + '.en.pt'))
        else:
            self.audio_model = whisper.load_model(os.path.join(os.getcwd(), self.model + '.pt'))

    def process_response(self, response) -> str:
        """
        Returns transcription from the response of transcription.
        """
        # results['text'] = transcription text
        # results['language'] = language of transcription
        # results['segments'] = list of segments.
        # Each segment is a dict
        #
        # pprint.pprint(results)
        return response['text'].strip()


class APIWhisperSTTModel(STTModelInterface):
    """Speech to Text using the Whisper API
    """
    def __init__(self, config: dict):
        # Check for api_key
        if config["api_key"] is None:
            raise Exception("Attempt to create Open AI Whisper STT Model without an api key.")  # pylint: disable=W0719
        print('[INFO] Using Open AI Whisper API for transcription.')
        openai.api_key = config["api_key"]
        # lang parameter is not required for API invocation. This exists solely
        # to support --api option from command line.
        # A better solution is to create a base class for APIWhisperSTTModel,
        # WhisperSTTModel and create set_lang method there and remove it from
        # this class
        self.lang = 'en'

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path) -> dict:
        """Get transcription from the provided audio file
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                result = openai.Audio.transcribe("whisper-1", audio_file)
        except Exception as exception:
            print(exception)
            return ''

        return result

    def process_response(self, response) -> str:
        """
        Returns transcription from the response of transcription.
        """
        # results['text'] = transcription text
        # results['language'] = language of transcription
        # results['segments'] = list of segments.
        # Each segment is a dict
        #
        # pprint.pprint(results)
        return response['text'].strip()


# TODO: Download the necessary models for whisper CPP automatically
# Test with and without GPU for main.exe. There are different exe with and without GPU
# Location of models is in https://github.com/ggerganov/whisper.cpp/blob/master/models/download-ggml-model.cmd
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v1.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v1.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.en.bin
# https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
#
#
# bin\main.exe c:\git\whisper.cpp\samples\jfk.wav -oj

class WhisperCPPSTTModel(STTModelInterface):
    """Speech to Text using the local whisper cpp exes.
    It primarily deals with interacting with the whisper CPP API model.
    This model works best when used with GPU
    """
    def __init__(self, config: dict):
        self.lang = 'en-US'

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
            # main.exe <filename> -oj
            subprocess.call(["./bin/main.exe", mod_file_path, '-oj'],
                            stdout=open(file='logs/whisper.cpp.txt', mode='w', encoding='utf-8'),
                            stderr=subprocess.STDOUT)
        except Exception as ex:
            print(f'ERROR: converting wav file {wav_file_path} to text using whisper.cpp.')
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


class DeepgramSTTModel(STTModelInterface):
    """Speech to Text using the Deepgram API.
    It primarily deals with interacting with the Deepgram API.
    """
    def __init__(self, config: dict):
        from deepgram import Deepgram  # noqa:E402  pylint: disable=C0415,C0411

        # Check for api_key
        if config["api_key"] is None:
            raise Exception("Attempt to create Deepgram STT Model without an api key.")  # pylint: disable=W0719
        self.lang = 'en-US'

        print('[INFO] Using Deepgram API for transcription.')
        self.audio_model = Deepgram(config["api_key"])

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path: str):
        """Get text using STT
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                # ...or replace mimetype as appropriate
                source = {'buffer': audio_file, 'mimetype': 'audio/wav'}
                options = {
                    "smart_format": True,
                    "model": "nova",
                    "language": self.lang,
                    'punctuate': True,
                    'paragraphs': True
                    }
                response = self.audio_model.transcription.sync_prerecorded(source, options=options)
                # This is not necessary and just a debugging aid
                with open('logs/deep.json', mode='a', encoding='utf-8') as deep_log:
                    deep_log.write(json.dumps(response, indent=4))

                return response
        except Exception as exception:
            print(exception)

        return None

    def process_response(self, response) -> str:
        # response is of type PrerecordedTranscriptionResponse
        # convert result to the appropriate dict format
        text = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        # print(f'Transcript: {text}')
        return text
