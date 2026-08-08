"""Application adapter for independent OpenAI Realtime audio sessions."""

from __future__ import annotations

import datetime
import queue
import threading
from collections import deque

from sdk.streaming_transcriber_models import StreamingTranscriptEvent, TranscriptEventKind

from . import constants
from .providers.openai_realtime import OpenAIRealtimeSTTModel
from .transcriber import TranscriberInterface
from tsutils import app_logging as al


logger = al.get_module_logger(al.TRANSCRIBER_LOGGER)


class OpenAIRealtimeTranscriber(TranscriberInterface):
    """Route microphone and loopback PCM to separate persistent STT sessions."""

    def __init__(
        self,
        mic_source,
        speaker_source,
        convo,
        config: dict,
        client_factory=OpenAIRealtimeSTTModel,
    ):
        self.config = config
        self.conversation = convo
        self.supports_diarization = False
        self.transcript_changed_event = threading.Event()
        self.transcribe = True
        self.clear_transcript_periodically = bool(config["General"]["clear_transcript_periodically"])
        self.clear_transcript_interval_seconds = int(config["General"]["clear_transcript_interval_seconds"])
        self._stop_event = threading.Event()
        self._result_queue: queue.Queue = queue.Queue(
            maxsize=max(10, int(config.get("OpenAIRealtime", {}).get("event_queue_size", 500)))
        )
        self._completed_queue: queue.Queue = queue.Queue()
        self._partial_items: dict[tuple[str, str], str] = {}
        self._completed_items: set[tuple[str, str]] = set()
        self._completed_item_order: deque[tuple[str, str]] = deque()
        self._deduplication_cache_size = max(
            1,
            int(config.get("OpenAIRealtime", {}).get("deduplication_cache_size", 2048)),
        )
        self._source_enabled = {
            constants.PERSONA_YOU: True,
            constants.PERSONA_SPEAKER: True,
        }
        self._source_formats = {
            constants.PERSONA_YOU: self._source_format(mic_source),
            constants.PERSONA_SPEAKER: self._source_format(speaker_source),
        }

        realtime_config = dict(config.get("OpenAIRealtime", {}))
        realtime_config["api_key"] = config.get("OpenAI", {}).get("api_key")
        realtime_config["languages"] = [self._language_code(config["OpenAI"].get("audio_lang", "English"))]
        self.clients = {
            source_name: client_factory(
                source_name=source_name,
                source_format=source_format,
                config=dict(realtime_config),
            )
            for source_name, source_format in self._source_formats.items()
        }
        for client in self.clients.values():
            client.set_transcript_callback(self._queue_transcript_event)
            client.set_error_callback(self._queue_error)

    @staticmethod
    def _source_format(source) -> dict:
        return {
            "sample_rate": int(source.SAMPLE_RATE),
            "sample_width": int(source.SAMPLE_WIDTH),
            "channels": int(source.channels),
        }

    @staticmethod
    def _language_code(lang: str) -> str:
        from tsutils import language  # pylint: disable=import-outside-toplevel

        normalized = str(lang or "").strip().lower()
        for code, name in language.LANGUAGES_DICT.items():
            if name == normalized:
                return code
        return normalized if normalized else "en"

    def set_source_properties(self, mic_source=None, speaker_source=None):
        """Keep each session's converter aligned with its real capture device."""
        updates = {
            constants.PERSONA_YOU: mic_source,
            constants.PERSONA_SPEAKER: speaker_source,
        }
        for source_name, source in updates.items():
            if source is None:
                continue
            source_format = self._source_format(source)
            self._source_formats[source_name] = source_format
            self.clients[source_name].configure_source(source_format)

    def set_language(self, lang: str):
        """Update expected input language on both active sessions."""
        languages = [self._language_code(lang)]
        for client in self.clients.values():
            client.set_languages(languages)

    def transcribe_audio_queue(self, audio_queue: queue.Queue):
        """Continuously route tagged raw audio and serialize callback results."""
        self._start_enabled_clients()
        while not self._stop_event.is_set():
            self._drain_result_queue()
            try:
                who_spoke, data, time_spoken = audio_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if self.transcribe and self._source_enabled.get(who_spoke, False):
                try:
                    self.clients[who_spoke].append_audio(data, captured_at=time_spoken)
                except (KeyError, TypeError, ValueError) as exception:
                    self._queue_error(who_spoke, f"Could not process source audio: {exception}")
            self._drain_result_queue()

        self._drain_result_queue()

    def set_source_enabled(self, source_name: str, enabled: bool):
        """Start or stop one billable network session as its capture source changes."""
        if source_name not in self.clients:
            return
        self._source_enabled[source_name] = bool(enabled)
        if enabled and self.transcribe and not self._stop_event.is_set():
            self.clients[source_name].start()
        else:
            self.clients[source_name].stop()

    def set_transcription_enabled(self, enabled: bool):
        """Pause or resume all selected sessions with the desktop transcription toggle."""
        self.transcribe = bool(enabled)
        if self.transcribe:
            self._start_enabled_clients()
        else:
            for client in self.clients.values():
                client.stop()

    def stop(self):
        """Close both independent sessions and unblock the consumer loop."""
        self._stop_event.set()
        for client in self.clients.values():
            client.stop()

    def get_transcript(self, length: int = 0):
        """Return only confirmed conversation rows, excluding volatile partials."""
        return self.conversation.get_conversation(
            sources=[constants.PERSONA_YOU, constants.PERSONA_SPEAKER],
            length=length,
        )

    def clear_transcript_data_loop(self, audio_queue: queue.Queue):
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.clear_transcript_interval_seconds):
                return
            if self.clear_transcript_periodically:
                self.clear_transcriber_context(audio_queue)

    def clear_transcriber_context(self, audio_queue: queue.Queue):
        """Clear confirmed, partial, queued, and server-side uncommitted state."""
        self._partial_items.clear()
        self._completed_items.clear()
        self._completed_item_order.clear()
        self._drain_queue(self._result_queue)
        self._drain_queue(self._completed_queue)
        with audio_queue.mutex:
            audio_queue.queue.clear()
        for client in self.clients.values():
            client.clear_audio()
        self.conversation.clear_conversation_data()

    def _start_enabled_clients(self):
        if not self.transcribe or self._stop_event.is_set():
            return
        for source_name, client in self.clients.items():
            if self._source_enabled[source_name]:
                client.start()

    def _queue_transcript_event(self, event: StreamingTranscriptEvent):
        if event.kind is TranscriptEventKind.COMPLETED:
            self._completed_queue.put(event)
        else:
            self._put_result(event)

    def _queue_error(self, source_name: str, message: str):
        self._put_result((source_name, str(message)), final=True)

    def _put_result(self, event, final: bool = False):
        try:
            self._result_queue.put_nowait(event)
        except queue.Full:
            if not final:
                return
            try:
                self._result_queue.get_nowait()
                self._result_queue.put_nowait(event)
            except queue.Empty:
                pass

    def _drain_result_queue(self):
        while True:
            try:
                event = self._result_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, StreamingTranscriptEvent):
                self._handle_partial(event)
            else:
                source_name, message = event
                logger.error("OpenAI Realtime (%s): %s", source_name, message)
        self._drain_completed_queue()

    def _drain_completed_queue(self):
        while True:
            try:
                event = self._completed_queue.get_nowait()
            except queue.Empty:
                return
            self._handle_completed(event)

    def _handle_partial(self, event: StreamingTranscriptEvent):
        key = (event.source, event.item_id)
        if key in self._completed_items or not event.text.strip():
            return
        update_previous = key in self._partial_items
        published = self.conversation.publish_partial(
            persona=event.source,
            text=event.text,
            update_previous=update_previous,
            partial_id=self._partial_id(event.source, event.item_id),
        )
        if published:
            self._partial_items[key] = event.text

    def _handle_completed(self, event: StreamingTranscriptEvent):
        key = (event.source, event.item_id)
        if key in self._completed_items or not event.text.strip():
            return
        self._remember_completed(key)
        replace_ui_partial = self._partial_items.pop(key, None) is not None
        self.conversation.update_conversation(
            persona=event.source,
            text=event.text.strip(),
            time_spoken=event.time_spoken or datetime.datetime.utcnow(),
            replace_ui_partial=replace_ui_partial,
            partial_id=self._partial_id(event.source, event.item_id) if replace_ui_partial else None,
        )
        self.transcript_changed_event.set()

    def _remember_completed(self, key: tuple[str, str]):
        if key in self._completed_items:
            return
        if len(self._completed_item_order) >= self._deduplication_cache_size:
            expired = self._completed_item_order.popleft()
            self._completed_items.discard(expired)
        self._completed_item_order.append(key)
        self._completed_items.add(key)

    @staticmethod
    def _partial_id(source_name: str, item_id: str) -> str:
        return f"{source_name}:{item_id}"

    @staticmethod
    def _drain_queue(target_queue: queue.Queue):
        try:
            while True:
                target_queue.get_nowait()
        except queue.Empty:
            pass
