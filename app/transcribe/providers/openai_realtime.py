"""OpenAI Realtime WebSocket transport for streaming transcription."""

from __future__ import annotations

import base64
import datetime
import json
import queue
import re
import threading
import time
from urllib.parse import quote

from sdk.streaming_transcriber_models import (
    PCM16MonoResampler,
    StreamingSTTModelInterface,
    StreamingTranscriptEvent,
    TranscriptEventKind,
)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
TRANSCRIPT_DELTA_EVENT = "conversation.item.input_audio_transcription.delta"
TRANSCRIPT_COMPLETED_EVENT = "conversation.item.input_audio_transcription.completed"


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
        self._converter_lock = threading.Lock()
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
        self._item_started_at: dict[str, datetime.datetime] = {}
        self._audio_timeline: list[tuple[float, float, datetime.datetime]] = []
        self._sent_audio_ms = 0.0
        self._timeline_lock = threading.Lock()
        self._transcript_callback = None
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
            if self._sender_thread and self._sender_thread.is_alive():
                self._stop_event.set()
                self._connected_event.set()
                self._sender_thread.join(timeout=2)
                if self._sender_thread.is_alive():
                    self._emit_error("Realtime sender did not stop; a duplicate worker was not started.")
                    return
            self._stop_event.clear()
            self._connected_event.clear()
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

    def append_audio(self, audio: bytes, captured_at=None):
        """Normalize source audio and enqueue it without allowing unbounded growth."""
        with self._converter_lock:
            converted = self._converter.convert(audio)
        if not converted:
            return
        try:
            self._audio_queue.put_nowait((converted, captured_at))
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
        with self._converter_lock:
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
            with self._converter_lock:
                self._converter.reset()
            self._partial_by_item.clear()
            with self._timeline_lock:
                self._item_started_at.clear()
                self._audio_timeline.clear()
                self._sent_audio_ms = 0.0

    def set_transcript_callback(self, callback):
        self._transcript_callback = callback

    def set_error_callback(self, callback):
        self._error_callback = callback

    def set_languages(self, languages: list[str]):
        """Update expected languages for future and active transcription turns."""
        self.languages = list(languages or [])
        if self._connected_event.is_set():
            self._send_event(self._session_update_event())

    def configure_source(self, source_format: dict):
        """Replace the incremental converter when the selected device format changes."""
        with self._converter_lock:
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
        self._stop_event.set()
        self._connected_event.set()

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
                        "audio": base64.b64encode(pending[0]).decode("ascii"),
                    }
                )
                self._record_sent_audio(pending[0], pending[1])
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
            with self._timeline_lock:
                self._item_started_at.clear()
                self._audio_timeline.clear()
                self._sent_audio_ms = 0.0
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
        if event_type == "input_audio_buffer.speech_started":
            item_id = str(event.get("item_id") or "")
            if item_id:
                self._item_started_at[item_id] = self._capture_time_for_audio_offset(
                    float(event.get("audio_start_ms") or 0)
                )
        elif event_type == TRANSCRIPT_DELTA_EVENT:
            item_id = str(event.get("item_id") or "")
            if not item_id:
                return
            delta = str(event.get("delta") or "")
            current = self._partial_by_item.get(item_id, "")
            updated = self._merge_delta(current, delta)
            self._partial_by_item[item_id] = updated
            if updated and self._transcript_callback:
                self._transcript_callback(StreamingTranscriptEvent(
                    kind=TranscriptEventKind.PARTIAL,
                    source=self.source_name,
                    item_id=item_id,
                    text=updated,
                ))
        elif event_type == TRANSCRIPT_COMPLETED_EVENT:
            item_id = str(event.get("item_id") or "")
            if not item_id:
                return
            final_text = str(event.get("transcript") or "").strip()
            self._partial_by_item.pop(item_id, None)
            if final_text and self._transcript_callback:
                self._transcript_callback(StreamingTranscriptEvent(
                    kind=TranscriptEventKind.COMPLETED,
                    source=self.source_name,
                    item_id=item_id,
                    text=final_text,
                    time_spoken=self._item_started_at.pop(item_id, None),
                ))
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

    def _record_sent_audio(self, audio: bytes, captured_at):
        duration_ms = len(audio) / 2 / self.input_sample_rate * 1000
        captured_at = captured_at or datetime.datetime.utcnow()
        chunk_started_at = captured_at - datetime.timedelta(milliseconds=duration_ms)
        with self._timeline_lock:
            start_ms = self._sent_audio_ms
            self._sent_audio_ms += duration_ms
            self._audio_timeline.append((start_ms, self._sent_audio_ms, chunk_started_at))

    def _capture_time_for_audio_offset(self, audio_offset_ms: float) -> datetime.datetime:
        with self._timeline_lock:
            for index in range(len(self._audio_timeline) - 1, -1, -1):
                start_ms, end_ms, captured_at = self._audio_timeline[index]
                if start_ms <= audio_offset_ms <= end_ms:
                    if index:
                        del self._audio_timeline[:index]
                    return captured_at + datetime.timedelta(milliseconds=audio_offset_ms - start_ms)
        return datetime.datetime.utcnow()

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
