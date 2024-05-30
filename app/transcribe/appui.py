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
from uicomp.selectable_text import SelectableText


logger = al.get_module_logger(al.UI_LOGGER)
UI_FONT_SIZE = 20
# Order of initialization can be unpredictable in python based on where imports are placed.
# Setting it to None so comparison is deterministic in update_transcript_ui method
last_transcript_ui_update_time: datetime.datetime = None
global_vars_module: TranscriptionGlobals = T_GLOBALS
pop_up = None


class AppUI(ctk.CTk):
    """Encapsulates all UI functionality for the app
    """
    global_vars: TranscriptionGlobals
    ui_filename: str = None

    def __init__(self, config: dict):
        super().__init__()
        self.global_vars = TranscriptionGlobals()

        self.global_vars.main_window = self
        self.create_ui_components(config=config)
        self.set_audio_device_menus(config=config)

    def start(self):
        """Start showing the UI
        """
        self.mainloop()

    def update_last_row(self, speaker: str, input_text: str):
        # Update the line for this speaker

        # Delete row starting with speaker
        self.transcript_text.delete_row_starting_with(start_text=speaker)
        self.transcript_text.replace_multiple_newlines()

        # Add new line to end, since it was cleared by previous operation
        self.transcript_text.add_text_to_bottom('\n')

        # Add a new row to the bottom with new text
        self.transcript_text.add_text_to_bottom(input_text)

        self.transcript_text.scroll_to_bottom()

    def update_initial_transcripts(self):
        """Set initial transcript in UI.
        """
        update_transcript_ui(self.global_vars.transcriber,
                             self.transcript_text)
        update_response_ui(self.global_vars.responder,
                           self.response_textbox,
                           self.update_interval_slider_label,
                           self.update_interval_slider)
        self.global_vars.convo.set_handlers(self.update_last_row,
                                            self.transcript_text.add_text_to_bottom)

    def clear_transcript(self):
        """Clear transcript from all places where it exists.
        """
        self.transcript_text.clear_all_text()
        self.global_vars.transcriber.clear_transcriber_context(self.global_vars.audio_queue)

    def create_ui_components(self, config: dict):
        """Create all UI components
        """
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Transcribe")
        self.configure(bg='#252422')
        self.geometry("1200x800")

        # Frame for the main content
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.create_menus()

        # Left side: SelectableTextComponent
        self.transcript_text: SelectableText = SelectableText(self.main_frame)
        self.transcript_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.transcript_text.set_callbacks(self.global_vars.convo.on_convo_select)

        # Right side
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # LLM Response textbox
        self.min_response_textbox_width = 300
        self.response_textbox = ctk.CTkTextbox(self.right_frame, self.min_response_textbox_width,
                                               font=("Arial", UI_FONT_SIZE),
                                               text_color='#639cdc',
                                               wrap="word")
        self.response_textbox.pack(fill="both", expand=True)
        self.response_textbox.insert("0.0", prompts.INITIAL_RESPONSE)

        # Bottom Frame for buttons
        self.bottom_frame = ctk.CTkFrame(self, border_color="white", border_width=2)
        self.bottom_frame.pack(side="bottom", fill="both", pady=10)

        response_enabled = bool(config['General']['continuous_response'])
        b_text = "Suggest Responses Continuously" if not response_enabled else "Do Not Suggest Responses Continuously"
        self.continuous_response_button = ctk.CTkButton(self.bottom_frame, text=b_text)
        self.continuous_response_button.grid(row=0, column=4, padx=10, pady=3, sticky="nsew")
        self.continuous_response_button.configure(command=self.freeze_unfreeze)

        self.response_now_button = ctk.CTkButton(self.bottom_frame, text="Suggest Response Now")
        self.response_now_button.grid(row=1, column=4, padx=10, pady=3, sticky="nsew")
        self.response_now_button.configure(command=self.get_response_now)

        self.read_response_now_button = ctk.CTkButton(self.bottom_frame, text="Suggest Response and Read")
        self.read_response_now_button.grid(row=2, column=4, padx=10, pady=3, sticky="nsew")
        self.read_response_now_button.configure(command=self.update_response_ui_and_read_now)

        self.summarize_button = ctk.CTkButton(self.bottom_frame, text="Summarize")
        self.summarize_button.grid(row=3, column=4, padx=10, pady=3, sticky="nsew")
        self.summarize_button.configure(command=self.summarize)

        # Continuous LLM Response label, and slider
        self.update_interval_slider_label = ctk.CTkLabel(self.bottom_frame, text="", font=("Arial", 12),
                                                         text_color="#FFFCF2")
        self.update_interval_slider_label.grid(row=0, column=0, columnspan=4, padx=10, pady=3, sticky="nsew")
        self.update_interval_slider = ctk.CTkSlider(self.bottom_frame, from_=1, to=30, width=300,  # height=5,
                                                    number_of_steps=29)
        self.update_interval_slider.set(config['General']['llm_response_interval'])
        self.update_interval_slider.grid(row=1, column=0, columnspan=4, padx=10, pady=3, sticky="nsew")
        self.update_interval_slider.configure(command=self.update_interval_slider_value)

        label_text = f'LLM Response interval: {int(self.update_interval_slider.get())} seconds'
        self.update_interval_slider_label.configure(text=label_text)

        # Speech to text language selection label, dropdown
        audio_lang_label = ctk.CTkLabel(self.bottom_frame, text="Audio Lang: ",
                                        font=("Arial", 12),
                                        text_color="#FFFCF2")
        audio_lang_label.grid(row=2, column=0, padx=10, pady=3, sticky='nw')

        audio_lang = config['OpenAI']['audio_lang']
        self.audio_lang_combobox = ctk.CTkOptionMenu(self.bottom_frame, width=15, values=list(LANGUAGES_DICT.values()))
        self.audio_lang_combobox.set(audio_lang)
        self.audio_lang_combobox.grid(row=2, column=1, ipadx=60, padx=10, pady=3, sticky="ne")
        self.audio_lang_combobox.configure(command=self.set_audio_language)

        # LLM Response language selection label, dropdown
        response_lang_label = ctk.CTkLabel(self.bottom_frame,
                                           text="Response Lang: ",
                                           font=("Arial", 12), text_color="#FFFCF2")
        response_lang_label.grid(row=2, column=2, padx=10, pady=3, sticky="nw")

        response_lang = config['OpenAI']['response_lang']
        self.response_lang_combobox = ctk.CTkOptionMenu(self.bottom_frame, width=15,
                                                        values=list(LANGUAGES_DICT.values()))
        self.response_lang_combobox.set(response_lang)
        self.response_lang_combobox.grid(row=2, column=3, ipadx=60, padx=10, pady=3, sticky="ne")
        self.response_lang_combobox.configure(command=self.set_response_language)

        self.github_link = ctk.CTkLabel(self.bottom_frame, text="Star the Github Repo",
                                        text_color="#639cdc", cursor="hand2")
        self.github_link.grid(row=3, column=0, padx=10, pady=3, sticky="wn")
        self.github_link.bind('<Button-1>', lambda e:
                              self.open_link('https://github.com/vivekuppal/transcribe?referer=desktop'))

        self.issue_link = ctk.CTkLabel(self.bottom_frame, text="Report an issue", text_color="#639cdc", cursor="hand2")
        self.issue_link.grid(row=3, column=1, padx=10, pady=3, sticky="wn")
        self.issue_link.bind('<Button-1>', lambda e: self.open_link(
            'https://github.com/vivekuppal/transcribe/issues/new?referer=desktop'))

        # Create right click menu for transcript textbox.
        # This displays only inside the speech to text textbox
        self.transcript_text.add_right_click_menu(label="Generate response for selected text",
                                                  command=self.get_response_selected_now)
        self.transcript_text.add_right_click_menu(label="Save Transcript to File", command=self.save_file)
        self.transcript_text.add_right_click_menu(label="Clear Audio Transcript", command=self.clear_transcript)
        self.transcript_text.add_right_click_menu(label="Copy Transcript to Clipboard", command=self.copy_to_clipboard)
        self.transcript_text.add_right_click_menu(label="Edit line", command=self.edit_current_line)
        self.transcript_text.add_right_menu_separator()
        self.transcript_text.add_right_click_menu(label="Quit", command=self.quit)

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
            self.continuous_response_button.configure(state='disabled')
            self.response_now_button.configure(state='disabled')
            self.read_response_now_button.configure(state='disabled')
            self.summarize_button.configure(state='disabled')

            tt_msg = 'Add API Key in override.yaml to enable button'
            # Add tooltips for disabled buttons
            ToolTip(self.continuous_response_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(self.response_now_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(self.read_response_now_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)
            ToolTip(self.summarize_button, msg=tt_msg,
                    delay=0.01, follow=True, parent_kwargs={"padx": 3, "pady": 3},
                    padx=7, pady=7)

        # self.grid_rowconfigure(0, weight=100)
        # self.grid_rowconfigure(1, weight=1)
        # self.grid_rowconfigure(2, weight=1)
        # self.grid_rowconfigure(3, weight=1)
        # self.grid_columnconfigure(0, weight=1)
        # self.grid_columnconfigure(1, weight=1)

    def edit_current_line(self):
        """Edit the selected line of text required
        """
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")

            current_line = self.transcript_text.text_widget.index("insert linestart")
            current_line_text = self.transcript_text.text_widget.get(current_line, f"{current_line} lineend")

            edit_window = tk.Toplevel(self)
            edit_window.title("Edit Line")
            edit_window.configure(background='#252422')

            edit_text = tk.Text(edit_window, wrap="word", height=10, width=50,
                                bg='#252422', font=("Arial", 20),
                                foreground='#639cdc')
            edit_text.pack(expand=True, fill='both')
            # Separate Person, text in this line
            end_speaker = current_line_text.find(':')
            if end_speaker == -1:
                # Could not determine speaker in text
                return
            speaker: str = current_line_text[:end_speaker].strip()
            speaker_text: str = current_line_text[end_speaker+1:].strip()
            if speaker_text[0] == '[':
                speaker_text = speaker_text[1:]
            if speaker_text[-1] == ']':
                speaker_text = speaker_text[:-1]
            edit_text.insert(tk.END, speaker_text)

            def save_edit():
                # Needs to do 3 things
                # 1. Edit the text in SelectableText class
                # 2. Edit the convo object
                # 3. Save in DBs
                new_text = edit_text.get("1.0", tk.END).strip()
                self.transcript_text.text_widget.configure(state="normal")
                self.transcript_text.text_widget.delete(current_line, f"{current_line} lineend")
                self.transcript_text.text_widget.insert(current_line, f'{speaker}: {new_text}')
                self.transcript_text.text_widget.configure(state="disabled")
                # Separate persona, text
                convo_id = self.global_vars.convo.get_convo_id(persona=speaker, input_text=speaker_text)
                self.global_vars.convo.update_conversation_by_id(persona=speaker, convo_id=convo_id, text=new_text)
                edit_window.destroy()

            def cancel_edit():
                edit_window.destroy()
            save_button = ctk.CTkButton(edit_window, text="Save", command=save_edit)
            save_button.pack(side=ctk.LEFT, padx=10, pady=10)

            cancel_button = ctk.CTkButton(edit_window, text="Cancel", command=cancel_edit)
            cancel_button.pack(side=ctk.RIGHT, padx=10, pady=10)

        except tk.TclError:
            pass  # No text in the line

    def create_menus(self):
        """Create menus for the application
        """
        # Create the menu bar
        menubar = tk.Menu(self)

        # Create a file menu
        self.filemenu = tk.Menu(menubar, tearoff=False)

        # Add a "Save" menu item to the file menu
        self.filemenu.add_command(label="Save Transcript to File", command=self.save_file)

        # Add a "Pause" menu item to the file menu
        self.filemenu.add_command(label="Pause Transcription", command=self.set_transcript_state)

        # Add a "Quit" menu item to the file menu
        self.filemenu.add_command(label="Quit", command=self.quit)

        # Add the file menu to the menu bar
        menubar.add_cascade(label="File", menu=self.filemenu)

        # Create an edit menu
        self.editmenu = tk.Menu(menubar, tearoff=False)

        # Add a "Clear Audio Transcript" menu item to the file menu
        self.editmenu.add_command(label="Clear Audio Transcript", command=self.clear_transcript)

        # Add a "Copy To Clipboard" menu item to the file menu
        self.editmenu.add_command(label="Copy Transcript to Clipboard",
                                  command=self.copy_to_clipboard)

        # Add "Disable Speaker" menu item to file menu
        self.editmenu.add_command(label="Disable Speaker",
                                  command=self.enable_disable_speaker)

        # Add "Disable Microphone" menu item to file menu
        self.editmenu.add_command(label="Disable Microphone",
                                  command=self.enable_disable_microphone)

        # Add the edit menu to the menu bar
        menubar.add_cascade(label="Edit", menu=self.editmenu)

        # Create help menu, add items in help menu
        helpmenu = tk.Menu(menubar, tearoff=False)
        helpmenu.add_command(label="Github Repo", command=self.open_github)
        helpmenu.add_command(label="Star the Github repo", command=self.open_github)
        helpmenu.add_command(label="Report an Issue", command=self.open_support)
        menubar.add_cascade(label="Help", menu=helpmenu)

        # Add the menu bar to the main window
        self.config(menu=menubar)

    def set_audio_device_menus(self, config):
        if config['General']['disable_speaker']:
            print('[INFO] Disabling Speaker')
            self.enable_disable_speaker()

        if config['General']['disable_mic']:
            print('[INFO] Disabling Microphone')
            self.enable_disable_microphone()

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
            self.continuous_response_button.configure(
                text="Suggest Responses Continuously" if not self.global_vars.responder.enabled else "Do Not Suggest Responses Continuously"
            )
        except Exception as e:
            logger.error(f"Error toggling responder state: {e}")

    def enable_disable_speaker(self):
        """Toggles the state of speaker
        """
        try:
            self.global_vars.speaker_audio_recorder.enabled = not self.global_vars.speaker_audio_recorder.enabled
            self.editmenu.entryconfigure(2, label="Disable Speaker" if self.global_vars.speaker_audio_recorder.enabled else "Enable Speaker")
            self.capture_action(f'{"Enabled " if self.global_vars.speaker_audio_recorder.enabled else "Disabled "} speaker input')
        except Exception as e:
            logger.error(f"Error toggling speaker state: {e}")

    def enable_disable_microphone(self):
        """Toggles the state of microphone
        """
        try:
            self.global_vars.user_audio_recorder.enabled = not self.global_vars.user_audio_recorder.enabled
            self.editmenu.entryconfigure(3, label="Disable Microphone" if self.global_vars.user_audio_recorder.enabled else "Enable Microphone")
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
            self.update_interval_slider_label.configure(text=label_text)
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
            self.response_textbox.configure(state="normal")
            if response_string:
                write_in_textbox(self.response_textbox, response_string)
            self.response_textbox.configure(state="disabled")
            self.response_textbox.see("end")
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
        selected_text = self.transcript_text.selection_get()
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
                self.filemenu.entryconfigure(1, label="Pause Transcription")
            else:
                self.filemenu.entryconfigure(1, label="Start Transcription")
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


def popup_msg_no_close_threaded(title, msg):
    """Create a pop up with no close button.
    """
    global pop_up  # pylint: disable=W0603
    try:
        popup = ctk.CTkToplevel(T_GLOBALS.main_window)
        popup.geometry("100x50")
        popup.title(title)
        label = ctk.CTkLabel(popup, text=msg, font=("Arial", 12),
                             text_color="#FFFCF2")
        label.pack(side="top", fill="x", pady=10)
        pop_up = popup
        popup.lift()
    except Exception as e:
        # Sometimes get the error - calling Tcl from different apartment
        logger.info('Exception in popup_msg_no_close_threaded')
        logger.info(e)
        return


def popup_msg_no_close(title: str, msg: str):
    """Create a popup that the caller is responsible for closing
    using the destroy method
    """
    kwargs = {}
    kwargs['title'] = title
    kwargs['msg'] = msg
    pop_ui_thread = threading.Thread(target=popup_msg_no_close_threaded,
                                     name='Pop up thread',
                                     kwargs=kwargs)
    pop_ui_thread.daemon = True
    pop_ui_thread.start()
    # Give a chance for the thread to initialize
    # When API key is not specified, need the thread to initialize to
    # allow summarize window to show and ultimately be closed.
    time.sleep(0.1)


def popup_msg_close_button(title: str, msg: str):
    """Create a popup that the caller is responsible for closing
    using the destroy method
    """
    popup = ctk.CTkToplevel(T_GLOBALS.main_window)
    popup.geometry("380x710")
    popup.title(title)
    txtbox = ctk.CTkTextbox(popup, width=350, height=600, font=("Arial", UI_FONT_SIZE),
                            text_color='#FFFCF2', wrap="word")
    txtbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    txtbox.insert("0.0", msg)

    def copy_summary_to_clipboard():
        pyperclip.copy(txtbox.cget("text"))

    copy_button = ctk.CTkButton(popup, text="Copy to Clipboard", command=copy_summary_to_clipboard)
    copy_button.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

    close_button = ctk.CTkButton(popup, text="Close", command=popup.destroy)
    close_button.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
    popup.lift()


def write_in_textbox(textbox: ctk.CTkTextbox, text: str):
    """Update the text of textbox with the given text
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    # Get current selection attributes, so they can be preserved after writing new text
    a: tuple = textbox.tag_ranges('sel')
    # (<string object: '5.22'>, <string object: '5.85'>)
    textbox.delete("0.0", "end")
    textbox.insert("0.0", text)
    if len(a):
        textbox.tag_add('sel', a[0], a[1])


def update_transcript_ui(transcriber: AudioTranscriber, textbox: SelectableText):
    """Update the text of transcription textbox with the given text
        Args:
          transcriber: AudioTranscriber Object
          textbox: SelectableText to be updated
    """

    global last_transcript_ui_update_time  # pylint: disable=W0603
    global global_vars_module  # pylint: disable=W0603

    if global_vars_module is None:
        global_vars_module = TranscriptionGlobals()

    # None comparison is for initialization
    if last_transcript_ui_update_time is None or last_transcript_ui_update_time < global_vars_module.convo.last_update:
        transcript_strings = transcriber.get_transcript()
        if isinstance(transcript_strings, list):
            for line in transcript_strings:
                textbox.add_text_to_bottom(line)
        else:
            textbox.add_text_to_bottom(transcript_strings)
        # write_in_textbox(textbox, transcript_string)
        textbox.scroll_to_bottom()
        last_transcript_ui_update_time = datetime.datetime.utcnow()


def update_response_ui(responder: gr.GPTResponder,
                       textbox: ctk.CTkTextbox,
                       update_interval_slider_label: ctk.CTkLabel,
                       update_interval_slider: ctk.CTkSlider):
    """Update the text of response textbox with the given text
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    global global_vars_module  # pylint: disable=W0603

    if global_vars_module is None:
        global_vars_module = TranscriptionGlobals()
    response = None

    # global_vars_module.responder.enabled --> This is continous response mode from LLM
    # global_vars_module.update_response_now --> Get Response now from LLM
    if global_vars_module.responder.enabled or global_vars_module.update_response_now:
        response = responder.response

    if global_vars_module.previous_response is not None:
        # User selection of previous response takes precedence over
        # Automated ping of LLM Response
        response = global_vars_module.previous_response

    if response:
        textbox.configure(state="normal")
        write_in_textbox(textbox, response)
        textbox.configure(state="disabled")
        textbox.see("end")

    update_interval = int(update_interval_slider.get())
    responder.update_response_interval(update_interval)
    update_interval_slider_label.configure(text=f'LLM Response interval: '
                                           f'{update_interval} seconds')

    textbox.after(300, update_response_ui, responder, textbox,
                  update_interval_slider_label, update_interval_slider)
