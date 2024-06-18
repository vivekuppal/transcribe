"""
Plays the responses received from LLM as Audio.
This class handles text-to-speech functionality.
"""

import os
import time
import tempfile
import threading
import playsound
import gtts
from conversation import Conversation
import constants
from tsutils import app_logging as al
from tsutils.language import LANGUAGES_DICT

logger = al.get_module_logger(al.AUDIO_PLAYER_LOGGER)


class AudioPlayer:
    """Play text to audio.
    """

    def __init__(self, convo: Conversation):
        logger.info(self.__class__.__name__)
        self.speech_text_available = threading.Event()
        self.conversation = convo
        self.temp_dir = tempfile.gettempdir()
        self.read_response = False
        self.stop_loop = False

    def play_audio(self, speech: str, lang: str):
        """Play text as audio.
        This is a blocking method and will return when audio playback is complete.
        For large audio text, this could take several minutes.
        """
        logger.info(f'{self.__class__.__name__} - Playing audio')  # pylint: disable=W1203
        try:
            audio_obj = gtts.gTTS(speech, lang=lang)
            temp_audio_file = tempfile.mkstemp(dir=self.temp_dir, suffix='.mp3')
            os.close(temp_audio_file[0])

            audio_obj.save(temp_audio_file[1])
            playsound.playsound(temp_audio_file[1])
        except playsound.PlaysoundException as play_ex:
            logger.error('Error when attempting to play audio.', exc_info=True)
            logger.info(play_ex)
        finally:
            os.remove(temp_audio_file[1])

    def play_audio_loop(self, config: dict):
        """Continuously play text as audio based on event signaling.
        """
        lang = 'english'
        lang_code = self._get_language_code(lang)

        while self.stop_loop is False:
            if self.speech_text_available.is_set() and self.read_response:
                self.speech_text_available.clear()
                speech = self._get_speech_text()
                final_speech = self._process_speech_text(speech)

                new_lang = config.get('OpenAI', {}).get('response_lang', lang)
                if new_lang != lang:
                    lang_code = self._get_language_code(new_lang)
                    lang = new_lang

                self.play_audio(speech=final_speech, lang=lang_code)
                self.read_response = False
            time.sleep(0.1)

    def _get_language_code(self, lang: str) -> str:
        """Get the language code from the configuration.
        """
        try:
            return next(key for key, value in LANGUAGES_DICT.items() if value == lang)
        except StopIteration:
            # Return dafault lang if nothing else is found
            return 'en'

    def _get_speech_text(self) -> str:
        """Get the speech text from the conversation.
        """
        return self.conversation.get_conversation(sources=[constants.PERSONA_ASSISTANT], length=1)

    def _process_speech_text(self, speech: str) -> str:
        """Process the speech text to remove persona and formatting.
        """
        persona_length = len(constants.PERSONA_ASSISTANT) + 2
        final_speech = speech[persona_length:].strip()
        return final_speech[1:-1]  # Remove square brackets
