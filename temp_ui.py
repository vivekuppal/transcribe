import streamlit as st
import GlobalVars
import app_logging as al
import pyperclip
import AudioTranscriber
import datetime
import constants
import GPTResponder
import queue
from language import LANGUAGES_DICT
import time

root_logger = al.get_logger()
UI_FONT_SIZE = 20
last_transcript_ui_update_time: datetime.datetime = datetime.datetime.now()
global_vars_module: GlobalVars.TranscriptionGlobals = None


class temp_ui_callbacks:
#top components
    global_vars: GlobalVars.TranscriptionGlobals

    def __init__(self) -> None:
        self.global_vars= GlobalVars.TranscriptionGlobals()

    def enable_disable_speaker(self):
        self.global_vars.speaker_audio_recorder.enabled = not self.global_vars.speaker_audio_recorder.enabled
        print(f" its currently {self.global_vars.speaker_audio_recorder.enabled}")

    def enable_disable_microphone(self):
        """Toggles the state of microphone"""
        self.global_vars.user_audio_recorder.enabled = not self.global_vars.user_audio_recorder.enabled
        
        print(f" its currently {self.global_vars.user_audio_recorder.enabled}")

    def copy_to_clipboard(self):
        root_logger.info(temp_ui_callbacks.copy_to_clipboard.__name__)
        pyperclip.copy(self.global_vars.transcriber.get_transcript())

    # def freeze_unfreeze(self):
    #     """Respond to start / stop of seeking responses from openAI API"""
    #     root_logger.info(temp_ui_callbacks.freeze_unfreeze)
    #     self.global_vars.freeze_state[0] = not self.global_vars.freeze_state[0]  # Invert the state
    #     self.global_vars.freeze_button.configure(
    #         label="Suggest Responses Continuously" if self.global_vars.freeze_state[0] else "Do Not Suggest Responses Continuously"
    #         )
          
    def update_response_ui_now(self):
        """Get response from LLM right away
           Update the Response UI with the response
        """
        transcript_string = self.global_vars.transcriber.get_transcript(
            length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
        
        response_string = self.global_vars.responder.generate_response_from_transcript_no_check(
            transcript_string)
        self.global_vars.response_textbox(disabled = False)
        temp_ui_callbacks.write_in_transciption_textbox(self.global_vars.response_textbox, response_string)
        self.global_vars.response_textbox(disabled = True)

    
    def update_response_ui_and_read_now(self):
        """Get response from LLM right away
        Update the Response UI with the response
        Read the response
        """
        self.update_response_ui_now()

        # Set event to play the recording audio
        self.global_vars.audio_player.speech_text_available.set()


    def write_in_conversation_textbox(self, text: str):
        """Update the text of textbox with the given text
            Args:
            textbox: textbox to be updated
            text: updated text
        """
        self.global_vars.transcript_textbox(value= text)
        
    

    def write_in_transciption_textbox(self, text: str):
        """Update the text of textbox with the given text
            Args:
            textbox: textbox to be updated
            text: updated text
        """
        #textbox.empty()
        self.global_vars.response_textbox(value= text)

    def update_transcript_ui(self, _transcriber: AudioTranscriber):
        global last_transcript_ui_update_time
        global global_vars_module

        if global_vars_module is None:
            global_vars_module = GlobalVars.TranscriptionGlobals()

        if last_transcript_ui_update_time < global_vars_module.convo.last_update:
            transcript_string = _transcriber.get_transcript()
            temp_ui_callbacks.write_in_conversation_textbox(self, transcript_string)
            last_transcript_ui_update_time = datetime.datetime.now()
            time.sleep(constants.TRANSCRIPT_UI_UPDATE_DELAY_DURATION_MS)
            self.update_transcript_ui(self, _transcriber)
        


    def update_response_ui(self, _responder: GPTResponder,
                        
                        freeze_state):
        """Update the text of response textbox with the given text
            Args:
            textbox: textbox to be updated
            text: updated text
        """
        if not freeze_state[0]:
            response = _responder.response
            temp_ui_callbacks.write_in_transciption_textbox(self, response)
            
        time.sleep(0.3)
        self.update_response_ui(self, _responder, freeze_state)    


def clear_transcriber_context(transcriber: AudioTranscriber,
                              audio_queue: queue.Queue):
    """Reset the transcriber
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    root_logger.info(clear_transcriber_context.__name__)
    transcriber.clear_transcript_data()
    with audio_queue.mutex:
        audio_queue.queue.clear()


def create_temp_ui():
    root_logger.info(create_temp_ui.__name__)
    ui_cb = temp_ui_callbacks()
    global_vars =GlobalVars.TranscriptionGlobals()
 
    conversation_col, transcription_col =st.columns(2,gap="small")

    with conversation_col:
        if "convo_key" not in st.session_state:
            conversationn = st.text_area("Conversation",value="wow tf?", key="convo_key", height=350)

    with transcription_col:
        if "transci_key" not in st.session_state:
            transcription = st.text_area("Transcription",key="transci_key", height=350)
            
    #middle components
    if "languages" not in st.session_state:
        st.session_state.languages_box = st.selectbox("Languages", options=(LANGUAGES_DICT.values()), placeholder="Languages", key="languages")

    #lower button components
    toggle_col, button_col =st.columns((30,12),gap="large")

    with toggle_col:
        if "speaker" not in st.session_state:
            st.session_state.speaker_button = st.toggle("Speaker", on_change=ui_cb.enable_disable_speaker, key="speaker")
        if "microphone" not in st.session_state:
            st.session_state.microphone_button =st.toggle("Microphone", on_change=ui_cb.enable_disable_microphone, key="microphone")

    # with button_col:
        # if "suggest" not in st.session_state:    
        #     st.session_state.suggest = st.button("Suggest Responses", key="suggest")
        # if "csuggest" not in st.session_state:
        #     st.session_state.csuggest = st.button("Suggest Responses Continuously", key="csuggest")

    #sidebar components
    if "copy" not in st.session_state:
        st.session_state.sidebar_copy_button = st.sidebar.button("Copy conversation", key="copy")
    if "download" not in st.session_state:
        st.session_state.sidebar_download_button = st.sidebar.download_button("Download your conversation","one", key="download") #data=ui_cb.global_vars.transcriber.get_transcript()
    if "clear" not in st.session_state:
        st.session_state.sidebar_clear_chat = st.sidebar.button("Clear Chat", key="clear")
        
    return [conversationn,transcription, st.session_state.languages_box,
             st.session_state.sidebar_download_button, st.session_state.sidebar_clear_chat,
            st.session_state.sidebar_copy_button, st.session_state.speaker_button,
            st.session_state.microphone_button]


           
        

   
