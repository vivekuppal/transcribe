"""Unit tests for core conversation formatting helpers."""

import datetime
import threading
import unittest

from app.transcribe import constants
from app.transcribe.core.conversation import Conversation


class TestConversationDisplayFormatting(unittest.TestCase):
    def setUp(self):
        self.conversation = Conversation.__new__(Conversation)
        self.conversation.transcript_data = {
            constants.PERSONA_SYSTEM: [],
            constants.PERSONA_YOU: [],
            constants.PERSONA_SPEAKER: [],
            constants.PERSONA_ASSISTANT: [],
        }
        self.conversation._lock = threading.RLock()

    def test_get_display_conversation_adds_timestamps(self):
        spoken_time = datetime.datetime(2026, 6, 16, 14, 5, 6)
        self.conversation.transcript_data[constants.PERSONA_YOU].append(
            ("You: [hello there]\n\n", spoken_time, 12)
        )
        expected_time = spoken_time.replace(tzinfo=datetime.timezone.utc).astimezone().strftime("%H:%M:%S")

        transcript = self.conversation.get_display_conversation(sources=[constants.PERSONA_YOU])

        self.assertEqual(transcript, f"You: [{expected_time}] [hello there]\n\n")

    def test_get_conversation_keeps_raw_text_without_timestamps(self):
        spoken_time = datetime.datetime(2026, 6, 16, 14, 5, 6)
        self.conversation.transcript_data[constants.PERSONA_SPEAKER].append(
            ("Speaker: [raw transcript]\n\n", spoken_time, 13)
        )

        transcript = self.conversation.get_conversation(sources=[constants.PERSONA_SPEAKER])

        self.assertEqual(transcript, "Speaker: [raw transcript]\n\n")

    def test_get_conversation_includes_diarized_source_personas(self):
        spoken_time = datetime.datetime(2026, 6, 16, 14, 5, 6)
        self.conversation.transcript_data["Speaker 1"] = [
            ("Speaker 1: [first speaker]\n\n", spoken_time, 13)
        ]
        self.conversation.transcript_data["Speaker 2"] = [
            ("Speaker 2: [second speaker]\n\n", spoken_time + datetime.timedelta(seconds=1), 14)
        ]

        transcript = self.conversation.get_conversation(sources=[constants.PERSONA_SPEAKER])

        self.assertEqual(
            transcript,
            "Speaker 1: [first speaker]\n\nSpeaker 2: [second speaker]\n\n",
        )

    def test_display_text_to_conversation_text_removes_timestamp(self):
        normalized = Conversation._display_text_to_conversation_text(
            "Speaker: [14:05:06] [timestamped transcript]"
        )

        self.assertEqual(normalized, "Speaker: [timestamped transcript]")

    def test_display_text_to_conversation_text_keeps_bracketed_transcript_text(self):
        normalized = Conversation._display_text_to_conversation_text(
            "Speaker: [not time] [actual words]"
        )

        self.assertEqual(normalized, "Speaker: [not time] [actual words]")


if __name__ == "__main__":
    unittest.main()
