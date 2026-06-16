"""Tests for live transcription reconciliation."""

import unittest

from app.transcribe.live_transcription import LiveTranscriptManager
from sdk.transcription_result import TranscriptSegment, TranscriptionHypothesis


def hypothesis(text, segments=None, start=0.0, end=10.0):
    return TranscriptionHypothesis(
        provider="test",
        text=text,
        segments=segments or [],
        audio_start_seconds=start,
        audio_end_seconds=end,
    )


class TestLiveTranscriptManager(unittest.TestCase):
    def setUp(self):
        self.manager = LiveTranscriptManager(
            {
                "General": {
                    "live_transcription_mutable_tail_seconds": 5,
                    "live_transcription_stability_passes": 2,
                }
            }
        )

    def test_overlapping_windows_do_not_duplicate_text(self):
        first = self.manager.process_hypothesis(
            "You",
            hypothesis("hello world"),
            new_phrase=True,
        )
        second = self.manager.process_hypothesis(
            "You",
            hypothesis("world again"),
            new_phrase=False,
        )

        self.assertEqual(first.text, "hello world")
        self.assertFalse(first.update_previous)
        self.assertEqual(second.text, "hello world again")
        self.assertTrue(second.update_previous)

    def test_rolling_window_replaces_overlapping_region_with_minor_wording_changes(self):
        self.manager.process_hypothesis(
            "Speaker",
            hypothesis(
                "Which is a little bit annoying, but I'm gonna try to do a brutal cana rush anyway "
                "So normally what you do against Zerg is that you just kind of expand anyway"
            ),
            new_phrase=True,
        )

        update = self.manager.process_hypothesis(
            "Speaker",
            hypothesis(
                "Which is a little bit annoying, but I'm gonna try to do a brutal cana-rush anyway "
                "So normally what you do against Zerg is that you just kind of expand anyway, "
                "oh it's actually what never mind"
            ),
            new_phrase=False,
        )

        self.assertEqual(update.text.count("Which is a little bit annoying"), 1)
        self.assertIn("oh it's actually what never mind", update.text)

    def test_repeated_rolling_windows_do_not_grow_duplicate_blocks(self):
        windows = [
            "Which is a little bit annoying, but I'm gonna try to do a brutal cana rush anyway "
            "So normally what you do against Zerg is that you just kind of expand anyway",
            "Which is a little bit annoying, but I'm gonna try to do a brutal cana-rush anyway "
            "So normally what you do against Zerg is that you just kind of expand anyway, oh it's actually",
            "Which is a little bit annoying, but I'm gonna try to do a brutal canaverse anyway "
            "So normally what you do against Zerg is that you just kind of expand anyway, oh it's actually "
            "what never mind",
        ]

        update = None
        for index, text in enumerate(windows):
            update = self.manager.process_hypothesis(
                "Speaker",
                hypothesis(text),
                new_phrase=index == 0,
            )

        self.assertIsNotNone(update)
        self.assertEqual(update.text.count("Which is a little bit annoying"), 1)
        self.assertEqual(update.text.count("So normally what you do against Zerg"), 1)

    def test_repeated_sentence_hallucination_is_collapsed(self):
        update = self.manager.process_hypothesis(
            "Speaker",
            hypothesis(
                "I'm just a little bit more careful. "
                "I'm just a little bit more careful. "
                "I'm just a little bit more careful. "
                "I'm not going to let you go. "
                "I'm not going to let you go. "
                "I'm not going to let you go."
            ),
            new_phrase=True,
        )

        self.assertEqual(update.text.count("I'm just a little bit more careful."), 1)
        self.assertEqual(update.text.count("I'm not going to let you go."), 1)

    def test_repeated_token_phrase_hallucination_is_collapsed(self):
        update = self.manager.process_hypothesis(
            "You",
            hypothesis(
                "I'm going to get a little bit of a little bit of a little bit of "
                "a little bit of rest."
            ),
            new_phrase=True,
        )

        self.assertEqual(update.text, "I'm going to get a little bit of rest.")

    def test_mutable_tail_correction_updates_current_text(self):
        self.manager.process_hypothesis(
            "You",
            hypothesis("hello wrld"),
            new_phrase=True,
        )
        update = self.manager.process_hypothesis(
            "You",
            hypothesis("hello world"),
            new_phrase=False,
        )

        self.assertEqual(update.text, "hello world")
        self.assertTrue(update.update_previous)

    def test_finalized_text_is_not_rewritten_outside_mutable_tail(self):
        self.manager.process_hypothesis(
            "You",
            hypothesis(
                "first sentence second thought",
                segments=[
                    TranscriptSegment(0, 0.0, 3.0, "first sentence"),
                    TranscriptSegment(1, 6.0, 9.0, "second thought"),
                ],
                end=10.0,
            ),
            new_phrase=True,
        )
        update = self.manager.process_hypothesis(
            "You",
            hypothesis("changed sentence second thought", start=5.0, end=12.0),
            new_phrase=False,
        )

        self.assertTrue(update.text.startswith("first sentence"))
        self.assertNotIn("changed sentence changed sentence", update.text)

    def test_new_phrase_creates_new_conversation_row(self):
        self.manager.process_hypothesis(
            "Speaker",
            hypothesis("old phrase"),
            new_phrase=True,
        )
        update = self.manager.process_hypothesis(
            "Speaker",
            hypothesis("new phrase"),
            new_phrase=True,
        )

        self.assertEqual(update.text, "new phrase")
        self.assertFalse(update.update_previous)

    def test_speakers_have_independent_state(self):
        self.manager.process_hypothesis("You", hypothesis("hello world"), new_phrase=True)
        self.manager.process_hypothesis("Speaker", hypothesis("different start"), new_phrase=True)

        you_update = self.manager.process_hypothesis("You", hypothesis("world again"), new_phrase=False)
        speaker_update = self.manager.process_hypothesis("Speaker", hypothesis("start here"), new_phrase=False)

        self.assertEqual(you_update.text, "hello world again")
        self.assertEqual(speaker_update.text, "different start here")

    def test_clear_resets_all_state(self):
        self.manager.process_hypothesis("You", hypothesis("hello world"), new_phrase=True)
        self.manager.clear()

        update = self.manager.process_hypothesis("You", hypothesis("fresh"), new_phrase=False)

        self.assertEqual(update.text, "fresh")
        self.assertTrue(update.update_previous)


if __name__ == "__main__":
    unittest.main()
