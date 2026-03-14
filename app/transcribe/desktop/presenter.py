"""Desktop UI presentation helpers for widget-facing updates."""

from __future__ import annotations


class DesktopPresenter:
    """Encapsulate widget-specific desktop UI updates."""

    FILEMENU_TRANSCRIPTION_INDEX = 1
    EDITMENU_SPEAKER_INDEX = 2
    EDITMENU_MICROPHONE_INDEX = 3

    def __init__(self):
        self.ui = None

    def bind_ui(self, ui):
        """Attach the presenter to the active UI instance."""
        self.ui = ui

    def get_selected_transcript_text(self) -> str:
        """Return the selected transcript text from the UI."""
        return self.ui.transcript_text.selection_get()

    def set_continuous_response_enabled(self, enabled: bool):
        """Update the continuous-response button label."""
        self.ui.continuous_response_button.configure(
            text=(
                "Do Not Suggest Responses Continuously"
                if enabled
                else "Suggest Responses Continuously"
            )
        )

    def set_speaker_enabled(self, enabled: bool):
        """Update the speaker menu label."""
        self.ui.editmenu.entryconfigure(
            self.EDITMENU_SPEAKER_INDEX,
            label="Disable Speaker" if enabled else "Enable Speaker",
        )

    def set_microphone_enabled(self, enabled: bool):
        """Update the microphone menu label."""
        self.ui.editmenu.entryconfigure(
            self.EDITMENU_MICROPHONE_INDEX,
            label="Disable Microphone" if enabled else "Enable Microphone",
        )

    def set_transcription_enabled(self, enabled: bool):
        """Update the transcription menu label."""
        self.ui.filemenu.entryconfigure(
            self.FILEMENU_TRANSCRIPTION_INDEX,
            label="Pause Transcription" if enabled else "Start Transcription",
        )

    def set_response_interval(self, interval: int):
        """Update the response-interval label."""
        self.ui.update_interval_slider_label.configure(
            text=f"LLM Response interval: {interval} seconds"
        )

    def queue_response_text(self, response_string: str):
        """Queue response text rendering on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.write_response_text, response_string)

    def queue_loading_popup(self, title: str, message: str):
        """Queue a loading popup on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.show_loading_popup, title, message)

    def queue_close_popup(self):
        """Queue popup closure on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.close_popup)

    def queue_message_popup(self, title: str, message: str):
        """Queue a text popup on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.show_message_popup, title, message)

    def queue_word_cloud_popup(self, title: str, word_cloud):
        """Queue a word-cloud popup on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.show_word_cloud_popup, title, word_cloud)
