"""Desktop controller for the Windows application UI."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

try:
    from .. import constants
    from ..core.state import TranscriptionGlobals
    from .services import (
        ActionLogService,
        BrowserService,
        ConversationInsightsService,
        SettingsService,
        TranscriptIOService,
    )
except ImportError:
    import constants
    from core.state import TranscriptionGlobals
    from services import (
        ActionLogService,
        BrowserService,
        ConversationInsightsService,
        SettingsService,
        TranscriptIOService,
    )

from tsutils import app_logging as al

if TYPE_CHECKING:
    try:
        from ..appui import AppUI
    except ImportError:
        from appui import AppUI


logger = al.get_module_logger(al.UI_LOGGER)


class DesktopController:
    """Coordinates desktop actions between background services and the UI."""

    def __init__(
        self,
        config: dict,
        global_vars: TranscriptionGlobals,
        action_log_service: ActionLogService = None,
        settings_service: SettingsService = None,
        transcript_io_service: TranscriptIOService = None,
        browser_service: BrowserService = None,
        insights_service: ConversationInsightsService = None,
    ):
        self.config = config
        self.global_vars = global_vars
        self.ui: AppUI | None = None
        self.action_log_service = action_log_service or ActionLogService()
        self.settings_service = settings_service or SettingsService()
        self.transcript_io_service = transcript_io_service or TranscriptIOService()
        self.browser_service = browser_service or BrowserService()
        self.insights_service = insights_service or ConversationInsightsService()

    def bind_ui(self, ui: "AppUI"):
        """Attach the active UI instance to the controller."""
        self.ui = ui

    def set_audio_device_menus(self):
        """Apply configured audio-device startup state to the UI."""
        if self.config["General"]["disable_speaker"]:
            print("[INFO] Disabling Speaker")
            self.enable_disable_speaker()

        if self.config["General"]["disable_mic"]:
            print("[INFO] Disabling Microphone")
            self.enable_disable_microphone()

    def copy_to_clipboard(self):
        """Copy the current transcript to the clipboard."""
        logger.info(f"{self.__class__.__name__}.copy_to_clipboard")
        self.capture_action("Copy transcript to clipboard")
        try:
            self.transcript_io_service.copy_transcript(self.global_vars.transcriber.get_transcript())
        except Exception as exception:
            logger.error(f"Error copying to clipboard: {exception}")

    def save_file(self):
        """Save transcript text to a file."""
        logger.info(f"{self.__class__.__name__}.save_file")
        filename = ctk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            title="Save Transcription",
            filetypes=[("Text Files", "*.txt")],
        )
        self.capture_action(f"Save transcript to file:{filename}")
        if not filename:
            return
        try:
            self.transcript_io_service.save_transcript(
                transcript=self.global_vars.transcriber.get_transcript(),
                filename=filename,
            )
        except Exception as exception:
            logger.error(f"Error saving file {filename}: {exception}")

    def freeze_unfreeze(self):
        """Toggle continuous LLM responses."""
        logger.info(f"{self.__class__.__name__}.freeze_unfreeze")
        try:
            self.global_vars.responder.enabled = not self.global_vars.responder.enabled
            self.capture_action(
                f'{"Enabled " if self.global_vars.responder.enabled else "Disabled "} continuous LLM responses'
            )
            self.ui.continuous_response_button.configure(
                text=(
                    "Suggest Responses Continuously"
                    if not self.global_vars.responder.enabled
                    else "Do Not Suggest Responses Continuously"
                )
            )
        except Exception as exception:
            logger.error(f"Error toggling responder state: {exception}")

    def enable_disable_speaker(self):
        """Toggle speaker capture state."""
        try:
            self.global_vars.speaker_audio_recorder.enabled = not self.global_vars.speaker_audio_recorder.enabled
            label = (
                "Disable Speaker"
                if self.global_vars.speaker_audio_recorder.enabled
                else "Enable Speaker"
            )
            self.ui.editmenu.entryconfigure(2, label=label)
            self.capture_action(
                f'{"Enabled " if self.global_vars.speaker_audio_recorder.enabled else "Disabled "} speaker input'
            )
        except Exception as exception:
            logger.error(f"Error toggling speaker state: {exception}")

    def enable_disable_microphone(self):
        """Toggle microphone capture state."""
        try:
            self.global_vars.user_audio_recorder.enabled = not self.global_vars.user_audio_recorder.enabled
            label = (
                "Disable Microphone"
                if self.global_vars.user_audio_recorder.enabled
                else "Enable Microphone"
            )
            self.ui.editmenu.entryconfigure(3, label=label)
            self.capture_action(
                f'{"Enabled " if self.global_vars.user_audio_recorder.enabled else "Disabled "} microphone input'
            )
        except Exception as exception:
            logger.error(f"Error toggling microphone state: {exception}")

    def update_interval_slider_value(self, slider_value):
        """Persist the LLM response interval and update its label."""
        try:
            interval = self.settings_service.save_llm_response_interval(slider_value)
            label_text = f"LLM Response interval: {interval} seconds"
            self.ui.update_interval_slider_label.configure(text=label_text)
            self.capture_action(f"Update LLM response interval to {interval}")
        except Exception as exception:
            logger.error(f"Error updating slider value: {exception}")

    def get_response_now(self):
        """Generate an LLM response from the current transcript."""
        if self.global_vars.update_response_now:
            return

        self.capture_action("Get LLM response now")
        response_ui_thread = threading.Thread(target=self.get_response_now_threaded, name="GetResponseNow")
        response_ui_thread.daemon = True
        response_ui_thread.start()

    def get_response_selected_now_threaded(self, text: str):
        """Generate an LLM response for the selected transcript text."""
        self.update_response_ui_threaded(
            lambda: self.global_vars.responder.generate_response_for_selected_text(text)
        )

    def get_response_now_threaded(self):
        """Generate an LLM response for the full transcript."""
        self.update_response_ui_threaded(
            self.global_vars.responder.generate_response_from_transcript_no_check
        )

    def update_response_ui_threaded(self, response_generator):
        """Run response generation off the UI thread and marshal updates back."""
        try:
            self.global_vars.update_response_now = True
            response_string = response_generator()
            if self.global_vars.read_response:
                self.global_vars.audio_player_var.speech_text_available.set()
            if response_string:
                self.ui.enqueue_ui_action(self.ui.write_response_text, response_string)
        except Exception as exception:
            logger.error(f"Error in threaded response: {exception}")
        finally:
            self.global_vars.update_response_now = False

    def get_response_selected_now(self):
        """Generate an LLM response for the selected transcript text."""
        if self.global_vars.update_response_now:
            return

        self.capture_action("Get LLM response selected now")
        selected_text = self.ui.transcript_text.selection_get()
        response_ui_thread = threading.Thread(
            target=self.get_response_selected_now_threaded,
            args=(selected_text,),
            name="GetResponseSelectedNow",
        )
        response_ui_thread.daemon = True
        response_ui_thread.start()

    def summarize_threaded(self):
        """Generate a summary off the UI thread."""
        try:
            print("Summarizing...")
            self.ui.enqueue_ui_action(self.ui.show_loading_popup, "Summary", "Creating a summary")
            summary = self.global_vars.responder.summarize()
            self.ui.enqueue_ui_action(self.ui.close_popup)
            if summary is None:
                self.ui.enqueue_ui_action(
                    self.ui.show_message_popup,
                    "Summary",
                    "Failed to get summary. Please check you have a valid API key.",
                )
                return

            self.ui.enqueue_ui_action(self.ui.show_message_popup, "Summary", summary)
        except Exception as exception:
            logger.error(f"Error in summarize_threaded: {exception}")

    def word_cloud_threaded(self):
        """Generate a word cloud off the UI thread."""
        try:
            self.ui.enqueue_ui_action(self.ui.close_popup)
            words = self.global_vars.convo.get_conversation(
                sources=[
                    constants.PERSONA_YOU,
                    constants.PERSONA_SPEAKER,
                    constants.PERSONA_ASSISTANT,
                ],
                length=0,
            )
            word_cloud = self.insights_service.build_word_cloud(words)
            self.ui.enqueue_ui_action(self.ui.show_word_cloud_popup, "Word Cloud", word_cloud)
        except Exception as exception:
            logger.error(f"Error in word_cloud_threaded: {exception}")

    def summarize(self):
        """Start the summary worker thread."""
        self.capture_action("Get summary from LLM")
        summarize_ui_thread = threading.Thread(target=self.summarize_threaded, name="Summarize")
        summarize_ui_thread.daemon = True
        summarize_ui_thread.start()

    def word_cloud(self):
        """Start the word cloud worker thread."""
        self.capture_action("Generate word cloud")
        word_cloud_ui_thread = threading.Thread(target=self.word_cloud_threaded, name="WordCloud")
        word_cloud_ui_thread.daemon = True
        word_cloud_ui_thread.start()

    def update_response_ui_and_read_now(self):
        """Generate a response and signal the audio player to read it aloud."""
        self.capture_action("Get LLM response now and read aloud")
        self.global_vars.set_read_response(True)
        self.get_response_now()

    def set_transcript_state(self):
        """Toggle transcription capture state."""
        logger.info(f"{self.__class__.__name__}.set_transcript_state")
        try:
            self.global_vars.transcriber.transcribe = not self.global_vars.transcriber.transcribe
            self.capture_action(
                f'{"Enabled " if self.global_vars.transcriber.transcribe else "Disabled "} transcription.'
            )
            self.ui.filemenu.entryconfigure(
                1,
                label="Pause Transcription" if self.global_vars.transcriber.transcribe else "Start Transcription",
            )
        except Exception as exception:
            logger.error(f"Error setting transcript state: {exception}")

    def open_link(self, url: str):
        """Open a URL in the default browser."""
        self.capture_action(f"Navigate to {url}.")
        try:
            self.browser_service.open_link(url)
        except Exception as exception:
            logger.error(f"Error opening URL {url}: {exception}")

    def open_github(self):
        """Open the GitHub repository page."""
        self.capture_action("open_github.")
        self.open_link("https://github.com/vivekuppal/transcribe?referer=desktop")

    def open_support(self):
        """Open the issue tracker."""
        self.capture_action("open_support.")
        self.open_link("https://github.com/vivekuppal/transcribe/issues/new?referer=desktop")

    def capture_action(self, action_text: str):
        """Append a UI action to the session log."""
        try:
            self.action_log_service.capture(action_text)
        except Exception as exception:
            logger.error(f"Error capturing action {action_text}: {exception}")

    def set_audio_language(self, lang: str):
        """Persist the STT audio language and update the live model."""
        try:
            self.settings_service.save_audio_language(
                lang=lang,
                stt_model=self.global_vars.transcriber.stt_model,
            )
        except Exception as exception:
            logger.error(f"Error setting audio language: {exception}")

    def set_response_language(self, lang: str):
        """Persist the response language and update the system prompt."""
        try:
            self.settings_service.save_response_language(lang=lang, convo=self.global_vars.convo)
        except Exception as exception:
            logger.error(f"Error setting response language: {exception}")
