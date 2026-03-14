import datetime
import queue
import tkinter as tk
import customtkinter as ctk

try:
    from .desktop import DesktopCommandBinder, DesktopController, DesktopDisplayManager, DesktopViewBuilder
    from .global_vars import AppRuntime, create_app_runtime
except ImportError:
    from desktop import DesktopCommandBinder, DesktopController, DesktopDisplayManager, DesktopViewBuilder
    from global_vars import AppRuntime, create_app_runtime
from tsutils import app_logging as al


logger = al.get_module_logger(al.UI_LOGGER)
UI_FONT_SIZE = 20
UI_POLL_INTERVAL_MS = 50


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
        display_manager: DesktopDisplayManager = None,
    ):
        super().__init__()
        self.global_vars = runtime or create_app_runtime()
        self.controller = controller or DesktopController(config=config, runtime=self.global_vars)
        self.view_builder = view_builder or DesktopViewBuilder()
        self.command_binder = command_binder or DesktopCommandBinder()
        self.display_manager = display_manager or DesktopDisplayManager(ui_font_size=self.ui_font_size)
        self._ui_action_queue: queue.Queue = queue.Queue()

        self.global_vars.main_window = self
        self.controller.bind_ui(self)
        self.display_manager.bind_ui(self)
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
        """Replace the latest transcript row for a speaker."""
        return self.display_manager.update_last_row(speaker, input_text)

    def queue_update_last_row(self, speaker: str, input_text: str):
        """Schedule transcript row replacement on the UI thread."""
        return self.display_manager.queue_update_last_row(speaker, input_text)

    def queue_add_transcript_line(self, input_text: str):
        """Schedule transcript insertion on the UI thread."""
        return self.display_manager.queue_add_transcript_line(input_text)

    def write_response_text(self, response_string: str):
        """Render a response string into the response textbox."""
        return self.display_manager.write_response_text(response_string)

    def close_popup(self):
        """Close the currently active popup, if one exists."""
        return self.display_manager.close_popup()

    def show_loading_popup(self, title: str, msg: str):
        """Create a temporary status popup on the UI thread."""
        return self.display_manager.show_loading_popup(title, msg)

    def show_message_popup(self, title: str, msg: str):
        """Create a popup with a message and close button."""
        return self.display_manager.show_message_popup(title, msg)

    def show_word_cloud_popup(self, title: str, word_cloud):
        """Create a word cloud popup on the UI thread."""
        return self.display_manager.show_word_cloud_popup(title, word_cloud)

    def update_initial_transcripts(self):
        """Set initial transcript in UI.
        """
        return self.display_manager.update_initial_transcripts(self.global_vars)

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
            return self.display_manager.edit_current_line(self.global_vars)
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
