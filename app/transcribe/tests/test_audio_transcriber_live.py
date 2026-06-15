"""Tests for live transcription behavior inside AudioTranscriber."""

import datetime
import unittest

from app.transcribe.audio_transcriber import WhisperTranscriber


class FakeSource:
    SAMPLE_RATE = 10
    SAMPLE_WIDTH = 2
    channels = 1


class FakeConversation:
    def __init__(self):
        self.updates = []
        self.cleared = False

    def update_conversation(self, persona, time_spoken, text, update_previous=False):
        self.updates.append(
            {
                "persona": persona,
                "time_spoken": time_spoken,
                "text": text,
                "update_previous": update_previous,
            }
        )

    def clear_conversation_data(self):
        self.cleared = True


class TestAudioTranscriberLiveBehavior(unittest.TestCase):
    def setUp(self):
        self.conversation = FakeConversation()
        self.transcriber = WhisperTranscriber(
            FakeSource(),
            FakeSource(),
            model=object(),
            convo=self.conversation,
            config={
                "General": {
                    "clear_transcript_periodically": False,
                    "clear_transcript_interval_seconds": 90,
                    "live_transcription_window_seconds": 0.1,
                    "live_transcription_audio_context_seconds": 1,
                    "live_transcription_mutable_tail_seconds": 5,
                    "live_transcription_stability_passes": 2,
                }
            },
        )

    def test_audio_buffer_is_trimmed_by_configured_window(self):
        source_info = self.transcriber.audio_sources_properties["You"]
        source_info["last_sample"] = b"0123456789"

        with source_info["mutex"]:
            self.transcriber._trim_audio_buffer_locked(source_info)

        self.assertEqual(source_info["last_sample"], b"89")
        self.assertEqual(source_info["buffer_start_seconds"], 0.4)

    def test_update_transcript_can_force_insert_or_update(self):
        now = datetime.datetime.utcnow()

        self.transcriber.update_transcript("You", "first", now, update_previous=False)
        self.transcriber.update_transcript("You", "first corrected", now, update_previous=True)

        self.assertFalse(self.conversation.updates[0]["update_previous"])
        self.assertTrue(self.conversation.updates[1]["update_previous"])

    def test_clear_transcript_data_resets_live_state_and_audio_window(self):
        self.transcriber.audio_sources_properties["You"]["last_sample"] = b"1234"
        self.transcriber.audio_sources_properties["You"]["buffer_start_seconds"] = 2.0
        self.transcriber.live_transcript_manager.process_hypothesis(
            "You",
            _hypothesis("hello"),
            new_phrase=True,
        )

        self.transcriber.clear_transcript_data()

        self.assertEqual(self.transcriber.audio_sources_properties["You"]["last_sample"], b"")
        self.assertEqual(self.transcriber.audio_sources_properties["You"]["buffer_start_seconds"], 0.0)
        self.assertTrue(self.conversation.cleared)


def _hypothesis(text):
    from sdk.transcription_result import TranscriptionHypothesis

    return TranscriptionHypothesis(provider="test", text=text)


if __name__ == "__main__":
    unittest.main()
