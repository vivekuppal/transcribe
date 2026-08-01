"""Unit tests for the persistent OpenAI Realtime streaming model."""

import base64
import json
import math
import os
import struct
import threading
import time
import unittest

from sdk.streaming_transcriber_models import OpenAIRealtimeSTTModel, PCM16MonoResampler


class FakeWebSocketApp:
    def __init__(self, url, header, on_open, on_message, on_error, on_close, close_immediately=False):
        self.url = url
        self.header = header
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.close_immediately = close_immediately
        self.messages = []
        self.closed = threading.Event()

    def send(self, message):
        self.messages.append(json.loads(message))

    def run_forever(self):
        self.on_open(self)
        if not self.close_immediately:
            self.closed.wait(2)
        self.on_close(self, 1000, "closed")

    def close(self):
        self.closed.set()

    def emit(self, event):
        self.on_message(self, json.dumps(event))


class FakeWebSocketFactory:
    def __init__(self, close_first=False):
        self.close_first = close_first
        self.instances = []

    def __call__(self, *args, **kwargs):
        instance = FakeWebSocketApp(
            *args,
            **kwargs,
            close_immediately=self.close_first and not self.instances,
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
        self.partials = []
        self.completed = []
        self.model = OpenAIRealtimeSTTModel(
            source_name="You",
            source_format={"sample_rate": 16000, "sample_width": 2, "channels": 1},
            config={
                "api_key": "test-key",
                "model": "gpt-live-transcribe",
                "languages": ["en"],
                "turn_detection": "server_vad",
                "reconnect_attempts": 1,
                "reconnect_backoff_seconds": 0,
            },
            websocket_app_factory=self.factory,
            sleep_func=lambda _seconds: None,
        )
        self.model.set_error_callback(lambda *args: self.errors.append(args))
        self.model.set_partial_callback(lambda *args: self.partials.append(args))
        self.model.set_completed_callback(lambda *args: self.completed.append(args))

    def tearDown(self):
        self.model.stop()

    def test_opens_configures_and_sends_resampled_audio(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        socket = self.factory.instances[0]
        session_event = socket.messages[0]

        self.assertEqual(session_event["session"]["type"], "transcription")
        input_config = session_event["session"]["audio"]["input"]
        self.assertEqual(input_config["format"], {"type": "audio/pcm", "rate": 24000})
        self.assertEqual(input_config["transcription"]["model"], "gpt-live-transcribe")
        self.assertEqual(input_config["transcription"]["languages"], ["en"])
        self.assertEqual(input_config["turn_detection"]["type"], "server_vad")

        self.model.append_audio(b"\x01\x00" * 160)
        self.assertTrue(wait_for(lambda: len(socket.messages) >= 2))
        append_event = socket.messages[1]
        self.assertEqual(append_event["type"], "input_audio_buffer.append")
        self.assertGreater(len(base64.b64decode(append_event["audio"])), 320)

    def test_deltas_are_replaced_by_one_authoritative_completion(self):
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

        self.assertEqual(self.partials, [("You", "item-1", "Hello"), ("You", "item-1", "Hello world")])
        self.assertEqual(self.completed, [("You", "item-1", "Hello world.")])

    def test_manual_commit_and_clean_disconnect(self):
        self.model.start()
        self.assertTrue(wait_for(lambda: self.model.connected))
        self.model.commit()
        self.assertEqual(self.factory.instances[0].messages[-1]["type"], "input_audio_buffer.commit")
        self.model.stop()
        self.assertFalse(self.model.connected)

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
            sleep_func=lambda _seconds: None,
        )
        try:
            model.start()
            self.assertTrue(wait_for(lambda: len(factory.instances) == 2))
            self.assertTrue(wait_for(lambda: model.connected))
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
