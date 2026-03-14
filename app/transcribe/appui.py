import datetime
import queue
import tkinter as tk
from io import BytesIO
import pyperclip
import customtkinter as ctk
from tkinter import *
from PIL import ImageTk, Image

try:
    from .audio_transcriber import AudioTranscriber
    from .desktop import DesktopCommandBinder, DesktopController, DesktopViewBuilder
    from .global_vars import AppRuntime, create_app_runtime
    from . import gpt_responder as gr
    from .uicomp.selectable_text import SelectableText
except ImportError:
    from audio_transcriber import AudioTranscriber
    from desktop import DesktopCommandBinder, DesktopController, DesktopViewBuilder
    from global_vars import AppRuntime, create_app_runtime
    import gpt_responder as gr
    from uicomp.selectable_text import SelectableText
from tsutils import app_logging as al


logger = al.get_module_logger(al.UI_LOGGER)
UI_FONT_SIZE = 20
UI_POLL_INTERVAL_MS = 50
# Order of initialization can be unpredictable in python based on where imports are placed.
# Setting it to None so comparison is deterministic in update_transcript_ui method
last_transcript_ui_update_time: datetime.datetime = None


class AppUI(ctk.CTk):
    """Encapsulates all UI functionality for the app
    """
    global_vars: AppRuntime
    ui_font_size: int = UI_FONT_SIZE

    def __init__(
        self,
        config: dict,
        runtime: AppRuntime = None,
        controller: DesktopController = None,
        view_builder: DesktopViewBuilder = None,
        command_binder: DesktopCommandBinder = None,
    ):
        super().__init__()
        self.global_vars = runtime or create_app_runtime()
        self.controller = controller or DesktopController(config=config, runtime=self.global_vars)
        self.view_builder = view_builder or DesktopViewBuilder()
        self.command_binder = command_binder or DesktopCommandBinder()
        self.popup_window = None
        self._ui_action_queue: queue.Queue = queue.Queue()

        self.global_vars.main_window = self
        self.controller.bind_ui(self)
        self.create_ui_components(config=config)
        self.set_audio_device_menus(config=config)
        self.after(UI_POLL_INTERVAL_MS, self.process_ui_actions)

    def start(self):
        """Start showing the UI
        """
        self.mainloop()

    def enqueue_ui_action(self, callback, *args, **kwargs):
        """Queue UI work for the Tk main loop."""
        self._ui_action_queue.put((callback, args, kwargs))

    def process_ui_actions(self):
        """Run queued UI actions on the Tk main loop."""
        try:
            while True:
                callback, args, kwargs = self._ui_action_queue.get_nowait()
                try:
                    callback(*args, **kwargs)
                except Exception as exception:
                    logger.error(f"Error processing queued UI action: {exception}")
        except queue.Empty:
            pass

        self.after(UI_POLL_INTERVAL_MS, self.process_ui_actions)

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

    def queue_update_last_row(self, speaker: str, input_text: str):
        """Schedule transcript row replacement on the UI thread."""
        self.enqueue_ui_action(self.update_last_row, speaker, input_text)

    def queue_add_transcript_line(self, input_text: str):
        """Schedule transcript insertion on the UI thread."""
        self.enqueue_ui_action(self.transcript_text.add_text_to_bottom, input_text)

    def write_response_text(self, response_string: str):
        """Render a response string into the response textbox."""
        self.response_textbox.configure(state="normal")
        if response_string:
            write_in_textbox(self.response_textbox, response_string)
        self.response_textbox.configure(state="disabled")
        self.response_textbox.see("end")

    def close_popup(self):
        """Close the currently active popup, if one exists."""
        if self.popup_window is None:
            return

        try:
            self.popup_window.destroy()
        except Exception as exception:
            logger.info('Exception closing popup window')
            logger.info(exception)
        finally:
            self.popup_window = None

    def show_loading_popup(self, title: str, msg: str):
        """Create a temporary status popup on the UI thread."""
        self.close_popup()
        popup = ctk.CTkToplevel(self)
        popup.geometry("220x80")
        popup.title(title)
        label = ctk.CTkLabel(popup, text=msg, font=("Arial", 12), text_color="#FFFCF2")
        label.pack(side="top", fill="x", pady=10, padx=10)
        popup.lift()
        self.popup_window = popup

    def show_message_popup(self, title: str, msg: str):
        """Create a popup with a message and close button."""
        self.close_popup()
        popup = ctk.CTkToplevel(self)
        popup.geometry("380x710")
        popup.title(title)
        txtbox = ctk.CTkTextbox(popup, width=350, height=600, font=("Arial", UI_FONT_SIZE),
                                text_color='#FFFCF2', wrap="word")
        txtbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        txtbox.insert("0.0", msg)

        def copy_summary_to_clipboard():
            try:
                pyperclip.copy(txtbox.get("0.0", "end-1c"))
            except Exception as exception:
                logger.error(f"Error copying popup text to clipboard: {exception}")

        copy_button = ctk.CTkButton(popup, text="Copy to Clipboard", command=copy_summary_to_clipboard)
        copy_button.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        close_button = ctk.CTkButton(popup, text="Close", command=self.close_popup)
        close_button.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        popup.lift()
        self.popup_window = popup

    def show_word_cloud_popup(self, title: str, word_cloud):
        """Create a word cloud popup on the UI thread."""
        self.close_popup()
        popup = ctk.CTkToplevel(self)
        popup.geometry("380x400")
        popup.title(title)

        try:
            buffer = BytesIO()
            word_cloud.to_image().save(buffer, format="PNG")
            buffer.seek(0)
            img = Image.open(buffer)
            img_tk = ImageTk.PhotoImage(img)
        except Exception as exception:
            logger.error(f"Error rendering word cloud to image: {exception}")
            popup.destroy()
            return

        word_cloud_label = ctk.CTkLabel(popup, image=img_tk, text="")
        word_cloud_label.image = img_tk
        word_cloud_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        close_button = ctk.CTkButton(popup, text="Close", command=self.close_popup)
        close_button.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        popup.lift()
        self.popup_window = popup

    def update_initial_transcripts(self):
        """Set initial transcript in UI.
        """
        update_transcript_ui(self.global_vars.transcriber,
                             self.transcript_text,
                             self.global_vars)
        update_response_ui(self.global_vars.responder,
                           self.response_textbox,
                           self.update_interval_slider_label,
                           self.update_interval_slider,
                           self.global_vars)
        self.global_vars.convo.set_handlers(self.queue_update_last_row,
                                            self.queue_add_transcript_line)

    def clear_transcript(self):
        """Clear transcript from all places where it exists.
        """
        self.transcript_text.clear_all_text()
        self.global_vars.transcriber.clear_transcriber_context(self.global_vars.audio_queue)

    def create_ui_components(self, config: dict):
        """Create all UI components."""
        self.view_builder.build(self, config)
        self.command_binder.bind(self, config)

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
        """Create and bind window menus for the application."""
        self.view_builder.create_menus(self)
        self.command_binder.bind_menus(self)

    def set_audio_device_menus(self, config):
        self.controller.set_audio_device_menus()

    def copy_to_clipboard(self):
        """Copy transcription text data to clipboard."""
        return self.controller.copy_to_clipboard()

    def save_file(self):
        """Save transcription text data to file."""
        return self.controller.save_file()

    def freeze_unfreeze(self):
        """Respond to start / stop of seeking responses from the LLM."""
        return self.controller.freeze_unfreeze()

    def enable_disable_speaker(self):
        """Toggle the state of speaker input."""
        return self.controller.enable_disable_speaker()

    def enable_disable_microphone(self):
        """Toggle the state of microphone input."""
        return self.controller.enable_disable_microphone()

    def update_interval_slider_value(self, slider_value):
        """Update the LLM response interval."""
        return self.controller.update_interval_slider_value(slider_value)

    def get_response_now(self):
        """Get an LLM response immediately."""
        return self.controller.get_response_now()

    def get_response_selected_now_threaded(self, text: str):
        """Update response UI in a separate thread."""
        return self.controller.get_response_selected_now_threaded(text)

    def get_response_now_threaded(self):
        """Update response UI in a separate thread."""
        return self.controller.get_response_now_threaded()

    def update_response_ui_threaded(self, response_generator):
        """Helper method to update response UI in a separate thread."""
        return self.controller.update_response_ui_threaded(response_generator)

    def get_response_selected_now(self):
        """Get an LLM response for the current transcript selection."""
        return self.controller.get_response_selected_now()

    def summarize_threaded(self):
        """Get summary from LLM in a separate thread."""
        return self.controller.summarize_threaded()

    def word_cloud_threaded(self):
        """Generate a word cloud in a separate thread."""
        return self.controller.word_cloud_threaded()

    def summarize(self):
        """Get summary response from LLM."""
        return self.controller.summarize()

    def word_cloud(self):
        """Start the word cloud thread."""
        return self.controller.word_cloud()

    def update_response_ui_and_read_now(self):
        """Get a response, update the UI, and read it aloud."""
        return self.controller.update_response_ui_and_read_now()

    def set_transcript_state(self):
        """Enable or disable transcription."""
        return self.controller.set_transcript_state()

    def open_link(self, url: str):
        """Open the link in a web browser."""
        return self.controller.open_link(url)

    def open_github(self):
        """Link to git repo main page."""
        return self.controller.open_github()

    def open_support(self):
        """Link to git repo issues page."""
        return self.controller.open_support()

    def capture_action(self, action_text: str):
        """Write a UI action to the session log."""
        return self.controller.capture_action(action_text)

    def set_audio_language(self, lang: str):
        """Alter audio language in memory and persist it in config file."""
        return self.controller.set_audio_language(lang)

    def set_response_language(self, lang: str):
        """Alter response language in memory and persist it in config file."""
        return self.controller.set_response_language(lang)


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


def update_transcript_ui(transcriber: AudioTranscriber, textbox: SelectableText, runtime: AppRuntime):
    """Update the text of transcription textbox with the given text
        Args:
          transcriber: AudioTranscriber Object
          textbox: SelectableText to be updated
    """
    global last_transcript_ui_update_time  # pylint: disable=W0603

    # None comparison is for initialization
    if last_transcript_ui_update_time is None or last_transcript_ui_update_time < runtime.convo.last_update:
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
                       update_interval_slider: ctk.CTkSlider,
                       runtime: AppRuntime):
    """Update the text of response textbox with the given text
        Args:
          textbox: textbox to be updated
          text: updated text
    """
    response = None

    if runtime.responder.enabled or runtime.update_response_now:
        response = responder.response

    if runtime.previous_response is not None:
        # User selection of previous response takes precedence over
        # Automated ping of LLM Response
        response = runtime.previous_response

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
                  update_interval_slider_label, update_interval_slider, runtime)
