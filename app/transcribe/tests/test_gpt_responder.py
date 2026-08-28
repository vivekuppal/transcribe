"""Tests for model-agnostic Chat Completions request construction."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.transcribe.gpt_responder import GPTResponder


class TestGPTResponderRequestSettings(unittest.TestCase):
    def setUp(self):
        self.responder = GPTResponder.__new__(GPTResponder)
        self.responder.model = "provider/new-model-preview"
        self.responder.config = {
            "OpenAI": {
                "response_request_timeout_seconds": 10,
                "temperature": None,
                "reasoning_effort": None,
            },
            "Together": {"temperature": 0.25},
        }

    def test_unset_optional_parameters_are_omitted(self):
        request = self.responder._build_chat_completion_request(
            [{"role": "user", "content": "hello"}], 10
        )

        self.assertEqual(request["model"], "provider/new-model-preview")
        self.assertTrue(request["stream"])
        self.assertNotIn("temperature", request)
        self.assertNotIn("reasoning_effort", request)

    def test_explicit_optional_parameters_are_preserved(self):
        request = self.responder._build_chat_completion_request(
            [], 30, temperature=0.0, reasoning_effort="max"
        )

        self.assertEqual(request["temperature"], 0.0)
        self.assertEqual(request["reasoning_effort"], "max")

    def test_reasoning_effort_is_case_normalized(self):
        self.responder.config["OpenAI"]["reasoning_effort"] = "XHIGH"

        _, _, reasoning_effort = self.responder._get_openai_settings()

        self.assertEqual(reasoning_effort, "xhigh")

    def test_all_documented_reasoning_efforts_are_accepted(self):
        allowed = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
        for value in allowed:
            with self.subTest(value=value):
                self.responder.config["OpenAI"]["reasoning_effort"] = value
                _, _, actual = self.responder._get_openai_settings()
                self.assertEqual(actual, value)

    def test_blank_reasoning_effort_is_treated_as_unset(self):
        self.responder.config["OpenAI"]["reasoning_effort"] = ""

        _, _, reasoning_effort = self.responder._get_openai_settings()

        self.assertIsNone(reasoning_effort)

    def test_malformed_reasoning_effort_fails_closed(self):
        for value in (0, [], "extreme"):
            with self.subTest(value=value):
                self.responder.config["OpenAI"]["reasoning_effort"] = value
                with self.assertRaises(ValueError):
                    self.responder._get_openai_settings()

    def test_compatible_provider_can_override_temperature(self):
        _, temperature, reasoning_effort = (
            self.responder._get_openai_settings("Together")
        )

        self.assertEqual(temperature, 0.25)
        self.assertIsNone(reasoning_effort)

    def test_streaming_request_passes_reasoning_effort(self):
        chunk = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="answer"))]
        )
        create = MagicMock(return_value=[chunk])
        self.responder.llm_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        self.responder._update_conversation = MagicMock()

        result = self.responder._get_llm_response(
            [], temperature=None, timeout=10, reasoning_effort="low"
        )

        self.assertEqual(result, "answer")
        create.assert_called_once_with(
            model="provider/new-model-preview",
            messages=[],
            timeout=10,
            stream=True,
            reasoning_effort="low",
        )


if __name__ == "__main__":
    unittest.main()
