"""Tests for the small-block capture path used by persistent STT providers."""

import queue
import threading
import time
import unittest
from unittest.mock import MagicMock

from sdk.audio_recorder import BaseRecorder


class DummyRecorder(BaseRecorder):
    def get_name(self):
        return "dummy"


class FakeStream:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.lock = threading.Lock()

    def read(self, _size):
        with self.lock:
            return self.chunks.pop(0) if self.chunks else b""


class FakeSource:
    CHUNK = 4
    SAMPLE_RATE = 1000

    def __init__(self, chunks):
        self.stream = FakeStream(chunks)

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False


class TestStreamingAudioCapture(unittest.TestCase):
    @staticmethod
    def recorder(chunks):
        recorder = DummyRecorder.__new__(DummyRecorder)
        recorder.source = FakeSource(chunks)
        recorder.source_name = "You"
        recorder.enabled = True
        recorder.audio_file_name = None
        recorder.config = {"General": {"stt": "openai-realtime"}}
        recorder.config["OpenAIRealtime"] = {"capture_chunk_duration_ms": 100}
        return recorder

    def test_continuous_capture_enqueues_raw_pcm_blocks(self):
        recorder = self.recorder([b"first", b"second", b""])
        audio_queue = queue.Queue()

        stop = recorder._record_audio_continuously(audio_queue)
        deadline = time.time() + 1
        while audio_queue.qsize() < 2 and time.time() < deadline:
            time.sleep(0.01)
        stop(wait_for_stop=True)

        captured = [audio_queue.get_nowait(), audio_queue.get_nowait()]
        self.assertEqual([item[0] for item in captured], ["You", "You"])
        self.assertEqual([item[1] for item in captured], [b"first", b"second"])

    def test_record_audio_selects_streaming_path_only_for_realtime_backend(self):
        recorder = self.recorder([])
        recorder._record_audio_continuously = MagicMock(return_value="stop")
        audio_queue = queue.Queue()

        result = recorder.record_audio(audio_queue)

        self.assertEqual(result, "stop")
        recorder._record_audio_continuously.assert_called_once_with(audio_queue)

    def test_disabled_source_does_not_enqueue_audio(self):
        recorder = self.recorder([b"ignored", b""])
        recorder.enabled = False
        audio_queue = queue.Queue()

        stop = recorder._record_audio_continuously(audio_queue)
        stop(wait_for_stop=True)

        self.assertTrue(audio_queue.empty())

    def test_full_ingress_queue_replaces_oldest_audio(self):
        recorder = self.recorder([])
        audio_queue = queue.Queue(maxsize=2)

        recorder._enqueue_audio(audio_queue, b"first")
        recorder._enqueue_audio(audio_queue, b"second")
        recorder._enqueue_audio(audio_queue, b"latest")

        self.assertEqual(audio_queue.qsize(), 2)
        self.assertEqual([audio_queue.get()[1], audio_queue.get()[1]], [b"second", b"latest"])


if __name__ == "__main__":
    unittest.main()
