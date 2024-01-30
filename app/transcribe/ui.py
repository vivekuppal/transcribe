import threading
import datetime
import time
import tkinter as tk
import webbrowser
import pyperclip
import customtkinter as ctk
from audio_transcriber import AudioTranscriber
import prompts
from global_vars import TranscriptionGlobals, T_GLOBALS
import constants
import gpt_responder as gr
from tsutils.language import LANGUAGES_DICT
from tsutils import utilities
from tsutils import app_logging as al


root_logger = al.get_logger()
UI_FONT_SIZE = 20
last_transcript_ui_update_time: datetime.datetime = datetime.datetime.utcnow()
global_vars_module: TranscriptionGlobals = T_GLOBALS
pop_up = None


class UICallbacks:
    """All callbacks for UI"""

    global_vars: TranscriptionGlobals

    def __init__(self):
        self.global_vars = TranscriptionGlobals()

    def copy_to_clipboard(self):
        """Copy transcription text data to clipboard.
           Does not include responses from assistant.
        """
        root_logger.info(UICallbacks.copy_to_clipboard.__name__)
        self.capture_action("Copy transcript to clipboard")
        pyperclip.copy(self.global_vars.transcriber.get_transcript())

    def save_file(self):
        """Save transcription text data to file.
           Does not include responses from assistant.
        """
        root_logger.info(UICallbacks.save_file.__name__)
        filename = ctk.filedialog.asksaveasfilename(defaultextension='.txt', title='Save Transcription',
                                                    filetypes=[("Text Files", "*.txt")])
        self.capture_action(f'Save transcript to file:{filename}')
        if filename == '':
            return
        with open(file=filename, mode="w", encoding='utf-8') as file_handle:
            file_handle.write(self.global_vars.transcriber.get_transcript())

    def freeze_unfreeze(self):
        """Respond to start / stop of seeking responses from openAI API"""
        root_logger.info(UICallbacks.freeze_unfreeze.__name__)
        # Invert the state
        self.global_vars.responder.enabled = not self.global_vars.responder.enabled
        self.capture_action(f'{"Enabled " if self.global_vars.responder.enabled else "Disabled "} continuous LLM responses')
        self.global_vars.freeze_button.configure(
            text="Suggest Responses Continuously" if not self.global_vars.responder.enabled else "Do Not Suggest Responses Continuously"
            )

    # to enable/disable speaker/microphone when args are given or button is pressed
    def enable_disable_speaker(self, editmenu):
        """Toggles the state of speaker"""
        self.global_vars.speaker_audio_recorder.enabled = not self.global_vars.speaker_audio_recorder.enabled
        editmenu.entryconfigure(2, label="Disable Speaker" if self.global_vars.speaker_audio_recorder.enabled else "Enable Speaker")
        self.capture_action(f'{"Enabled " if self.global_vars.speaker_audio_recorder.enabled else "Disabled "} speaker input')

    def enable_disable_microphone(self, editmenu):
        """Toggles the state of microphone"""
        self.global_vars.user_audio_recorder.enabled = not self.global_vars.user_audio_recorder.enabled
        editmenu.entryconfigure(3, label="Disable Microphone" if self.global_vars.user_audio_recorder.enabled else "Enable Microphone")
        self.capture_action(f'{"Enabled " if self.global_vars.user_audio_recorder.enabled else "Disabled "} microphone input')

    def update_interval_slider_label(self, slider_value):
        """Update interval slider label to match the slider value"""
        label_text = f'LLM Response interval: {int(slider_value)} seconds'
        self.global_vars.update_interval_slider_label.configure(text=label_text)
        self.capture_action(f'Update LLM response interval to {int(slider_value)}')

    def update_response_ui_now(self):
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
        response_ui_thread = threading.Thread(target=self.update_response_ui_now_threaded,
                                              name='UpdateResponseUINow')
        response_ui_thread.daemon = True
        response_ui_thread.start()

    def update_response_ui_now_threaded(self):
        """Update response ui in a separate thread
        """
        self.global_vars.update_response_now = True
        response_string = self.global_vars.responder.generate_response_from_transcript_no_check()
        self.global_vars.update_response_now = False
        # Set event to play the recording audio if required
        if self.global_vars.read_response:
            self.global_vars.audio_player_var.speech_text_available.set()
        self.global_vars.response_textbox.configure(state="normal")
        write_in_textbox(self.global_vars.response_textbox, response_string)
        self.global_vars.response_textbox.configure(state="disabled")
        self.global_vars.response_textbox.see("end")

    def summarize_threaded(self):
        """Get summary from LLM in a separate thread
        """
        global pop_up  # pylint: disable=W0603
        print('Summarizing...')
        popup_msg_no_close(title='Summary', msg='Creating a summary')
        summary = self.global_vars.responder.summarize()
        # When API key is not specified, give a chance for the thread to initilizw
        
        if pop_up is not None:
            try:
                pop_up.destroy()
            except Exception as e:
                # Somehow we get the exception
                # RuntimeError: main thread is not in main loop
                root_logger.info('Exception in summarize_threaded')
                root_logger.info(e)

            pop_up = None
        if summary is None:
            popup_msg_close_button(title='Summary', msg='Failed to get summary. Please check you have a valid API key.')
            return
        # Enhancement here would be to get a streaming summary
        popup_msg_close_button(title='Summary', msg=summary)

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
        self.update_response_ui_now()

    def set_transcript_state(self):
        """Enables, disables transcription.
           Text of menu item File -> Pause Transcription toggles accordingly"""
        root_logger.info(UICallbacks.set_transcript_state.__name__)
        self.global_vars.transcriber.transcribe = not self.global_vars.transcriber.transcribe
        self.capture_action(f'{"Enabled " if self.global_vars.transcriber.transcribe else "Disabled "} transcription.')
        if self.global_vars.transcriber.transcribe:
            self.global_vars.filemenu.entryconfigure(1, label="Pause Transcription")
        else:
            self.global_vars.filemenu.entryconfigure(1, label="Start Transcription")

    def open_link(self, url: str):
        """Open the link in a web browser"""
        self.capture_action(f'Navigate to {url}.')
        webbrowser.open(url=url, new=2)

    def open_github(self):
        """Link to git repo main page
        """
        webbrowser.open(url='https://github.com/vivekuppal/transcribe?referer=desktop', new=2)

    def open_support(self):
        """Link to git repo issues page
        """
        webbrowser.open(url='https://github.com/vivekuppal/transcribe/issues/new?referer=desktop', new=2)

    def capture_action(self, action_text: str):
        """write to file"""
        filename = utilities.incrementing_filename(filename='logs/ui',
                                                   extension='txt')
        with open(filename, mode='a', encoding='utf-8') as ui_file:
            ui_file.write(f'{datetime.datetime.now()}: {action_text}\n')


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
        root_logger.info('Exception in popup_msg_no_close_threaded')
        root_logger.info(e)
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
    textbox.delete("0.0", "end")
    textbox.insert("0.0", text)


def update_transcript_ui(transcriber: AudioTranscriber, textbox: ctk.CTkTextbox):
    """Update the text of transcription textbox with the given text
        Args:
          transcriber: AudioTranscriber Object
          textbox: textbox to be updated
    """

    global last_transcript_ui_update_time  # pylint: disable=W0603
    global global_vars_module  # pylint: disable=W0603

    if global_vars_module is None:
        global_vars_module = TranscriptionGlobals()

    if last_transcript_ui_update_time < global_vars_module.convo.last_update:
        transcript_string = transcriber.get_transcript()
        write_in_textbox(textbox, transcript_string)
        textbox.see("end")
        last_transcript_ui_update_time = datetime.datetime.utcnow()

    textbox.after(constants.TRANSCRIPT_UI_UPDATE_DELAY_DURATION_MS,
                  update_transcript_ui, transcriber, textbox)


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

    # global_vars_module.responder.enabled --> This is continous response mode from LLM
    # global_vars_module.update_response_now --> Get Response now from LLM
    if global_vars_module.responder.enabled or global_vars_module.update_response_now:
        response = responder.response

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


def create_ui_components(root, config: dict):
    root_logger.info(create_ui_components.__name__)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root.title("Transcribe")
    root.configure(bg='#252422')
    root.geometry("1000x600")

    ui_cb = UICallbacks()
    global_vars = TranscriptionGlobals()

    # Create the menu bar
    menubar = tk.Menu(root)

    # Create a file menu
    filemenu = tk.Menu(menubar, tearoff=False)

    # Add a "Save" menu item to the file menu
    filemenu.add_command(label="Save Transcript to File", command=ui_cb.save_file)

    # Add a "Pause" menu item to the file menu
    filemenu.add_command(label="Pause Transcription", command=ui_cb.set_transcript_state)

    # Add a "Quit" menu item to the file menu
    filemenu.add_command(label="Quit", command=root.quit)

    # Add the file menu to the menu bar
    menubar.add_cascade(label="File", menu=filemenu)

    # Create an edit menu
    editmenu = tk.Menu(menubar, tearoff=False)

    # Add a "Clear Audio Transcript" menu item to the file menu
    editmenu.add_command(label="Clear Audio Transcript", command=lambda:
                         global_vars.transcriber.clear_transcriber_context(global_vars.audio_queue))

    # Add a "Copy To Clipboard" menu item to the file menu
    editmenu.add_command(label="Copy Transcript to Clipboard", command=ui_cb.copy_to_clipboard)

    # Add "Disable Speaker" menu item to file menu
    editmenu.add_command(label="Disable Speaker", command=lambda: ui_cb.enable_disable_speaker(editmenu))

    # Add "Disable Microphone" menu item to file menu
    editmenu.add_command(label="Disable Microphone", command=lambda: ui_cb.enable_disable_microphone(editmenu))

    # See example of add_radiobutton() at https://www.plus2net.com/python/tkinter-menu.php
    # Radiobutton would be a good way to display different languages
    # lang_menu = tk.Menu(menubar, tearoff=False)
    # for lang in LANGUAGES_DICT.values():
    #    model.change_lang
    #    lang_menu.add_command(label=lang, command=model.change_lang)
    # editmenu.add_cascade(menu=lang_menu, label='Languages')

    # Add the edit menu to the menu bar
    menubar.add_cascade(label="Edit", menu=editmenu)

    helpmenu = tk.Menu(menubar, tearoff=False)
    helpmenu.add_command(label="Github Repo", command=ui_cb.open_github)
    helpmenu.add_command(label="Star the Github repo", command=ui_cb.open_github)
    helpmenu.add_command(label="Report an Issue", command=ui_cb.open_support)
    menubar.add_cascade(label="Help", menu=helpmenu)

    # Add the menu bar to the main window
    root.config(menu=menubar)

    transcript_textbox = ctk.CTkTextbox(root, width=300, font=("Arial", UI_FONT_SIZE),
                                        text_color='#FFFCF2', wrap="word")
    transcript_textbox.grid(row=0, column=0, padx=10, pady=20, sticky="nsew")

    response_textbox = ctk.CTkTextbox(root, width=300, font=("Arial", UI_FONT_SIZE),
                                      text_color='#639cdc', wrap="word")
    response_textbox.grid(row=0, column=1, padx=10, pady=20, sticky="nsew")
    response_textbox.insert("0.0", prompts.INITIAL_RESPONSE)

    response_enabled = bool(config['General']['continuous_response'])
    b_text = "Suggest Responses Continuously" if not response_enabled else "Do Not Suggest Responses Continuously"
    freeze_button = ctk.CTkButton(root, text=b_text, command=None)
    freeze_button.grid(row=1, column=1, padx=10, pady=3, sticky="nsew")

    response_now_button = ctk.CTkButton(root, text="Suggest Response Now", command=None)
    response_now_button.grid(row=2, column=1, padx=10, pady=3, sticky="nsew")

    read_response_now_button = ctk.CTkButton(root, text="Suggest Response and Read", command=None)
    read_response_now_button.grid(row=3, column=1, padx=10, pady=3, sticky="nsew")

    summarize_button = ctk.CTkButton(root, text="Summarize", command=None)
    summarize_button.grid(row=4, column=1, padx=10, pady=3, sticky="nsew")

    update_interval_slider_label = ctk.CTkLabel(root, text="", font=("Arial", 12),
                                                text_color="#FFFCF2")
    update_interval_slider_label.grid(row=1, column=0, padx=10, pady=3, sticky="nsew")

    update_interval_slider = ctk.CTkSlider(root, from_=1, to=10, width=300, height=20,
                                           number_of_steps=9)
    update_interval_slider.set(config['General']['response_interval'])
    update_interval_slider.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    lang_combobox = ctk.CTkOptionMenu(root, width=15, values=list(LANGUAGES_DICT.values()))
    lang_combobox.grid(row=3, column=0, ipadx=60, padx=10, sticky="wn")

    github_link = ctk.CTkLabel(root, text="Star the Github Repo", text_color="#639cdc", cursor="hand2")
    github_link.grid(row=3, column=0, padx=10, pady=10, sticky="n")

    issue_link = ctk.CTkLabel(root, text="Report an issue", text_color="#639cdc", cursor="hand2")
    issue_link.grid(row=3, column=0, padx=10, pady=10, sticky="en")

    # Order of returned components is important.
    # Add new components to the end
    return [transcript_textbox, response_textbox, update_interval_slider,
            update_interval_slider_label, freeze_button, lang_combobox,
            filemenu, response_now_button, read_response_now_button, editmenu,
            github_link, issue_link, summarize_button]
