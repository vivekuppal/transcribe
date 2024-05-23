import threading
import datetime
import time
import tkinter as tk
import webbrowser
import pyperclip
import customtkinter as ctk
from tktooltip import ToolTip
from audio_transcriber import AudioTranscriber
import prompts
from global_vars import TranscriptionGlobals, T_GLOBALS
import constants
import gpt_responder as gr
from tsutils.language import LANGUAGES_DICT
from tsutils import utilities
from tsutils import app_logging as al
from tsutils import configuration

logger = al.get_module_logger(al.UI_LOGGER)
UI_FONT_SIZE = 20
# Order of initialization can be unpredictable in python based on where imports are placed.
# Setting it to None so comparison is deterministic in update_transcript_ui method
last_transcript_ui_update_time: datetime.datetime = None
global_vars_module: TranscriptionGlobals = T_GLOBALS
pop_up = None


class AppUI:
    global_vars: TranscriptionGlobals
    ui_filename: str = None

    def __init__(self, config: dict):
        self.global_vars = TranscriptionGlobals()

        root = ctk.CTk()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        root.title("Transcribe")
        root.configure(bg='#252422')
        root.geometry("1000x600")

        # Create the menu bar
        menubar = tk.Menu(root)

        # Create a file menu
        filemenu = tk.Menu(menubar, tearoff=False)

        # Add a "Save" menu item to the file menu
        filemenu.add_command(label="Save Transcript to File", command=self.save_file)

        # Add a "Pause" menu item to the file menu
        filemenu.add_command(label="Pause Transcription", command=self.set_transcript_state)

        # Add a "Quit" menu item to the file menu
        filemenu.add_command(label="Quit", command=root.quit)

        # Add the file menu to the menu bar
        menubar.add_cascade(label="File", menu=filemenu)

        # Create an edit menu
        editmenu = tk.Menu(menubar, tearoff=False)

        # Add a "Clear Audio Transcript" menu item to the file menu
        editmenu.add_command(label="Clear Audio Transcript", command=lambda:
                             self.global_vars.transcriber.clear_transcriber_context(self.global_vars.audio_queue))

        # Add a "Copy To Clipboard" menu item to the file menu
        editmenu.add_command(label="Copy Transcript to Clipboard", command=self.copy_to_clipboard)

        # Add "Disable Speaker" menu item to file menu
        editmenu.add_command(label="Disable Speaker", command=lambda: self.enable_disable_speaker(editmenu))

        # Add "Disable Microphone" menu item to file menu
        editmenu.add_command(label="Disable Microphone", command=lambda: self.enable_disable_microphone(editmenu))

        # Add the edit menu to the menu bar
        menubar.add_cascade(label="Edit", menu=editmenu)

        # Create help menu, add items in help menu
        helpmenu = tk.Menu(menubar, tearoff=False)
        helpmenu.add_command(label="Github Repo", command=self.open_github)
        helpmenu.add_command(label="Star the Github repo", command=self.open_github)
        helpmenu.add_command(label="Report an Issue", command=self.open_support)
        menubar.add_cascade(label="Help", menu=helpmenu)

        # Add the menu bar to the main window
        root.config(menu=menubar)

        # Speech to Text textbox
        transcript_textbox = ctk.CTkTextbox(root, width=300, font=("Arial", UI_FONT_SIZE),
                                            text_color='#FFFCF2', wrap="word")
        transcript_textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=3, sticky="nsew")

        # LLM Response textbox
        response_textbox = ctk.CTkTextbox(root, width=300, font=("Arial", UI_FONT_SIZE),
                                          text_color='#639cdc', wrap="word")
        response_textbox.grid(row=0, column=2, padx=10, pady=3, sticky="nsew")
        response_textbox.insert("0.0", prompts.INITIAL_RESPONSE)

        response_enabled = bool(config['General']['continuous_response'])
        b_text = "Suggest Responses Continuously" if not response_enabled else "Do Not Suggest Responses Continuously"
        continuous_response_button = ctk.CTkButton(root, text=b_text)
        continuous_response_button.grid(row=1, column=2, padx=10, pady=3, sticky="nsew")

        response_now_button = ctk.CTkButton(root, text="Suggest Response Now")
        response_now_button.grid(row=2, column=2, padx=10, pady=3, sticky="nsew")

        read_response_now_button = ctk.CTkButton(root, text="Suggest Response and Read")
        read_response_now_button.grid(row=3, column=2, padx=10, pady=3, sticky="nsew")

        summarize_button = ctk.CTkButton(root, text="Summarize")
        summarize_button.grid(row=4, column=2, padx=10, pady=3, sticky="nsew")

        # Continuous LLM Response label, and slider
        update_interval_slider_label = ctk.CTkLabel(root, text="", font=("Arial", 12),
                                                    text_color="#FFFCF2")
        update_interval_slider_label.grid(row=1, column=0, columnspan=2, padx=10, pady=3, sticky="nsew")

        update_interval_slider = ctk.CTkSlider(root, from_=1, to=30, width=300,  # height=5,
                                               number_of_steps=29)
        update_interval_slider.set(config['General']['llm_response_interval'])
        update_interval_slider.grid(row=2, column=0, columnspan=2, padx=10, pady=3, sticky="nsew")

        # Speech to text language selection label, dropdown
        audio_lang_label = ctk.CTkLabel(root, text="Audio Lang: ",
                                        font=("Arial", 12),
                                        text_color="#FFFCF2")
        audio_lang_label.grid(row=3, column=0, padx=10, pady=3, sticky="nw")

        audio_lang = config['OpenAI']['audio_lang']
        audio_lang_combobox = ctk.CTkOptionMenu(root, width=15, values=list(LANGUAGES_DICT.values()))
        audio_lang_combobox.set(audio_lang)
        audio_lang_combobox.grid(row=3, column=0, ipadx=60, padx=10, pady=3, sticky="ne")

        # LLM Response language selection label, dropdown
        response_lang_label = ctk.CTkLabel(root,
                                           text="Response Lang: ",
                                           font=("Arial", 12), text_color="#FFFCF2")
        response_lang_label.grid(row=3, column=1, padx=10, pady=3, sticky="nw")

        response_lang = config['OpenAI']['response_lang']
        response_lang_combobox = ctk.CTkOptionMenu(root, width=15, values=list(LANGUAGES_DICT.values()))
        response_lang_combobox.set(response_lang)
        response_lang_combobox.grid(row=3, column=1, ipadx=60, padx=10, pady=3, sticky="ne")

        github_link = ctk.CTkLabel(root, text="Star the Github Repo",
                                   text_color="#639cdc", cursor="hand2")
        github_link.grid(row=4, column=0, padx=10, pady=3, sticky="wn")

        issue_link = ctk.CTkLabel(root, text="Report an issue", text_color="#639cdc", cursor="hand2")
        issue_link.grid(row=4, column=1, padx=10, pady=3, sticky="wn")

        # Create right click menu for transcript textbox.
        # This displays only inside the speech to text textbox
        m = tk.Menu(root, tearoff=0)
        m.add_command(label="Generate response for selected text",
                      command=self.get_response_selected_now)
        m.add_command(label="Save Transcript to File", command=self.save_file)
        m.add_command(label="Clear Audio Transcript", command=lambda:
                      self.global_vars.transcriber.clear_transcriber_context(self.global_vars.audio_queue))
        m.add_command(label="Copy Transcript to Clipboard", command=self.copy_to_clipboard)
        m.add_separator()
        m.add_command(label="Quit", command=root.quit)

        chat_inference_provider = config['General']['chat_inference_provider']
        if chat_inference_provider == 'openai':
            api_key = config['OpenAI']['api_key']
            base_url = config['OpenAI']['base_url']
            model = config['OpenAI']['ai_model']
        elif chat_inference_provider == 'together':
            api_key = config['Together']['api_key']
            base_url = config['Together']['base_url']
            model = config['Together']['ai_model']

        if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
            # Disable buttons that interact with backend services
            continuous_response_button.configure(state='disabled')
            response_now_button.configure(state='disabled')
            read_response_now_button.configure(state='disabled')
            summarize_button.configure(state='disabled')

            tt_msg = 'Add API Key in override.yaml to enable button'
            # Add tooltips for disabled buttons
            ToolTip(continuous_response_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(response_now_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(read_response_now_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(summarize_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)

    def copy_to_clipboard(self):
        """Copy transcription text data to clipboard.
           Does not include responses from assistant.
        """
        logger.info(AppUI.copy_to_clipboard.__name__)
        self.capture_action("Copy transcript to clipboard")
        try:
            pyperclip.copy(self.global_vars.transcriber.get_transcript())
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")

    def save_file(self):
        """Save transcription text data to file.
           Does not include responses from assistant.
        """
        logger.info(AppUI.save_file.__name__)
        filename = ctk.filedialog.asksaveasfilename(defaultextension='.txt',
                                                    title='Save Transcription',
                                                    filetypes=[("Text Files", "*.txt")])
        self.capture_action(f'Save transcript to file:{filename}')
        if not filename:
            return
        try:
            with open(file=filename, mode="w", encoding='utf-8') as file_handle:
                file_handle.write(self.global_vars.transcriber.get_transcript())
        except Exception as e:
            logger.error(f"Error saving file {filename}: {e}")

    def freeze_unfreeze(self):
        """Respond to start / stop of seeking responses from openAI API
        """
        logger.info(AppUI.freeze_unfreeze.__name__)
        try:
            # Invert the state
            self.global_vars.responder.enabled = not self.global_vars.responder.enabled
            self.capture_action(f'{"Enabled " if self.global_vars.responder.enabled else "Disabled "} continuous LLM responses')
            self.global_vars.freeze_button.configure(
                text="Suggest Responses Continuously" if not self.global_vars.responder.enabled else "Do Not Suggest Responses Continuously"
            )
        except Exception as e:
            logger.error(f"Error toggling responder state: {e}")

    def enable_disable_speaker(self, editmenu):
        """Toggles the state of speaker
        """
        try:
            self.global_vars.speaker_audio_recorder.enabled = not self.global_vars.speaker_audio_recorder.enabled
            editmenu.entryconfigure(2, label="Disable Speaker" if self.global_vars.speaker_audio_recorder.enabled else "Enable Speaker")
            self.capture_action(f'{"Enabled " if self.global_vars.speaker_audio_recorder.enabled else "Disabled "} speaker input')
        except Exception as e:
            logger.error(f"Error toggling speaker state: {e}")

    def enable_disable_microphone(self, editmenu):
        """Toggles the state of microphone
        """
        try:
            self.global_vars.user_audio_recorder.enabled = not self.global_vars.user_audio_recorder.enabled
            editmenu.entryconfigure(3, label="Disable Microphone" if self.global_vars.user_audio_recorder.enabled else "Enable Microphone")
            self.capture_action(f'{"Enabled " if self.global_vars.user_audio_recorder.enabled else "Disabled "} microphone input')
        except Exception as e:
            logger.error(f"Error toggling microphone state: {e}")

    def update_interval_slider_value(self, slider_value):
        """Update interval slider label to match the slider value
           Update the config value
        """
        try:
            config_obj = configuration.Config()
            # Save config
            altered_config = {'General': {'llm_response_interval': int(slider_value)}}
            config_obj.add_override_value(altered_config)

            label_text = f'LLM Response interval: {int(slider_value)} seconds'
            self.global_vars.update_interval_slider_label.configure(text=label_text)
            self.capture_action(f'Update LLM response interval to {int(slider_value)}')
        except Exception as e:
            logger.error(f"Error updating slider value: {e}")

    def get_response_now(self):
        """Get response from LLM right away
           Update the Response UI with the response
        """
        if self.global_vars.update_response_now:
            # We are already in the middle of getting a response
            return
        # We need a separate thread to ensure UI is responsive as responses are
        # streamed back. Without the thread UI appears stuck as we stream the
        # responses back
        self.capture_action('Get LLM response now')
        response_ui_thread = threading.Thread(target=self.get_response_now_threaded,
                                              name='GetResponseNow')
        response_ui_thread.daemon = True
        response_ui_thread.start()

    def get_response_selected_now_threaded(self, text: str):
        """Update response UI in a separate thread
        """
        self.update_response_ui_threaded(lambda: self.global_vars.responder.generate_response_for_selected_text(text))

    def get_response_now_threaded(self):
        """Update response UI in a separate thread
        """
        self.update_response_ui_threaded(self.global_vars.responder.generate_response_from_transcript_no_check)

    def update_response_ui_threaded(self, response_generator):
        """Helper method to update response UI in a separate thread
        """
        try:
            self.global_vars.update_response_now = True
            response_string = response_generator()
            self.global_vars.update_response_now = False
            # Set event to play the recording audio if required
            if self.global_vars.read_response:
                self.global_vars.audio_player_var.speech_text_available.set()
            self.global_vars.response_textbox.configure(state="normal")
            if response_string:
                write_in_textbox(self.global_vars.response_textbox, response_string)
            self.global_vars.response_textbox.configure(state="disabled")
            self.global_vars.response_textbox.see("end")
        except Exception as e:
            logger.error(f"Error in threaded response: {e}")

    def get_response_selected_now(self):
        """Get response from LLM right away for selected_text
           Update the Response UI with the response
        """
        if self.global_vars.update_response_now:
            # We are already in the middle of getting a response
            return
        # We need a separate thread to ensure UI is responsive as responses are
        # streamed back. Without the thread UI appears stuck as we stream the
        # responses back
        self.capture_action('Get LLM response selected now')
        selected_text = self.global_vars.transcript_textbox.selection_get()
        response_ui_thread = threading.Thread(target=self.get_response_selected_now_threaded,
                                              args=(selected_text,),
                                              name='GetResponseSelectedNow')
        response_ui_thread.daemon = True
        response_ui_thread.start()

    def summarize_threaded(self):
        """Get summary from LLM in a separate thread"""
        global pop_up  # pylint: disable=W0603
        try:
            print('Summarizing...')
            popup_msg_no_close(title='Summary', msg='Creating a summary')
            summary = self.global_vars.responder.summarize()
            # When API key is not specified, give a chance for the thread to initialize

            if pop_up is not None:
                try:
                    pop_up.destroy()
                except Exception as e:
                    # Somehow we get the exception
                    # RuntimeError: main thread is not in main loop
                    logger.info('Exception in summarize_threaded')
                    logger.info(e)

                pop_up = None
            if summary is None:
                popup_msg_close_button(title='Summary',
                                       msg='Failed to get summary. Please check you have a valid API key.')
                return

            # Enhancement here would be to get a streaming summary
            popup_msg_close_button(title='Summary', msg=summary)
        except Exception as e:
            logger.error(f"Error in summarize_threaded: {e}")

    def summarize(self):
        """Get summary response from LLM
        """
        self.capture_action('Get summary from LLM')
        summarize_ui_thread = threading.Thread(target=self.summarize_threaded,
                                               name='Summarize')
        summarize_ui_thread.daemon = True
        summarize_ui_thread.start()

    def update_response_ui_and_read_now(self):
        """Get response from LLM right away
        Update the Response UI with the response
        Read the response
        """
        self.capture_action('Get LLM response now and read aloud')
        self.global_vars.set_read_response(True)
        self.get_response_now()

    def set_transcript_state(self):
        """Enables, disables transcription.
           Text of menu item File -> Pause Transcription toggles accordingly
        """
        logger.info(AppUI.set_transcript_state.__name__)
        try:
            self.global_vars.transcriber.transcribe = not self.global_vars.transcriber.transcribe
            self.capture_action(f'{"Enabled " if self.global_vars.transcriber.transcribe else "Disabled "} transcription.')
            if self.global_vars.transcriber.transcribe:
                self.global_vars.filemenu.entryconfigure(1, label="Pause Transcription")
            else:
                self.global_vars.filemenu.entryconfigure(1, label="Start Transcription")
        except Exception as e:
            logger.error(f"Error setting transcript state: {e}")

    def open_link(self, url: str):
        """Open the link in a web browser
        """
        self.capture_action(f'Navigate to {url}.')
        try:
            webbrowser.open(url=url, new=2)
        except Exception as e:
            logger.error(f"Error opening URL {url}: {e}")

    def open_github(self):
        """Link to git repo main page
        """
        self.capture_action('open_github.')
        self.open_link('https://github.com/vivekuppal/transcribe?referer=desktop')

    def open_support(self):
        """Link to git repo issues page
        """
        self.capture_action('open_support.')
        self.open_link('https://github.com/vivekuppal/transcribe/issues/new?referer=desktop')

    def capture_action(self, action_text: str):
        """Write to file
        """
        try:
            if not self.ui_filename:
                data_dir = utilities.get_data_path(app_name='Transcribe')
                self.ui_filename = utilities.incrementing_filename(filename=f'{data_dir}/logs/ui', extension='txt')
            with open(self.ui_filename, mode='a', encoding='utf-8') as ui_file:
                ui_file.write(f'{datetime.datetime.now()}: {action_text}\n')
        except Exception as e:
            logger.error(f"Error capturing action {action_text}: {e}")

    def set_audio_language(self, lang: str):
        """Alter audio language in memory and persist it in config file
        """
        try:
            self.global_vars.transcriber.stt_model.set_lang(lang)
            config_obj = configuration.Config()
            # Save config
            altered_config = {'OpenAI': {'audio_lang': lang}}
            config_obj.add_override_value(altered_config)
        except Exception as e:
            logger.error(f"Error setting audio language: {e}")

    def set_response_language(self, lang: str):
        """Alter response language in memory and persist it in config file
        """
        try:
            config_obj = configuration.Config()
            altered_config = {'OpenAI': {'response_lang': lang}}
            # Save config
            config_obj.add_override_value(altered_config)
            config_data = config_obj.data

            # Create a new system prompt
            prompt = config_data["General"]["system_prompt"]
            response_lang = config_data["OpenAI"]["response_lang"]
            if response_lang is not None:
                prompt += f'.  Respond exclusively in {response_lang}.'
            convo = self.global_vars.convo
            convo.update_conversation(persona=constants.PERSONA_SYSTEM,
                                      text=prompt,
                                      time_spoken=datetime.datetime.utcnow(),
                                      update_previous=True)
        except Exception as e:
            logger.error(f"Error setting response language: {e}")
