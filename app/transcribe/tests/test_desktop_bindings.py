"""Unit tests for desktop command binding helpers."""

import unittest
from types import SimpleNamespace

from app.transcribe.desktop.bindings import DesktopCommandBinder


class FakeButton:
    """Simple button double that records configuration updates."""

    def __init__(self):
        self.calls = []

    def configure(self, **kwargs):
        self.calls.append(kwargs)


class TestDesktopCommandBinder(unittest.TestCase):
    def test_get_provider_settings_for_openai(self):
        binder = DesktopCommandBinder()
        config = {
            "General": {"chat_inference_provider": "openai"},
            "OpenAI": {"api_key": "key", "base_url": "https://api.example.com", "ai_model": "gpt"},
            "Together": {},
        }

        provider_settings = binder.get_provider_settings(config)

        self.assertEqual(provider_settings, ("key", "https://api.example.com", "gpt"))

    def test_get_provider_settings_for_unknown_provider(self):
        binder = DesktopCommandBinder()
        config = {
            "General": {"chat_inference_provider": "custom"},
            "OpenAI": {},
            "Together": {},
        }

        provider_settings = binder.get_provider_settings(config)

        self.assertIsNone(provider_settings)

    def test_apply_backend_availability_disables_backend_buttons(self):
        tooltip_calls = []
        binder = DesktopCommandBinder(
            api_key_validator=lambda api_key, base_url, model: False,
            tooltip_factory=lambda *args, **kwargs: tooltip_calls.append((args, kwargs)),
        )
        ui = SimpleNamespace(
            continuous_response_button=FakeButton(),
            response_now_button=FakeButton(),
            read_response_now_button=FakeButton(),
            summarize_button=FakeButton(),
        )
        config = {
            "General": {"chat_inference_provider": "openai"},
            "OpenAI": {"api_key": "", "base_url": "https://api.example.com", "ai_model": "gpt"},
            "Together": {},
        }

        binder.apply_backend_availability(ui, config)

        self.assertEqual(ui.continuous_response_button.calls[-1], {"state": "disabled"})
        self.assertEqual(ui.response_now_button.calls[-1], {"state": "disabled"})
        self.assertEqual(ui.read_response_now_button.calls[-1], {"state": "disabled"})
        self.assertEqual(ui.summarize_button.calls[-1], {"state": "disabled"})
        self.assertEqual(len(tooltip_calls), 4)
        self.assertEqual(tooltip_calls[0][1]["font"], ("Arial", 12))


if __name__ == "__main__":
    unittest.main()
