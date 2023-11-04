import sys
import os
import json
import openai
import whisper
import torch
import GlobalVars
# import pprint


# TODO: Deep Step - STT_Model should be a common base class

# This should be a factory method instead
def get_model(use_api: bool, model: str = None):
    if use_api:
        return APIWhisperTranscriber()
    if model.lower() == 'deepgram':
        return DeepgramTranscriber()

    model_cleaned = model if model else 'tiny'
    print(f'[INFO] Using local model: {model_cleaned}')
    return WhisperTranscriber(model=model_cleaned)


class WhisperTranscriber:
    def __init__(self, model: str = 'tiny'):
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
                    https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt')  # noqa: E501  pylint: disable=C0115
            print('large-v1 model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt')  # noqa: E501  pylint: disable=C0115
            print('large-v2 model has to be downloaded from the link \
                    https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt')  # noqa: E501  pylint: disable=C0115
            sys.exit()

        self.model_filename = os.path.join(os.getcwd(), model_filename)
        self.audio_model = whisper.load_model(self.model_filename)
        print(f'[INFO] Whisper using GPU: {str(torch.cuda.is_available())}')

    def get_transcription(self, wav_file_path) -> dict:
        try:
            result = self.audio_model.transcribe(wav_file_path,
                                                 fp16=torch.cuda.is_available(), language=self.lang)
        except Exception as exception:
            print('Encountered error in get_transcription')
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


class APIWhisperTranscriber:
    def __init__(self):
        print('[INFO] Using Open AI API for transcription.')
        openai.api_key = GlobalVars.TranscriptionGlobals().openai_api_key
        # lang parameter is not required for API invocation. This exists solely
        # to support --api option from command line.
        # A better solution is to create a base class for APIWhisperTranscriber,
        # WhisperTranscriber and create set_lang method there and remove it from
        # this class
        self.lang = 'en'

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    def get_transcription(self, wav_file_path) -> dict:
        """Get text using STT
        """
        try:
            with open(wav_file_path, "rb") as audio_file:
                result = openai.Audio.transcribe("whisper-1", audio_file)
        except Exception as exception:
            print(exception)
            return ''

        return result


class DeepgramTranscriber:
    def __init__(self):
        from deepgram import Deepgram  # noqa:E402  pylint: disable=C0413,C0411

        self.lang = 'en'

        print('[INFO] Using Deepgram API for transcription.')
        self.model = Deepgram(GlobalVars.TranscriptionGlobals().deepgram_api_key)

    def set_lang(self, lang: str):
        """Set STT Language"""
        self.lang = lang

    # TODO: deep, not sure if the return type is a dict or is it something else
    def get_transcription(self, wav_file_path) -> dict:
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
                response = self.model.transcription.sync_prerecorded(source, options=options)
                print(json.dumps(response, indent=4))
                return response
        except Exception as exception:
            print(exception)

        return None
