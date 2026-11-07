"""Chunked speech to text for the microphone and the speaker.

How audio moves (each step was a cause of lag before):

* The recorders deliver phrases of up to ``transcript_audio_duration_seconds`` that are
  already 16 kHz mono 16-bit PCM (see ``sdk.audio_format``).
* One dispatcher hands every phrase to its own source worker, so a slow transcription of
  the speaker never holds back the microphone (or the other way round).
* A worker takes everything that is waiting for its source in one go and transcribes it in
  one request. When transcription is slower than speech, audio is merged instead of queueing
  up one request per phrase, so the delay cannot keep growing.
* Audio is passed to the model in memory (``transcribe_pcm``); no temporary WAV per phrase.
* While someone speaks without a pause, the rolling buffer is re-transcribed so earlier words
  can still be corrected. Once the buffer passes ``live_transcription_commit_seconds``, text
  that the model has finished with (segments ending before the mutable tail) is committed:
  that audio leaves the buffer and later passes start a new row. Each request therefore
  stays around ``commit + phrase`` seconds long instead of growing to the 30 second window.
"""

from __future__ import annotations

import datetime
import queue
import threading
import time

from sdk import audio_format
from . import constants, conversation
from .live_transcription import (
    DEFAULT_AUDIO_CONTEXT_SECONDS,
    DEFAULT_WINDOW_SECONDS,
    LiveTranscriptManager,
)
from .transcriber import TranscriberInterface
from tsutils import app_logging as al
from tsutils import duration, language


# pylint: disable=logging-fstring-interpolation
# A gap longer than this between two captured phrases of one source starts a new row.
PHRASE_TIMEOUT = 3.05
DEFAULT_COMMIT_SECONDS = 10.0
# Never cut off less audio than this when committing; tiny cuts are not worth a new row.
MIN_COMMIT_CUT_SECONDS = 1.0
SOURCES = (constants.PERSONA_YOU, constants.PERSONA_SPEAKER)
logger = al.get_module_logger(al.TRANSCRIBER_LOGGER)


class AudioTranscriber(TranscriberInterface):   # pylint: disable=C0115, R0902

    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation,
                 config: dict):
        logger.info(self.__class__.__name__)
        del mic_source, speaker_source     # capture formats no longer matter: audio arrives as 16 kHz mono
        self.transcript_changed_event = threading.Event()
        self.stt_model = model
        self.mutex = threading.Lock()
        self.config = config
        general_config = self.config.get("General", {})
        self.live_transcript_manager = LiveTranscriptManager(config=config)
        self.live_transcription_window_seconds = float(
            general_config.get("live_transcription_window_seconds", DEFAULT_WINDOW_SECONDS)
        )
        self.live_transcription_audio_context_seconds = float(
            general_config.get("live_transcription_audio_context_seconds", DEFAULT_AUDIO_CONTEXT_SECONDS)
        )
        self.commit_seconds = float(
            general_config.get("live_transcription_commit_seconds", DEFAULT_COMMIT_SECONDS)
        )
        self.clear_transcript_periodically: bool = general_config['clear_transcript_periodically']
        self.clear_transcript_interval_seconds: int = general_config['clear_transcript_interval_seconds']
        # Determines if transcription is enabled for the application. By default it is enabled.
        self.transcribe = True
        # Bumped by clear_transcript_data so a request that was running during a clear
        # cannot write old text into the new, empty transcript.
        self._generation = 0
        self.audio_sources_properties = {name: self._new_source_state() for name in SOURCES}
        self._source_queues: dict[str, queue.Queue] = {name: queue.Queue() for name in SOURCES}
        self._workers: dict[str, threading.Thread] = {}
        # Local engines (openai-whisper, SenseVoice, whisper.cpp) must not run two transcriptions at
        # once; network engines and faster-whisper (two workers) can.
        self._model_lock = None if getattr(model, "thread_safe", False) else threading.Lock()
        self.conversation = convo

    def _new_source_state(self) -> dict:
        return {
            "sample_rate": audio_format.TARGET_SAMPLE_RATE,
            "sample_width": audio_format.TARGET_SAMPLE_WIDTH,
            "channels": audio_format.TARGET_CHANNELS,
            "last_sample": bytes(),      # 16 kHz mono PCM of the current row (plus context)
            "buffer_start_seconds": 0.0,
            # UTC time the last captured phrase of this source was queued
            "last_spoken": None,
            # True until the current phrase has produced its own transcript row
            "new_phrase": True,
            # True when audio was added that has not been transcribed yet
            "dirty": False,
            "mutex": self.mutex,
        }

    def set_source_properties(self, mic_source=None, speaker_source=None):
        """Capture formats are normalised by the recorders; nothing to update here."""
        del mic_source, speaker_source

    def set_source_enabled(self, source_name: str, enabled: bool):
        """File/window providers do not own source capture resources."""
        del source_name, enabled

    def set_transcription_enabled(self, enabled: bool):
        """Pause or resume transcription without changing capture resources."""
        self.transcribe = bool(enabled)

    def set_language(self, lang: str):
        """Update the language on the configured file/window STT model.

        The UI and parameters.yaml use names ("English"); every engine wants the code ("en").
        """
        self.stt_model.set_lang(language_code(lang))

    def stop(self):
        """File/window transcribers own no persistent provider resources."""

    # ----------------------------------------------------------------------------------------
    # Threads
    # ----------------------------------------------------------------------------------------
    def transcribe_audio_queue(self, audio_queue: queue.Queue):
        """Dispatch captured phrases to one worker per source (runs forever on its own thread)."""
        logger.info(self.__class__.__name__)
        self._start_workers()
        while True:
            who_spoke, data, time_spoken = audio_queue.get()
            source_queue = self._source_queues.get(who_spoke)
            if source_queue is None:
                logger.warning(f'Audio from unknown source {who_spoke} was ignored')
                continue
            source_queue.put((data, time_spoken))

    def _start_workers(self):
        for name in SOURCES:
            worker = self._workers.get(name)
            if worker is None or not worker.is_alive():
                worker = threading.Thread(target=self._source_worker, args=(name,),
                                          name=f'Transcribe {name}', daemon=True)
                self._workers[name] = worker
                worker.start()

    def _source_worker(self, who_spoke: str):
        source_queue = self._source_queues[who_spoke]
        source_info = self.audio_sources_properties[who_spoke]
        while True:
            try:
                # With audio still untranscribed (the tail after a commit), wait only as long
                # as a phrase may pause; if nothing more comes, finish the phrase now.
                timeout = PHRASE_TIMEOUT if source_info["dirty"] else None
                items = [source_queue.get(timeout=timeout)]
            except queue.Empty:
                self._run_safely(who_spoke)
                continue
            while True:
                try:
                    items.append(source_queue.get_nowait())
                except queue.Empty:
                    break
            generation = self._generation
            for data, time_spoken in items:
                if self._is_new_phrase(source_info, time_spoken) and source_info["dirty"]:
                    # Finish the previous phrase before its audio is replaced by the next one.
                    self._run_safely(who_spoke)
                if generation != self._generation:
                    break           # the transcript was cleared: audio taken before it is dropped
                self._update_last_sample_and_phrase_status(who_spoke, data, time_spoken)
            if source_info["dirty"]:
                self._run_safely(who_spoke)

    def _run_safely(self, who_spoke: str):
        try:
            self._transcribe_source(who_spoke)
        except Exception as exception:  # a worker must never die: the source would go silent
            logger.exception(f'Transcription failed for {who_spoke}: {exception}')
            with self.mutex:
                self.audio_sources_properties[who_spoke]["dirty"] = False

    # ----------------------------------------------------------------------------------------
    # Buffer handling
    # ----------------------------------------------------------------------------------------
    @staticmethod
    def _is_new_phrase(source_info: dict, time_spoken) -> bool:
        last_spoken = source_info["last_spoken"]
        return last_spoken is None or \
            time_spoken - last_spoken > datetime.timedelta(seconds=PHRASE_TIMEOUT)

    def _update_last_sample_and_phrase_status(self, who_spoke, data, time_spoken):
        if not self.transcribe:
            return
        source_info = self.audio_sources_properties[who_spoke]

        with source_info["mutex"]:
            if self._is_new_phrase(source_info, time_spoken):
                source_info["last_sample"] = bytes()
                source_info["buffer_start_seconds"] = 0.0
                source_info["new_phrase"] = True
                self.live_transcript_manager.reset(who_spoke)

            source_info["last_sample"] += data
            source_info["dirty"] = True
            self._trim_audio_buffer_locked(source_info)
            source_info["last_spoken"] = time_spoken

    def _trim_audio_buffer_locked(self, source_info: dict):
        """Hard cap for providers without timestamps: keep only the rolling window."""
        bytes_per_second = self._bytes_per_second(source_info)
        if bytes_per_second <= 0:
            return

        frame_size = self._frame_size(source_info)
        max_bytes = int(self.live_transcription_window_seconds * bytes_per_second)
        max_bytes -= max_bytes % frame_size
        if max_bytes <= 0 or len(source_info["last_sample"]) <= max_bytes:
            return

        trim_bytes = len(source_info["last_sample"]) - max_bytes
        trim_bytes -= trim_bytes % frame_size
        if trim_bytes <= 0:
            return

        source_info["last_sample"] = source_info["last_sample"][trim_bytes:]
        source_info["buffer_start_seconds"] += trim_bytes / bytes_per_second

    def _get_audio_window_seconds(self, source_info: dict) -> tuple[float, float]:
        """Return the retained audio window boundaries in source-relative seconds."""
        with source_info["mutex"]:
            start_seconds = float(source_info.get("buffer_start_seconds", 0.0))
            duration_seconds = self._audio_duration_seconds(source_info)
            return start_seconds, start_seconds + duration_seconds

    def _audio_duration_seconds(self, source_info: dict) -> float:
        bytes_per_second = self._bytes_per_second(source_info)
        if bytes_per_second <= 0:
            return 0.0
        return len(source_info["last_sample"]) / bytes_per_second

    @staticmethod
    def _frame_size(source_info: dict) -> int:
        return max(int(source_info.get("sample_width", 2)) * int(source_info.get("channels", 1)), 1)

    @classmethod
    def _bytes_per_second(cls, source_info: dict) -> int:
        return max(cls._frame_size(source_info) * int(source_info.get("sample_rate", 0)), 0)

    # ----------------------------------------------------------------------------------------
    # Transcription
    # ----------------------------------------------------------------------------------------
    def _transcribe_source(self, who_spoke: str):
        source_info = self.audio_sources_properties[who_spoke]
        with source_info["mutex"]:
            source_info["dirty"] = False
            pcm = source_info["last_sample"]
            audio_start_seconds = float(source_info["buffer_start_seconds"])
            audio_end_seconds = audio_start_seconds + self._audio_duration_seconds(source_info)
            new_phrase = source_info["new_phrase"]
            time_spoken = source_info["last_spoken"]
            generation = self._generation
        if not self.transcribe or not pcm:
            return

        with duration.Duration(f'Transcription (Speech to Text) {who_spoke}', screen=False):
            if self._model_lock is None:
                response = self.stt_model.transcribe_pcm(pcm, audio_format.TARGET_SAMPLE_RATE)
            else:
                with self._model_lock:
                    response = self.stt_model.transcribe_pcm(pcm, audio_format.TARGET_SAMPLE_RATE)
            raw_text = self.stt_model.process_response(response) if response else ''
        if not raw_text:
            return

        hypothesis = self.stt_model.normalize_response(
            response,
            audio_start_seconds=audio_start_seconds,
            audio_end_seconds=audio_end_seconds,
        )
        with self.mutex:
            if generation != self._generation:
                return              # the transcript was cleared while this request ran
            live_update = self.live_transcript_manager.process_hypothesis(
                speaker=who_spoke,
                hypothesis=hypothesis,
                new_phrase=new_phrase,
            )
            text = live_update.text if live_update.changed else ''
            if text and text.lower() != 'you':
                # Written while holding the lock, so a clear cannot slip in between the check above
                # and the write (the conversation never waits for this lock: no deadlock).
                self.update_transcript(who_spoke, text, time_spoken,
                                       update_previous=live_update.update_previous)
                source_info["new_phrase"] = False
                self.transcript_changed_event.set()
        logger.info(f'{who_spoke}: transcribed {audio_end_seconds - audio_start_seconds:.1f}s -> {text}')

        self._maybe_commit(who_spoke, hypothesis, audio_start_seconds,
                           audio_end_seconds - audio_start_seconds, time_spoken, generation)

    def _maybe_commit(self, who_spoke: str, hypothesis, audio_start_seconds: float,
                      audio_seconds: float, time_spoken, generation: int):
        """Move finished text out of the rolling buffer once it is long enough."""
        if self.commit_seconds <= 0 or audio_seconds < self.commit_seconds:
            return
        source_info = self.audio_sources_properties[who_spoke]
        cutoff = hypothesis.audio_end_seconds - self.live_transcript_manager.mutable_tail_seconds
        segments = [segment for segment in hypothesis.segments if segment.text]
        final = [segment for segment in segments if segment.end_seconds <= cutoff]
        if not final:
            return                  # no timestamps, or nothing settled yet: the window cap applies
        cut_seconds = final[-1].end_seconds - audio_start_seconds
        if cut_seconds < MIN_COMMIT_CUT_SECONDS:
            return
        tail_text = " ".join(segment.text for segment in segments[len(final):])

        with self.mutex:
            if generation != self._generation or source_info["new_phrase"]:
                return              # cleared, or the hypothesis never reached the transcript
            committed_text = self.live_transcript_manager.commit(who_spoke, tail_text)
            if committed_text is None:
                return              # the row does not end with the open tail; try next pass
            cut_bytes = int(cut_seconds * self._bytes_per_second(source_info))
            cut_bytes -= cut_bytes % self._frame_size(source_info)
            cut_bytes = min(cut_bytes, len(source_info["last_sample"]))
            source_info["last_sample"] = source_info["last_sample"][cut_bytes:]
            source_info["buffer_start_seconds"] += cut_bytes / self._bytes_per_second(source_info)
            source_info["new_phrase"] = True
            # The open tail is no longer in any row: transcribe it with the next audio, or
            # on its own if the speaker stops here.
            source_info["dirty"] = bool(source_info["last_sample"])
            self.update_transcript(who_spoke, committed_text, time_spoken, update_previous=True)
        logger.info(f'{who_spoke}: committed {cut_seconds:.1f}s of audio')

    def update_transcript(self, who_spoke, text, time_spoken, update_previous=None):
        """Update transcript with new data
        Args:
        who_spoke: Person this audio is attributed to
        text: Actual spoken words
        time_spoken: Time at which audio was taken, relative to start time
        """
        source_info = self.audio_sources_properties[who_spoke]
        if update_previous is None:
            update_previous = not source_info["new_phrase"]
        self.conversation.update_conversation(persona=who_spoke,
                                              time_spoken=time_spoken or datetime.datetime.utcnow(),
                                              text=text,
                                              update_previous=bool(update_previous))

    def get_transcript(self, length: int = 0):
        """Get the audio transcript
        Args:
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript
        """
        return self.conversation.get_conversation(sources=list(SOURCES), length=length)

    def clear_transcript_data_loop(self, audio_queue: queue.Queue):
        """Clear transcript data at a specified interval if needed.
        Args:
          audio_queue: queue object with reference to audio files
        """
        while True:
            if self.clear_transcript_periodically:
                self.clear_transcriber_context(audio_queue=audio_queue)
            time.sleep(self.clear_transcript_interval_seconds)

    def clear_transcriber_context(self, audio_queue: queue.Queue):
        """Reset the transcriber and drop audio that has not been transcribed yet."""
        logger.info(AudioTranscriber.clear_transcriber_context.__name__)
        for pending in [audio_queue, *self._source_queues.values()]:
            with pending.mutex:
                pending.queue.clear()
        self.clear_transcript_data()

    def clear_transcript_data(self):
        """Clears all internal data associated with the transcript
        """
        with self.mutex:
            self._generation += 1
            for source_info in self.audio_sources_properties.values():
                source_info["last_sample"] = bytes()
                source_info["buffer_start_seconds"] = 0.0
                source_info["new_phrase"] = True
                source_info["dirty"] = False
            self.live_transcript_manager.clear()

        self.conversation.clear_conversation_data()


def language_code(lang: str) -> str:
    """'English' / 'english' / 'en' -> 'en' (unknown names are passed on unchanged)."""
    value = str(lang or "").strip()
    lowered = value.lower()
    if lowered in language.LANGUAGES_DICT:
        return lowered
    for code, name in language.LANGUAGES_DICT.items():
        if name == lowered:
            return code
    return value


class WhisperTranscriber(AudioTranscriber):
    """Transcriber for local Whisper and the OpenAI-compatible Whisper API."""


class WhisperCPPTranscriber(AudioTranscriber):
    """Transcriber for whisper.cpp (audio already arrives in its 16 kHz mono format)."""


class DeepgramTranscriber(AudioTranscriber):
    """Transcriber for Deepgram pre-recorded transcription."""

