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

        
    def update_response_ui_now(self):
        """Get response from LLM right away
           Update the Response UI with the response
        """
        transcript_string = self.global_vars.transcriber.get_transcript(
            length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
        
        response_string = self.global_vars.responder.generate_response_from_transcript_no_check(
            transcript_string)
        self.global_vars.response_textbox.configure(state="normal")
        write_in_textbox(self.global_vars.response_textbox, response_string)
        self.global_vars.response_textbox.configure(state="disabled")

    def update_response_ui_and_read_now(self):
        """Get response from LLM right away
        Update the Response UI with the response
        Read the response
        """
        self.update_response_ui_now()

        # Set event to play the recording audio
        self.global_vars.audio_player.speech_text_available.set()

    def set_transcript_state(self):
        """Enables, disables transcription.
           Text of menu item File -> Pause Transcription toggles accordingly"""
        root_logger.info(temp_ui_callbacks.set_transcript_state.__name__)
        self.global_vars.transcriber.transcribe = not self.global_vars.transcriber.transcribe
        if self.global_vars.transcriber.transcribe:
            self.global_vars.filemenu.entryconfigure(1, label="Pause Transcription")
        else:
            self.global_vars.filemenu.entryconfigure(1, label="Start Transcription")

@st.cache_data
def write_in_textbox(textbox: st.text_area, text: str):
    """Update the text of textbox with the given text
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    textbox.delete("0.0", "end")
    textbox.insert("0.0", text)
@st.cache_data
def update_transcript_ui(transcriber: AudioTranscriber, textbox:st.text_area):
    global last_transcript_ui_update_time
    global global_vars_module

    if global_vars_module is None:
        global_vars_module = GlobalVars.TranscriptionGlobals()

    if last_transcript_ui_update_time < global_vars_module.convo.last_update:
        transcript_string = transcriber.get_transcript()
        write_in_textbox(textbox, transcript_string)
        textbox.see("end")
        last_transcript_ui_update_time = datetime.datetime.now()

    textbox.after(constants.TRANSCRIPT_UI_UPDATE_DELAY_DURATION_MS,
                  update_transcript_ui, transcriber, textbox)    

@st.cache_data
def update_response_ui(responder: GPTResponder,
                       textbox: st.text_area,
                       freeze_state):
    """Update the text of response textbox with the given text
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    if not freeze_state[0]:
        response = responder.response

        textbox.configure(state="normal")
        write_in_textbox(textbox, response)
        textbox.configure(state="disabled")

    textbox.after(300, update_response_ui, responder, textbox, freeze_state)

@st.cache_data
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
        conversation = st.text_area("Conversation", height=350)

    with transcription_col:
        transcription = st.text_area("Transcription", height=350)

    #middle components
    languages_box = st.selectbox("Languages", options=(LANGUAGES_DICT.values()), placeholder="Languages")

    #lower button components
    toggle_col, button_col =st.columns((30,12),gap="large")

    with toggle_col:
        speaker_button = st.toggle("Speaker", on_change=ui_cb.enable_disable_speaker)
        microphone_button =st.toggle("Microphone", on_change=ui_cb.enable_disable_microphone)

    with button_col:    
        suggest = st.button("Suggest Responses")
        csuggest = st.button("Suggest Responses Continuously")

    #sidebar components
    sidebar_copy_button = st.sidebar.button("Copy conversation")
    sidebar_download_button = st.sidebar.download_button("Download your conversation","one") #data=ui_cb.global_vars.transcriber.get_transcript()
    sidebar_clear_chat = st.sidebar.button("Clear Chat")
        
    return [conversation, transcription, languages_box, sidebar_download_button, sidebar_clear_chat,
            sidebar_copy_button, speaker_button, microphone_button, suggest, csuggest]

main_ui = create_temp_ui()

           
        

   
