"""Unit tests for desktop presentation helpers."""

import unittest
from types import SimpleNamespace

from app.transcribe.desktop.presenter import DesktopPresenter


class FakeWidget:
    """Simple widget double that records configure and bind calls."""

    def __init__(self):
        self.configure_calls = []
        self.bind_calls = []

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def bind(self, event_name, callback):
        self.bind_calls.append((event_name, callback))


class FakeMenu:
    """Simple menu double that records entry updates."""

    def __init__(self):
        self.entryconfigure_calls = []

    def entryconfigure(self, index, **kwargs):
        self.entryconfigure_calls.append((index, kwargs))


class FakeTranscriptText:
    """Transcript selection double."""

    def __init__(self, selected_text):
        self.selected_text = selected_text

    def selection_get(self):
        return self.selected_text


class TestDesktopPresenter(unittest.TestCase):
    def setUp(self):
        self.presenter = DesktopPresenter()
        self.ui = SimpleNamespace(
            continuous_response_button=FakeWidget(),
            editmenu=FakeMenu(),
            filemenu=FakeMenu(),
            update_interval_slider_label=FakeWidget(),
            transcript_text=FakeTranscriptText("selected transcript"),
            enqueue_ui_action=lambda callback, *args: self.enqueued_actions.append((callback, args)),
            write_response_text=object(),
            show_loading_popup=object(),
            close_popup=object(),
            show_message_popup=object(),
            show_word_cloud_popup=object(),
        )
        self.enqueued_actions = []
        self.presenter.bind_ui(self.ui)

    def test_get_selected_transcript_text_reads_from_ui(self):
        self.assertEqual(self.presenter.get_selected_transcript_text(), "selected transcript")

    def test_set_continuous_response_enabled_updates_button_text(self):
        self.presenter.set_continuous_response_enabled(True)
        self.presenter.set_continuous_response_enabled(False)

        self.assertEqual(
            self.ui.continuous_response_button.configure_calls,
            [
                {"text": "Do Not Suggest Responses Continuously"},
                {"text": "Suggest Responses Continuously"},
            ],
        )

    def test_menu_state_methods_update_expected_indexes(self):
        self.presenter.set_speaker_enabled(True)
        self.presenter.set_microphone_enabled(False)
        self.presenter.set_transcription_enabled(False)

        self.assertEqual(
            self.ui.editmenu.entryconfigure_calls,
            [
                (DesktopPresenter.EDITMENU_SPEAKER_INDEX, {"label": "Disable Speaker"}),
                (DesktopPresenter.EDITMENU_MICROPHONE_INDEX, {"label": "Enable Microphone"}),
            ],
        )
        self.assertEqual(
            self.ui.filemenu.entryconfigure_calls,
            [
                (DesktopPresenter.FILEMENU_TRANSCRIPTION_INDEX, {"label": "Start Transcription"}),
            ],
        )

    def test_queue_methods_enqueue_expected_callbacks(self):
        word_cloud = object()

        self.presenter.queue_response_text("response")
        self.presenter.queue_loading_popup("Summary", "Loading")
        self.presenter.queue_close_popup()
        self.presenter.queue_message_popup("Summary", "Done")
        self.presenter.queue_word_cloud_popup("Word Cloud", word_cloud)

        self.assertEqual(
            self.enqueued_actions,
            [
                (self.ui.write_response_text, ("response",)),
                (self.ui.show_loading_popup, ("Summary", "Loading")),
                (self.ui.close_popup, ()),
                (self.ui.show_message_popup, ("Summary", "Done")),
                (self.ui.show_word_cloud_popup, ("Word Cloud", word_cloud)),
            ],
        )


if __name__ == "__main__":
    unittest.main()
