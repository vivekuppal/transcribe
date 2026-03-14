"""Unit tests for desktop service helpers."""

import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.transcribe.desktop.services import (
    ActionLogService,
    BrowserService,
    ConversationInsightsService,
    SettingsService,
    TranscriptIOService,
)


class FakeConfig:
    """Simple config double used for settings tests."""

    def __init__(self, data):
        self.data = data
        self.override_values = []

    def add_override_value(self, value):
        self.override_values.append(value)
        for section, section_values in value.items():
            self.data.setdefault(section, {}).update(section_values)


class FakeWordCloud:
    """Capture text passed to generate without depending on rendering."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.generated_text = None

    def generate(self, text):
        self.generated_text = text
        return self


class TestActionLogService(unittest.TestCase):
    def test_capture_reuses_log_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "ui-1.txt"
            now_values = iter(
                [
                    datetime.datetime(2026, 1, 1, 8, 0, 0),
                    datetime.datetime(2026, 1, 1, 8, 0, 1),
                ]
            )

            service = ActionLogService(
                get_data_path=lambda app_name: temp_dir,
                incrementing_filename=lambda filename, extension: str(log_file),
                now_provider=lambda: next(now_values),
            )

            service.capture("First action")
            service.capture("Second action")

            self.assertEqual(service.log_filename, str(log_file))
            self.assertEqual(
                log_file.read_text(encoding="utf-8"),
                "2026-01-01 08:00:00: First action\n2026-01-01 08:00:01: Second action\n",
            )


class TestSettingsService(unittest.TestCase):
    def test_save_llm_response_interval_persists_integer_value(self):
        fake_config = FakeConfig(data={"General": {}, "OpenAI": {}})
        service = SettingsService(config_factory=lambda: fake_config)

        interval = service.save_llm_response_interval("7")

        self.assertEqual(interval, 7)
        self.assertEqual(fake_config.override_values, [{"General": {"llm_response_interval": 7}}])

    def test_save_audio_language_updates_model_and_config(self):
        fake_config = FakeConfig(data={"General": {}, "OpenAI": {}})
        stt_model = MagicMock()
        service = SettingsService(config_factory=lambda: fake_config)

        service.save_audio_language("french", stt_model)

        stt_model.set_lang.assert_called_once_with("french")
        self.assertEqual(fake_config.override_values, [{"OpenAI": {"audio_lang": "french"}}])

    def test_save_response_language_updates_system_prompt(self):
        fake_config = FakeConfig(
            data={
                "General": {"system_prompt": "You are helpful"},
                "OpenAI": {"response_lang": None},
            }
        )
        convo = MagicMock()
        current_time = datetime.datetime(2026, 3, 14, 10, 30, 0)
        service = SettingsService(
            config_factory=lambda: fake_config,
            utcnow_provider=lambda: current_time,
        )

        service.save_response_language("spanish", convo)

        self.assertEqual(fake_config.override_values, [{"OpenAI": {"response_lang": "spanish"}}])
        convo.update_conversation.assert_called_once_with(
            persona="system",
            text="You are helpful.  Respond exclusively in spanish.",
            time_spoken=current_time,
            update_previous=True,
        )


class TestTranscriptIOService(unittest.TestCase):
    def test_copy_transcript_uses_clipboard(self):
        copied = []
        service = TranscriptIOService(clipboard_copy=copied.append)

        service.copy_transcript("hello world")

        self.assertEqual(copied, ["hello world"])

    def test_save_transcript_writes_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "transcript.txt"
            service = TranscriptIOService()

            service.save_transcript("saved text", str(output_file))

            self.assertEqual(output_file.read_text(encoding="utf-8"), "saved text")


class TestBrowserService(unittest.TestCase):
    def test_open_link_uses_browser_with_new_window(self):
        browser_open = MagicMock()
        service = BrowserService(browser_open=browser_open)

        service.open_link("https://example.com")

        browser_open.assert_called_once_with(url="https://example.com", new=2)


class TestConversationInsightsService(unittest.TestCase):
    def test_normalize_word_cloud_text_removes_persona_prefixes(self):
        service = ConversationInsightsService(word_cloud_factory=FakeWordCloud)

        normalized = service.normalize_word_cloud_text("You: hi\nSpeaker: hello\nassistant: ok")

        self.assertEqual(normalized, "hi\nhello\nok")

    def test_build_word_cloud_uses_normalized_text_tail(self):
        service = ConversationInsightsService(word_cloud_factory=FakeWordCloud)
        words = "You: " + ("a" * 90)

        word_cloud = service.build_word_cloud(words)

        self.assertEqual(word_cloud.generated_text, "a" * 10)
        self.assertEqual(word_cloud.kwargs["background_color"], "white")


if __name__ == "__main__":
    unittest.main()
