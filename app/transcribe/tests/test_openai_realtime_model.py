"""Unit tests for the persistent OpenAI Realtime streaming model."""

import base64
import datetime
import json
import math
import os
import struct
import threading
import time
import unittest

from app.transcribe.providers.openai_realtime import OpenAIRealtimeSTTModel
from sdk.streaming_transcriber_models import PCM16MonoResampler, TranscriptEventKind


class FakeWebSocketApp:
    def __init__(
        self,
        url,
        header,
        on_open,
        on_message,
        on_error,
        on_close,
        close_immediately=False,
        acknowledge_session=True,
    ):
        self.url = url
        self.header = header
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.close_immediately = close_immediately
        self.acknowledge_session = acknowledge_session
        self.messages = []
        self.closed = threading.Event()

    def send(self, message):
        self.messages.append(json.loads(message))

    def run_forever(self):
        self.on_open(self)
        if self.acknowledge_session and not self.close_immediately:
            self.emit({"type": "session.updated", "session": {"type": "transcription"}})
        if not self.close_immediately:
            self.closed.wait(2)
        self.on_close(self, 1000, "closed")

    def close(self):
        self.closed.set()

    def emit(self, event):
        self.on_message(self, json.dumps(event))


class FakeWebSocketFactory:
    def __init__(self, close_first=False, close_always=False, acknowledge_session=True):
        self.close_first = close_first
        self.close_always = close_always
        self.acknowledge_session = acknowledge_session
        self.instances = []

    def __call__(self, *args, **kwargs):
        instance = FakeWebSocketApp(
            *args,
            **kwargs,
            close_immediately=self.close_always or (self.close_first and not self.instances),
            acknowledge_session=self.acknowledge_session,
        )
        self.instances.append(instance)
        return instance


def wait_for(predicate, timeout=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class TestPCM16MonoResampler(unittest.TestCase):
    def test_split_unaligned_chunks_match_single_conversion(self):
        samples = [int(10000 * math.sin(index / 8)) for index in range(320)]
        stereo = b"".join(struct.pack("<hh", sample, -sample) for sample in samples)
        whole = PCM16MonoResampler(16000, 2, 2).convert(stereo)

        split_converter = PCM16MonoResampler(16000, 2, 2)
        split = b"".join(
            split_converter.convert(chunk)
            for chunk in (stereo[:7], stereo[7:101], stereo[101:])
        )

        self.assertEqual(split, whole)
        self.assertEqual(len(split) % 2, 0)

    def test_multichannel_input_is_downmixed(self):
        frames = b"".join(struct.pack("<hhh", 3000, 0, -3000) for _ in range(10))
        converted = PCM16MonoResampler(24000, 2, 3).convert(frames)
        self.assertEqual(converted, b"\x00\x00" * 10)


class TestOpenAIRealtimeSTTModel(unittest.TestCase):
    def setUp(self):
        self.factory = FakeWebSocketFactory()
        self.errors = []
        self.events = []
        self.secret_requests = []

        def create_secret(api_key, session):
            self.secret_requests.append((api_key, session))
            return "test-ephemeral-key"

        self.model = OpenAIRealtimeSTTModel(
            source_name="You",
            source_format={"sample_rate": 16000, "sample_width": 2, "channels": 1},
            config={
                "api_key": "test-key",
                "model": "gpt-live-transcribe",
                "languages": ["en"],
                "turn_detection": None,
                "manual_commit_interval_seconds": 3,
                "reconnect_attempts": 1,
                "reconnect_backoff_seconds": 0,
            },
            websocket_app_factory=self.factory,
            client_secret_factory=create_secret,
            sleep_func=lambda _seconds: None,
        )
        self.model.set_error_callback(lambda *args: self.errors.append(args))
        self.model.set_transcript_callback(self.events.append)

    def tearDown(self):
        self.model.stop()

    def test_opens_configures_and_sends_resampled_audio(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]
        session_event = socket.messages[0]

        self.assertEqual(
            socket.url,
            "wss://api.openai.com/v1/realtime",
        )
        self.assertEqual(socket.header, ["Authorization: Bearer test-ephemeral-key"])
        self.assertEqual(self.secret_requests[0][0], "test-key")
        self.assertEqual(self.secret_requests[0][1]["type"], "transcription")
        self.assertEqual(session_event["session"]["type"], "transcription")
        input_config = session_event["session"]["audio"]["input"]
        self.assertEqual(input_config["format"], {"type": "audio/pcm", "rate": 24000})
        self.assertEqual(input_config["transcription"]["model"], "gpt-live-transcribe")
        self.assertEqual(input_config["transcription"]["languages"], ["en"])
        self.assertIsNone(input_config["turn_detection"])

        self.model.append_audio(b"\x01\x00" * 160)
        self.assertTrue(wait_for(lambda: len(socket.messages) >= 2))
        append_event = socket.messages[1]
        self.assertEqual(append_event["type"], "input_audio_buffer.append")
        self.assertGreater(len(base64.b64decode(append_event["audio"])), 320)

    def test_connection_is_ready_only_after_session_is_accepted(self):
        factory = FakeWebSocketFactory(acknowledge_session=False)
        model = OpenAIRealtimeSTTModel(
            source_name="Speaker",
            source_format={"sample_rate": 48000, "sample_width": 2, "channels": 2},
            config={"api_key": "test-key", "reconnect_attempts": 0},
            websocket_app_factory=factory,
            client_secret_factory=lambda *_args: "test-ephemeral-key",
            sleep_func=lambda _seconds: None,
        )
        try:
            model.start()
            self.assertTrue(wait_for(lambda: len(factory.instances) == 1))
            self.assertTrue(wait_for(lambda: len(factory.instances[0].messages) == 1))
            self.assertFalse(model.connected)

            factory.instances[0].emit({
                "type": "session.updated",
                "session": {"type": "transcription"},
            })
            self.assertTrue(wait_for(lambda: model.connected))
        finally:
            model.stop()

    def test_unexpected_session_type_is_rejected(self):
        factory = FakeWebSocketFactory(acknowledge_session=False)
        model = OpenAIRealtimeSTTModel(
            source_name="Speaker",
            source_format={"sample_rate": 48000, "sample_width": 2, "channels": 2},
            config={"api_key": "test-key", "reconnect_attempts": 0},
            websocket_app_factory=factory,
            client_secret_factory=lambda *_args: "test-ephemeral-key",
            sleep_func=lambda _seconds: None,
        )
        errors = []
        model.set_error_callback(lambda *args: errors.append(args))
        try:
            model.start()
            self.assertTrue(wait_for(lambda: len(factory.instances) == 1))
            factory.instances[0].emit({
                "type": "session.updated",
                "session": {"type": "realtime"},
            })

            self.assertFalse(model.connected)
            self.assertTrue(factory.instances[0].closed.is_set())
            self.assertIn("unexpected session type", errors[-1][1])
        finally:
            model.stop()

    def test_deltas_and_completions_are_emitted_as_typed_events(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]
        socket.emit({
            "type": "conversation.item.input_audio_transcription.delta",
            "item_id": "item-1",
            "delta": "Hello",
        })
        socket.emit({
            "type": "conversation.item.input_audio_transcription.delta",
            "item_id": "item-1",
            "delta": " world",
        })
        completed = {
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "item-1",
            "transcript": "Hello world.",
        }
        socket.emit(completed)
        socket.emit(completed)

        partials = [event for event in self.events if event.kind is TranscriptEventKind.PARTIAL]
        completed_events = [event for event in self.events if event.kind is TranscriptEventKind.COMPLETED]
        self.assertEqual([event.text for event in partials], ["Hello", "Hello world"])
        self.assertEqual([event.text for event in completed_events], ["Hello world.", "Hello world."])

    def test_completion_uses_capture_time_from_speech_start(self):
        captured_at = datetime.datetime(2026, 1, 1, 12, 0, 1)
        self.model.turn_detection = "server_vad"
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]
        self.model.append_audio(b"\x01\x00" * 2400, captured_at=captured_at)
        self.assertTrue(wait_for(lambda: len(socket.messages) >= 2))
        socket.emit({
            "type": "input_audio_buffer.speech_started",
            "item_id": "item-timed",
            "audio_start_ms": 25,
        })
        socket.emit({
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "item-timed",
            "transcript": "Timed speech",
        })

        expected = captured_at - datetime.timedelta(milliseconds=125)
        self.assertAlmostEqual(
            self.events[-1].time_spoken.timestamp(),
            expected.timestamp(),
            places=3,
        )

    def test_manual_commit_uses_capture_time_without_speech_started_event(self):
        captured_at = datetime.datetime(2026, 1, 1, 12, 0, 5)
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]
        self.model.append_audio(b"\x01\x00" * 4800, captured_at=captured_at)
        self.assertTrue(wait_for(lambda: len(socket.messages) >= 2))
        self.model.commit()
        socket.emit({
            "type": "input_audio_buffer.committed",
            "item_id": "item-manual",
        })
        socket.emit({
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "item-manual",
            "transcript": "Manually committed speech",
        })

        expected = captured_at - datetime.timedelta(milliseconds=300)
        self.assertAlmostEqual(
            self.events[-1].time_spoken.timestamp(),
            expected.timestamp(),
            places=3,
        )

    def test_manual_commit_timestamps_follow_server_item_assignment_order(self):
        first_captured_at = datetime.datetime(2026, 1, 1, 12, 0, 1)
        second_captured_at = datetime.datetime(2026, 1, 1, 12, 0, 2)
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]

        for index, captured_at in enumerate((first_captured_at, second_captured_at), start=1):
            self.model.append_audio(b"\x01\x00" * 2400, captured_at=captured_at)
            self.assertTrue(wait_for(
                lambda: sum(
                    message["type"] == "input_audio_buffer.append"
                    for message in socket.messages
                ) >= index
            ))
            self.model.commit()

        socket.emit({"type": "input_audio_buffer.committed", "item_id": "first"})
        socket.emit({"type": "input_audio_buffer.committed", "item_id": "second"})
        socket.emit({
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "second",
            "transcript": "Second",
        })
        socket.emit({
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "first",
            "transcript": "First",
        })

        expected = {
            "first": first_captured_at - datetime.timedelta(milliseconds=150),
            "second": second_captured_at - datetime.timedelta(milliseconds=150),
        }
        for event in self.events:
            self.assertAlmostEqual(
                event.time_spoken.timestamp(),
                expected[event.item_id].timestamp(),
                places=3,
            )

    def test_manual_commit_and_clean_disconnect(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        self.model.commit()
        self.assertEqual(self.factory.instances[0].messages[-1]["type"], "input_audio_buffer.commit")
        self.model.stop()
        self.assertFalse(self.model.connected)

    def test_manual_turn_mode_commits_audio_periodically(self):
        captured_at = datetime.datetime(2026, 1, 1, 12, 0, 5)
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]

        self.model.append_audio(b"\x01\x00" * 50000, captured_at=captured_at)
        self.assertTrue(wait_for(lambda: len(socket.messages) >= 3))

        self.assertEqual(socket.messages[-2]["type"], "input_audio_buffer.append")
        self.assertEqual(socket.messages[-1]["type"], "input_audio_buffer.commit")
        socket.emit({"type": "input_audio_buffer.committed", "item_id": "periodic"})
        socket.emit({
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "periodic",
            "transcript": "Periodic commit",
        })
        expected = captured_at - datetime.timedelta(milliseconds=3125)
        self.assertAlmostEqual(
            self.events[-1].time_spoken.timestamp(),
            expected.timestamp(),
            places=3,
        )

    def test_source_reconfiguration_is_safe_during_audio_append(self):
        errors = []

        def append_audio():
            try:
                for _ in range(100):
                    self.model.append_audio(b"\x01\x00" * 160)
            except Exception as exception:  # test captures any cross-thread failure
                errors.append(exception)

        worker = threading.Thread(target=append_audio)
        worker.start()
        for sample_rate in (24000, 16000, 48000, 16000):
            self.model.configure_source({"sample_rate": sample_rate, "sample_width": 2, "channels": 1})
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])

    def test_reconnects_independently_with_bounded_attempts(self):
        factory = FakeWebSocketFactory(close_first=True)
        model = OpenAIRealtimeSTTModel(
            source_name="Speaker",
            source_format={"sample_rate": 48000, "sample_width": 2, "channels": 2},
            config={
                "api_key": "test-key",
                "reconnect_attempts": 1,
                "reconnect_backoff_seconds": 0,
            },
            websocket_app_factory=factory,
            client_secret_factory=lambda *_args: "test-ephemeral-key",
            sleep_func=lambda _seconds: None,
        )
        try:
            model.start()
            self.assertTrue(wait_for(lambda: len(factory.instances) == 2))
            self.assertTrue(wait_for(lambda: model.connected))
        finally:
            model.stop()

    def test_stop_during_secret_creation_does_not_open_websocket(self):
        secret_requested = threading.Event()
        release_secret = threading.Event()
        factory = FakeWebSocketFactory()

        def create_secret(*_args):
            secret_requested.set()
            release_secret.wait(2)
            return "test-ephemeral-key"

        model = OpenAIRealtimeSTTModel(
            source_name="Speaker",
            source_format={"sample_rate": 48000, "sample_width": 2, "channels": 2},
            config={"api_key": "test-key", "reconnect_attempts": 0},
            websocket_app_factory=factory,
            client_secret_factory=create_secret,
            sleep_func=lambda _seconds: None,
        )
        model.start()
        self.assertTrue(secret_requested.wait(1))
        stopper = threading.Thread(target=model.stop)
        stopper.start()
        self.assertTrue(wait_for(model._stop_event.is_set))
        release_secret.set()
        stopper.join(timeout=2)

        self.assertFalse(stopper.is_alive())
        self.assertEqual(factory.instances, [])

    def test_restart_after_retry_exhaustion_replaces_sender_worker(self):
        factory = FakeWebSocketFactory(close_always=True)
        model = OpenAIRealtimeSTTModel(
            source_name="Speaker",
            source_format={"sample_rate": 48000, "sample_width": 2, "channels": 2},
            config={"api_key": "test-key", "reconnect_attempts": 0},
            websocket_app_factory=factory,
            client_secret_factory=lambda *_args: "test-ephemeral-key",
            sleep_func=lambda _seconds: None,
        )
        try:
            model.start()
            first_sender = model._sender_thread
            self.assertTrue(wait_for(lambda: not first_sender.is_alive()))

            factory.close_always = False
            model.start()
            self.assertIsNot(model._sender_thread, first_sender)
            self.assertTrue(wait_for(lambda: model.connected))
            active_senders = [
                thread for thread in threading.enumerate()
                if thread.name == "OpenAIRealtimeSender-Speaker"
            ]
            self.assertEqual(len(active_senders), 1)
        finally:
            model.stop()

    def test_provider_errors_are_sanitized(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        self.factory.instances[0].emit({
            "type": "error",
            "error": {"message": "Authorization: Bearer sk-secret-value quota exceeded"},
        })
        self.assertNotIn("sk-secret-value", self.errors[-1][1])

    def test_missing_api_key_fails_before_starting_threads(self):
        with self.assertRaisesRegex(ValueError, "requires an OpenAI API key"):
            OpenAIRealtimeSTTModel(
                source_name="You",
                source_format={"sample_rate": 16000, "sample_width": 2, "channels": 1},
                config={"api_key": "API_KEY"},
            )


@unittest.skipUnless(
    os.environ.get("TRANSCRIBE_OPENAI_REALTIME_SMOKE") == "1" and os.environ.get("OPENAI_API_KEY"),
    "Set TRANSCRIBE_OPENAI_REALTIME_SMOKE=1 and OPENAI_API_KEY for the live smoke test.",
)
class TestOpenAIRealtimeSmoke(unittest.TestCase):
    def test_connect_and_close(self):
        model = OpenAIRealtimeSTTModel(
            source_name="Smoke",
            source_format={"sample_rate": 24000, "sample_width": 2, "channels": 1},
            config={"api_key": os.environ["OPENAI_API_KEY"], "reconnect_attempts": 0},
        )
        try:
            model.start()
            self.assertTrue(wait_for(lambda: model.connected, timeout=10))
        finally:
            model.stop()


if __name__ == "__main__":
    unittest.main()
