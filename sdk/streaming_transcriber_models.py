"""Provider-neutral streaming STT contracts and OpenAI Realtime support."""

from __future__ import annotations

import audioop
import base64
import json
import queue
import re
import threading
import time
from abc import ABC, abstractmethod
from array import array
from urllib.parse import quote


OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
TRANSCRIPT_DELTA_EVENT = "conversation.item.input_audio_transcription.delta"
TRANSCRIPT_COMPLETED_EVENT = "conversation.item.input_audio_transcription.completed"


class StreamingSTTModelInterface(ABC):
    """Contract for STT providers that keep a persistent streaming session."""

    @abstractmethod
    def start(self):
        """Open the provider session and start its background workers."""

    @abstractmethod
    def append_audio(self, audio: bytes):
        """Append source-format PCM audio to the persistent session."""

    @abstractmethod
    def commit(self):
        """Commit the current input turn when automatic turn detection is disabled."""

    @abstractmethod
    def stop(self):
        """Close the provider session and all background workers."""

    @abstractmethod
    def set_partial_callback(self, callback):
        """Set callback(source, item_id, text) for replaceable partial text."""

    @abstractmethod
    def set_completed_callback(self, callback):
        """Set callback(source, item_id, text) for confirmed transcript text."""

    @abstractmethod
    def set_error_callback(self, callback):
        """Set callback(source, sanitized_message) for provider errors."""


class PCM16MonoResampler:
    """Incrementally convert arbitrary interleaved PCM into 24 kHz mono PCM16."""

    def __init__(self, sample_rate: int, sample_width: int, channels: int, target_rate: int = 24000):
        if sample_rate <= 0 or sample_width not in (1, 2, 3, 4) or channels <= 0:
            raise ValueError("Invalid PCM source format")
        self.sample_rate = int(sample_rate)
        self.sample_width = int(sample_width)
        self.channels = int(channels)
        self.target_rate = int(target_rate)
        self._pending = b""
        self._rate_state = None
        self._lock = threading.Lock()

    def convert(self, audio: bytes) -> bytes:
        """Convert a chunk without losing partial frames at chunk boundaries."""
        if not audio:
            return b""
        with self._lock:
            framed = self._pending + bytes(audio)
            frame_size = self.sample_width * self.channels
            complete_size = len(framed) - (len(framed) % frame_size)
            if complete_size <= 0:
                self._pending = framed
                return b""
            complete = framed[:complete_size]
            self._pending = framed[complete_size:]

            if self.sample_width == 1:
                complete = audioop.bias(complete, 1, -128)
            pcm16 = audioop.lin2lin(complete, self.sample_width, 2)
            mono = self._to_mono(pcm16)
            if self.sample_rate == self.target_rate:
                return mono
            converted, self._rate_state = audioop.ratecv(
                mono,
                2,
                1,
                self.sample_rate,
                self.target_rate,
                self._rate_state,
            )
            return converted

    def reset(self):
        """Drop incomplete input and resampler history after an explicit stream reset."""
        with self._lock:
            self._pending = b""
            self._rate_state = None

    def _to_mono(self, pcm16: bytes) -> bytes:
        if self.channels == 1:
            return pcm16
        if self.channels == 2:
            return audioop.tomono(pcm16, 2, 0.5, 0.5)

        samples = array("h")
        samples.frombytes(pcm16)
        mono = array("h")
        for offset in range(0, len(samples), self.channels):
            frame = samples[offset:offset + self.channels]
            mono.append(int(sum(frame) / len(frame)))
        return mono.tobytes()


class OpenAIRealtimeSTTModel(StreamingSTTModelInterface):
    """One persistent OpenAI Realtime transcription session for one audio source."""

    def __init__(
        self,
        source_name: str,
        source_format: dict,
        config: dict,
        websocket_app_factory=None,
        sleep_func=time.sleep,
    ):
        api_key = str(config.get("api_key") or "").strip()
        if not api_key or api_key == "API_KEY":
            raise ValueError("OpenAI Realtime transcription requires an OpenAI API key.")

        self.source_name = source_name
        self.api_key = api_key
        self.model = config.get("model", "gpt-live-transcribe")
        self.input_sample_rate = int(config.get("input_sample_rate", 24000))
        self.turn_detection = config.get("turn_detection", "server_vad")
        self.reconnect_attempts = max(0, int(config.get("reconnect_attempts", 3)))
        self.reconnect_backoff_seconds = max(0.0, float(config.get("reconnect_backoff_seconds", 2)))
        self.max_buffered_chunks = max(1, int(config.get("max_buffered_chunks", 120)))
        self.transcription_delay = config.get("delay", "low")
        self.languages = list(config.get("languages") or [])
        self.prompt = str(config.get("prompt") or "").strip()
        self.keywords = list(config.get("keywords") or [])
        self.vad_threshold = float(config.get("vad_threshold", 0.5))
        self.vad_prefix_padding_ms = int(config.get("vad_prefix_padding_ms", 300))
        self.vad_silence_duration_ms = int(config.get("vad_silence_duration_ms", 500))

        self._converter = PCM16MonoResampler(
            sample_rate=int(source_format["sample_rate"]),
            sample_width=int(source_format["sample_width"]),
            channels=int(source_format["channels"]),
            target_rate=self.input_sample_rate,
        )
        self._websocket_app_factory = websocket_app_factory or self._default_websocket_app_factory
        self._sleep = sleep_func
        self._audio_queue: queue.Queue = queue.Queue(maxsize=self.max_buffered_chunks)
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._lifecycle_lock = threading.Lock()
        self._websocket = None
        self._connection_thread = None
        self._sender_thread = None
        self._partial_by_item: dict[str, str] = {}
        self._completed_items: set[str] = set()
        self._partial_callback = None
        self._completed_callback = None
        self._error_callback = None

    @staticmethod
    def _default_websocket_app_factory(*args, **kwargs):
        import websocket  # pylint: disable=import-outside-toplevel
        return websocket.WebSocketApp(*args, **kwargs)

    def start(self):
        """Start connection and sender workers once; safe to call repeatedly."""
        with self._lifecycle_lock:
            if self._connection_thread and self._connection_thread.is_alive():
                return
            self._stop_event.clear()
            self._connection_thread = threading.Thread(
                target=self._connection_loop,
                name=f"OpenAIRealtime-{self.source_name}",
                daemon=True,
            )
            self._sender_thread = threading.Thread(
                target=self._sender_loop,
                name=f"OpenAIRealtimeSender-{self.source_name}",
                daemon=True,
            )
            self._connection_thread.start()
            self._sender_thread.start()

    def append_audio(self, audio: bytes):
        """Normalize source audio and enqueue it without allowing unbounded growth."""
        converted = self._converter.convert(audio)
        if not converted:
            return
        try:
            self._audio_queue.put_nowait(converted)
        except queue.Full:
            self._emit_error(
                "Realtime audio buffer is full; the connection is not keeping up and audio was not queued."
            )

    def commit(self):
        """Commit the current input buffer for manual-turn configurations."""
        self._send_event({"type": "input_audio_buffer.commit"})

    def clear_audio(self):
        """Clear queued and server-side uncommitted audio."""
        self._drain_queue(self._audio_queue)
        self._converter.reset()
        self._partial_by_item.clear()
        if self._connected_event.is_set():
            try:
                self._send_event({"type": "input_audio_buffer.clear"})
            except Exception as exception:  # network state may change between the check and send
                self._emit_error(exception)

    def stop(self):
        """Stop workers and close the socket without leaving non-daemon resources."""
        with self._lifecycle_lock:
            self._stop_event.set()
            self._connected_event.set()
            websocket_app = self._websocket
            if websocket_app is not None:
                try:
                    websocket_app.close()
                except Exception as exception:  # close is best effort
                    self._emit_error(exception)
            current = threading.current_thread()
            for worker in (self._sender_thread, self._connection_thread):
                if worker and worker is not current and worker.is_alive():
                    worker.join(timeout=2)
            self._connected_event.clear()
            self._drain_queue(self._audio_queue)
            self._converter.reset()
            self._partial_by_item.clear()

    def set_partial_callback(self, callback):
        self._partial_callback = callback

    def set_completed_callback(self, callback):
        self._completed_callback = callback

    def set_error_callback(self, callback):
        self._error_callback = callback

    def set_languages(self, languages: list[str]):
        """Update expected languages for future and active transcription turns."""
        self.languages = list(languages or [])
        if self._connected_event.is_set():
            self._send_event(self._session_update_event())

    def configure_source(self, source_format: dict):
        """Replace the incremental converter when the selected device format changes."""
        self._converter = PCM16MonoResampler(
            sample_rate=int(source_format["sample_rate"]),
            sample_width=int(source_format["sample_width"]),
            channels=int(source_format["channels"]),
            target_rate=self.input_sample_rate,
        )

    @property
    def connected(self) -> bool:
        return self._connected_event.is_set() and not self._stop_event.is_set()

    def _connection_loop(self):
        url = f"{OPENAI_REALTIME_URL}?model={quote(self.model)}"
        headers = [f"Authorization: Bearer {self.api_key}"]
        total_attempts = self.reconnect_attempts + 1
        for attempt in range(total_attempts):
            if self._stop_event.is_set():
                return
            if attempt:
                self._emit_error(f"Realtime connection retry {attempt}/{self.reconnect_attempts}.")
                self._sleep(self.reconnect_backoff_seconds * attempt)
                if self._stop_event.is_set():
                    return
            try:
                websocket_app = self._websocket_app_factory(
                    url,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._websocket = websocket_app
                websocket_app.run_forever()
            except Exception as exception:
                self._emit_error(exception)
            finally:
                self._connected_event.clear()
                self._websocket = None
            if self._stop_event.is_set():
                return
        self._emit_error("Realtime connection stopped after the configured retry limit.")

    def _sender_loop(self):
        pending = None
        while not self._stop_event.is_set():
            if pending is None:
                try:
                    pending = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
            if not self._connected_event.wait(timeout=0.1):
                continue
            if self._stop_event.is_set():
                return
            try:
                self._send_event(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pending).decode("ascii"),
                    }
                )
                pending = None
            except Exception as exception:
                self._connected_event.clear()
                self._emit_error(f"Audio send failed; reconnecting ({exception.__class__.__name__}).")
                websocket_app = self._websocket
                if websocket_app is not None:
                    try:
                        websocket_app.close()
                    except Exception:
                        pass

    def _on_open(self, websocket_app):
        try:
            websocket_app.send(json.dumps(self._session_update_event()))
            self._connected_event.set()
        except Exception as exception:
            self._emit_error(exception)
            websocket_app.close()

    def _on_message(self, _websocket_app, message):
        try:
            event = json.loads(message)
        except (TypeError, json.JSONDecodeError):
            self._emit_error("Realtime server returned an invalid JSON event.")
            return

        event_type = event.get("type")
        if event_type == TRANSCRIPT_DELTA_EVENT:
            item_id = str(event.get("item_id") or "")
            if not item_id or item_id in self._completed_items:
                return
            delta = str(event.get("delta") or "")
            current = self._partial_by_item.get(item_id, "")
            updated = self._merge_delta(current, delta)
            self._partial_by_item[item_id] = updated
            if updated and self._partial_callback:
                self._partial_callback(self.source_name, item_id, updated)
        elif event_type == TRANSCRIPT_COMPLETED_EVENT:
            item_id = str(event.get("item_id") or "")
            if not item_id or item_id in self._completed_items:
                return
            self._completed_items.add(item_id)
            final_text = str(event.get("transcript") or "").strip()
            self._partial_by_item.pop(item_id, None)
            if final_text and self._completed_callback:
                self._completed_callback(self.source_name, item_id, final_text)
        elif event_type in ("error", "conversation.item.input_audio_transcription.failed"):
            error = event.get("error") or {}
            self._emit_error(error.get("message") or error.get("code") or "Realtime transcription failed.")

    def _on_error(self, _websocket_app, error):
        if not self._stop_event.is_set():
            self._emit_error(error)

    def _on_close(self, _websocket_app, _status_code, _message):
        self._connected_event.clear()

    def _session_update_event(self) -> dict:
        transcription = {"model": self.model, "delay": self.transcription_delay}
        if self.languages:
            transcription["languages"] = self.languages
        if self.prompt:
            transcription["prompt"] = self.prompt
        if self.keywords:
            transcription["keywords"] = self.keywords

        turn_detection = None
        if self.turn_detection == "server_vad":
            turn_detection = {
                "type": "server_vad",
                "threshold": self.vad_threshold,
                "prefix_padding_ms": self.vad_prefix_padding_ms,
                "silence_duration_ms": self.vad_silence_duration_ms,
            }

        return {
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": self.input_sample_rate},
                        "transcription": transcription,
                        "turn_detection": turn_detection,
                    }
                },
            },
        }

    def _send_event(self, event: dict):
        websocket_app = self._websocket
        if websocket_app is None:
            raise ConnectionError("Realtime WebSocket is not connected.")
        websocket_app.send(json.dumps(event))

    def _emit_error(self, error):
        message = self._sanitize_error(error)
        if self._error_callback:
            self._error_callback(self.source_name, message)

    @staticmethod
    def _sanitize_error(error) -> str:
        message = str(error or "Unknown Realtime transcription error.")
        message = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", message, flags=re.IGNORECASE)
        message = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", message)
        return message[:500]

    @staticmethod
    def _merge_delta(current: str, delta: str) -> str:
        if not delta:
            return current
        if delta == current:
            return current
        if delta.startswith(current):
            return delta
        return current + delta

    @staticmethod
    def _drain_queue(target_queue: queue.Queue):
        try:
            while True:
                target_queue.get_nowait()
        except queue.Empty:
            pass
