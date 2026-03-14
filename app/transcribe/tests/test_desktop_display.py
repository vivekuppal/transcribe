"""Unit tests for desktop display helpers."""

import datetime
import unittest
from types import SimpleNamespace

from app.transcribe.desktop.display import DesktopDisplayManager


class FakeTranscriptText:
    """Transcript widget double for display manager tests."""

    def __init__(self):
        self.calls = []
        self.text_widget = None

    def delete_row_starting_with(self, start_text):
        self.calls.append(("delete_row_starting_with", start_text))

    def replace_multiple_newlines(self):
        self.calls.append(("replace_multiple_newlines",))

    def add_text_to_bottom(self, text):
        self.calls.append(("add_text_to_bottom", text))

    def scroll_to_bottom(self):
        self.calls.append(("scroll_to_bottom",))


class FakeTextbox:
    """Textbox double that records text operations."""

    def __init__(self):
        self.configure_calls = []
        self.insert_calls = []
        self.delete_calls = []
        self.see_calls = []
        self.after_calls = []
        self.text = ""

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def tag_ranges(self, tag_name):
        return ()

    def delete(self, start, end):
        self.delete_calls.append((start, end))
        self.text = ""

    def insert(self, start, text):
        self.insert_calls.append((start, text))
        self.text = text

    def see(self, where):
        self.see_calls.append(where)

    def after(self, delay, callback, *args):
        self.after_calls.append((delay, callback, args))


class TestDesktopDisplayManager(unittest.TestCase):
    def setUp(self):
        self.manager = DesktopDisplayManager(ui_font_size=20)
        self.transcript_text = FakeTranscriptText()
        self.response_textbox = FakeTextbox()
        self.interval_label = FakeTextbox()
        self.interval_slider = SimpleNamespace(get=lambda: 5)
        self.ui = SimpleNamespace(
            transcript_text=self.transcript_text,
            response_textbox=self.response_textbox,
            update_interval_slider_label=self.interval_label,
            update_interval_slider=self.interval_slider,
            enqueue_ui_action=lambda callback, *args: self.enqueued.append((callback, args)),
        )
        self.enqueued = []
        self.manager.bind_ui(self.ui)

    def test_update_last_row_rewrites_transcript_tail(self):
        self.manager.update_last_row("Speaker", "Speaker: [updated]")

        self.assertEqual(
            self.transcript_text.calls,
            [
                ("delete_row_starting_with", "Speaker"),
                ("replace_multiple_newlines",),
                ("add_text_to_bottom", "\n"),
                ("add_text_to_bottom", "Speaker: [updated]"),
                ("scroll_to_bottom",),
            ],
        )

    def test_write_response_text_updates_textbox_state(self):
        self.manager.write_response_text("response text")

        self.assertEqual(
            self.response_textbox.configure_calls,
            [{"state": "normal"}, {"state": "disabled"}],
        )
        self.assertEqual(self.response_textbox.insert_calls[-1], ("0.0", "response text"))
        self.assertEqual(self.response_textbox.see_calls, ["end"])

    def test_update_transcript_ui_only_runs_when_conversation_changed(self):
        runtime = SimpleNamespace(convo=SimpleNamespace(last_update=datetime.datetime(2026, 1, 1, 12, 0, 0)))
        transcriber = SimpleNamespace(get_transcript=lambda: "line one")

        self.manager.update_transcript_ui(transcriber, self.transcript_text, runtime)
        self.manager.update_transcript_ui(transcriber, self.transcript_text, runtime)

        add_calls = [call for call in self.transcript_text.calls if call[0] == "add_text_to_bottom"]
        self.assertEqual(add_calls, [("add_text_to_bottom", "line one")])

    def test_update_response_ui_writes_response_and_reschedules(self):
        responder = SimpleNamespace(response="assistant response", update_response_interval=lambda value: value)
        runtime = SimpleNamespace(responder=SimpleNamespace(enabled=True), update_response_now=False, previous_response=None)

        self.manager.update_response_ui(
            responder,
            self.response_textbox,
            self.interval_label,
            self.interval_slider,
            runtime,
        )

        self.assertEqual(self.response_textbox.insert_calls[-1], ("0.0", "assistant response"))
        self.assertEqual(self.response_textbox.after_calls[0][0], 300)


if __name__ == "__main__":
    unittest.main()
