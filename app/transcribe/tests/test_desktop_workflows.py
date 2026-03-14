"""Unit tests for desktop workflow helpers."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.transcribe.desktop.workflows import DesktopWorkflowService, SUMMARY_FAILURE_MESSAGE


class ImmediateThread:
    """Thread double that runs targets synchronously on start."""

    created = []

    def __init__(self, target, name, args):
        self.target = target
        self.name = name
        self.args = args
        self.daemon = False
        self.started = False
        self.__class__.created.append(self)

    def start(self):
        self.started = True
        self.target(*self.args)


class TestDesktopWorkflowService(unittest.TestCase):
    def setUp(self):
        ImmediateThread.created = []
        self.speech_event = MagicMock()
        self.global_vars = SimpleNamespace(
            update_response_now=False,
            read_response=False,
            audio_player_var=SimpleNamespace(speech_text_available=self.speech_event),
        )
        self.insights_service = MagicMock()
        self.service = DesktopWorkflowService(
            runtime=self.global_vars,
            insights_service=self.insights_service,
            thread_factory=ImmediateThread,
        )

    def test_start_response_workflow_runs_and_resets_state(self):
        responses = []
        self.global_vars.read_response = True

        started = self.service.start_response_workflow(
            response_generator=lambda: "hello",
            on_response=responses.append,
            thread_name="GetResponseNow",
        )

        self.assertTrue(started)
        self.assertEqual(responses, ["hello"])
        self.assertFalse(self.global_vars.update_response_now)
        self.speech_event.set.assert_called_once_with()
        self.assertEqual(ImmediateThread.created[0].name, "GetResponseNow")
        self.assertTrue(ImmediateThread.created[0].daemon)
        self.assertTrue(ImmediateThread.created[0].started)

    def test_start_response_workflow_skips_when_busy(self):
        self.global_vars.update_response_now = True

        started = self.service.start_response_workflow(
            response_generator=lambda: "hello",
            on_response=lambda value: value,
            thread_name="GetResponseNow",
        )

        self.assertFalse(started)
        self.assertEqual(ImmediateThread.created, [])

    def test_run_summary_workflow_emits_loading_close_and_message(self):
        events = []

        self.service.run_summary_workflow(
            summarize_fn=lambda: "summary text",
            on_loading=lambda title, message: events.append(("loading", title, message)),
            on_close=lambda: events.append(("close",)),
            on_message=lambda title, message: events.append(("message", title, message)),
        )

        self.assertEqual(
            events,
            [
                ("loading", "Summary", "Creating a summary"),
                ("close",),
                ("message", "Summary", "summary text"),
            ],
        )

    def test_run_summary_workflow_emits_failure_message_when_summary_is_missing(self):
        events = []

        self.service.run_summary_workflow(
            summarize_fn=lambda: None,
            on_loading=lambda title, message: events.append(("loading", title, message)),
            on_close=lambda: events.append(("close",)),
            on_message=lambda title, message: events.append(("message", title, message)),
        )

        self.assertEqual(events[-1], ("message", "Summary", SUMMARY_FAILURE_MESSAGE))

    def test_run_word_cloud_workflow_builds_word_cloud_and_emits_popup(self):
        events = []
        self.insights_service.build_word_cloud.return_value = "word-cloud"

        self.service.run_word_cloud_workflow(
            words_provider=lambda: "conversation text",
            on_close=lambda: events.append(("close",)),
            on_word_cloud=lambda title, word_cloud: events.append(("cloud", title, word_cloud)),
        )

        self.insights_service.build_word_cloud.assert_called_once_with("conversation text")
        self.assertEqual(events, [("close",), ("cloud", "Word Cloud", "word-cloud")])


if __name__ == "__main__":
    unittest.main()
