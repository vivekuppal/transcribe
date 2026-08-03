"""Tests for source isolation and final-only persistence in the streaming adapter."""

import datetime
import queue
import threading
import time
import unittest

from app.transcribe.openai_realtime_transcriber import OpenAIRealtimeTranscriber
from sdk.streaming_transcriber_models import StreamingTranscriptEvent, TranscriptEventKind


class FakeSource:
    def __init__(self, sample_rate, sample_width, channels):
        self.SAMPLE_RATE = sample_rate
        self.SAMPLE_WIDTH = sample_width
        self.channels = channels


class FakeClient:
    instances = {}

    def __init__(self, source_name, source_format, config):
        self.source_name = source_name
        self.source_format = source_format
        self.config = config
        self.audio = []
        self.started = 0
        self.stopped = 0
        self.transcript_callback = None
        self.error_callback = None
        self.__class__.instances[source_name] = self

    def set_transcript_callback(self, callback):
        self.transcript_callback = callback

    def set_error_callback(self, callback):
        self.error_callback = callback

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def append_audio(self, audio, captured_at=None):
        self.audio.append((audio, captured_at))

    def clear_audio(self):
        self.audio.clear()

    def configure_source(self, source_format):
        self.source_format = source_format

    def set_languages(self, languages):
        self.config["languages"] = languages


class FakeConversation:
    def __init__(self):
        self.partials = []
        self.finals = []
        self.cleared = False

    def publish_partial(self, persona, text, update_previous=False, partial_id=None):
        self.partials.append((persona, text, update_previous, partial_id))
        return True

    def update_conversation(self, **kwargs):
        self.finals.append(kwargs)

    def get_conversation(self, sources, length=0):
        del sources, length
        return "".join(f"{item['persona']}: [{item['text']}]\n\n" for item in self.finals)

    def clear_conversation_data(self):
        self.cleared = True
        self.finals.clear()


def wait_for(predicate, timeout=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def transcript_event(kind, source, item_id, text, time_spoken=None):
    return StreamingTranscriptEvent(kind, source, item_id, text, time_spoken)


class TestOpenAIRealtimeTranscriber(unittest.TestCase):
    def setUp(self):
        FakeClient.instances = {}
        self.conversation = FakeConversation()
        self.audio_queue = queue.Queue()
        self.transcriber = OpenAIRealtimeTranscriber(
            FakeSource(16000, 2, 1),
            FakeSource(48000, 2, 2),
            convo=self.conversation,
            config={
                "OpenAI": {"api_key": "test-key", "audio_lang": "English"},
                "OpenAIRealtime": {},
                "General": {
                    "clear_transcript_periodically": False,
                    "clear_transcript_interval_seconds": 90,
                },
            },
            client_factory=FakeClient,
        )
        self.thread = threading.Thread(
            target=self.transcriber.transcribe_audio_queue,
            args=(self.audio_queue,),
            daemon=True,
        )
        self.thread.start()
        self.assertTrue(wait_for(lambda: all(client.started for client in FakeClient.instances.values())))

    def tearDown(self):
        self.transcriber.stop()
        self.thread.join(timeout=1)

    def test_microphone_and_speaker_use_independent_sessions(self):
        self.audio_queue.put(("You", b"mic", None))
        self.audio_queue.put(("Speaker", b"speaker", None))
        self.assertTrue(wait_for(lambda: [item[0] for item in FakeClient.instances["You"].audio] == [b"mic"]))
        self.assertTrue(wait_for(lambda: [item[0] for item in FakeClient.instances["Speaker"].audio] == [b"speaker"]))

        self.assertEqual(FakeClient.instances["You"].source_format["sample_rate"], 16000)
        self.assertEqual(FakeClient.instances["Speaker"].source_format["sample_rate"], 48000)

    def test_partial_is_replaced_and_only_final_is_persisted(self):
        client = FakeClient.instances["You"]
        client.transcript_callback(transcript_event(TranscriptEventKind.PARTIAL, "You", "item-1", "hel"))
        client.transcript_callback(transcript_event(TranscriptEventKind.PARTIAL, "You", "item-1", "hello"))
        final = transcript_event(TranscriptEventKind.COMPLETED, "You", "item-1", "hello world")
        client.transcript_callback(final)
        client.transcript_callback(final)

        self.assertTrue(wait_for(lambda: len(self.conversation.finals) == 1))
        self.assertEqual(
            self.conversation.partials,
            [("You", "hel", False, "You:item-1"), ("You", "hello", True, "You:item-1")],
        )
        self.assertEqual(self.conversation.finals[0]["text"], "hello world")
        self.assertTrue(self.conversation.finals[0]["replace_ui_partial"])
        self.assertEqual(self.transcriber.get_transcript(), "You: [hello world]\n\n")

    def test_source_toggle_stops_only_that_session(self):
        self.transcriber.set_source_enabled("Speaker", False)
        self.audio_queue.put(("You", b"mic", None))
        self.audio_queue.put(("Speaker", b"speaker", None))

        self.assertTrue(wait_for(lambda: [item[0] for item in FakeClient.instances["You"].audio] == [b"mic"]))
        time.sleep(0.05)
        self.assertEqual(FakeClient.instances["Speaker"].audio, [])
        self.assertGreaterEqual(FakeClient.instances["Speaker"].stopped, 1)

    def test_microphone_toggle_routes_only_speaker(self):
        self.transcriber.set_source_enabled("You", False)
        self.audio_queue.put(("You", b"mic", None))
        self.audio_queue.put(("Speaker", b"speaker", None))

        self.assertTrue(wait_for(lambda: [item[0] for item in FakeClient.instances["Speaker"].audio] == [b"speaker"]))
        time.sleep(0.05)
        self.assertEqual(FakeClient.instances["You"].audio, [])
        self.assertGreaterEqual(FakeClient.instances["You"].stopped, 1)

    def test_pause_stops_both_sessions_and_resume_restarts_selected_sources(self):
        self.transcriber.set_transcription_enabled(False)
        self.assertTrue(all(client.stopped for client in FakeClient.instances.values()))
        self.transcriber.set_source_enabled("Speaker", False)
        self.transcriber.set_transcription_enabled(True)
        self.assertGreaterEqual(FakeClient.instances["You"].started, 2)
        self.assertEqual(FakeClient.instances["Speaker"].started, 1)

    def test_clear_and_shutdown_cancel_all_resources(self):
        FakeClient.instances["You"].transcript_callback(
            transcript_event(TranscriptEventKind.COMPLETED, "You", "item-1", "final")
        )
        self.assertTrue(wait_for(lambda: len(self.conversation.finals) == 1))
        self.transcriber.clear_transcriber_context(self.audio_queue)
        self.assertTrue(self.conversation.cleared)
        self.transcriber.stop()
        self.assertTrue(all(client.stopped for client in FakeClient.instances.values()))

    def test_completed_events_are_not_dropped_when_partial_queue_is_full(self):
        self.transcriber._result_queue = queue.Queue(maxsize=1)
        self.transcriber._result_queue.put(
            transcript_event(TranscriptEventKind.PARTIAL, "You", "stale", "old")
        )
        client = FakeClient.instances["You"]

        client.transcript_callback(transcript_event(
            TranscriptEventKind.COMPLETED, "You", "item-1", "first", datetime.datetime(2026, 1, 1)
        ))
        client.transcript_callback(transcript_event(
            TranscriptEventKind.COMPLETED, "You", "item-2", "second", datetime.datetime(2026, 1, 2)
        ))

        self.assertTrue(wait_for(lambda: len(self.conversation.finals) == 2))
        self.assertEqual([item["text"] for item in self.conversation.finals], ["first", "second"])

    def test_interleaved_items_keep_distinct_partial_ids(self):
        client = FakeClient.instances["You"]
        client.transcript_callback(transcript_event(TranscriptEventKind.PARTIAL, "You", "item-a", "alpha"))
        client.transcript_callback(transcript_event(TranscriptEventKind.PARTIAL, "You", "item-b", "bravo"))
        client.transcript_callback(
            transcript_event(TranscriptEventKind.PARTIAL, "You", "item-a", "alpha updated")
        )

        self.assertTrue(wait_for(lambda: len(self.conversation.partials) == 3))
        self.assertEqual(
            [item[3] for item in self.conversation.partials],
            ["You:item-a", "You:item-b", "You:item-a"],
        )

    def test_reverse_completions_preserve_capture_chronology(self):
        speaker_time = datetime.datetime(2026, 1, 1, 12, 0, 0)
        microphone_time = datetime.datetime(2026, 1, 1, 12, 0, 1)

        FakeClient.instances["You"].transcript_callback(transcript_event(
            TranscriptEventKind.COMPLETED, "You", "item-you", "second turn", microphone_time
        ))
        FakeClient.instances["Speaker"].transcript_callback(transcript_event(
            TranscriptEventKind.COMPLETED, "Speaker", "item-speaker", "first turn", speaker_time
        ))

        self.assertTrue(wait_for(lambda: len(self.conversation.finals) == 2))
        timestamps = {item["persona"]: item["time_spoken"] for item in self.conversation.finals}
        self.assertEqual(timestamps, {"You": microphone_time, "Speaker": speaker_time})

    def test_completed_item_cache_is_bounded(self):
        self.transcriber._deduplication_cache_size = 2
        for index in range(3):
            self.transcriber._handle_completed(
                transcript_event(
                    TranscriptEventKind.COMPLETED,
                    "You",
                    f"item-{index}",
                    f"turn {index}",
                    datetime.datetime(2026, 1, 1, 12, 0, index),
                )
            )

        self.assertEqual(len(self.transcriber._completed_items), 2)
        self.assertNotIn(("You", "item-0"), self.transcriber._completed_items)


if __name__ == "__main__":
    unittest.main()
