"""Core conversation state shared across the application."""

from __future__ import annotations

from heapq import merge
import datetime
import threading
from pathlib import Path

from .. import constants
from ..db import AppDB as appdb
from ..db import conversation as convodb
from ..db import llm_responses as llmrdb

from tsutils import configuration


APP_DIR = Path(__file__).resolve().parent.parent


class Conversation:
    """Encapsulates the complete conversation state for the application."""

    def __init__(self, context):
        self.transcript_data = {
            constants.PERSONA_SYSTEM: [],
            constants.PERSONA_YOU: [],
            constants.PERSONA_SPEAKER: [],
            constants.PERSONA_ASSISTANT: [],
        }
        self.last_update: datetime.datetime | None = None
        self.update_handler = None
        self.insert_handler = None
        self.context = context
        self._initialized = False
        self._lock = threading.RLock()
        self.initialize_conversation()

    def set_handlers(self, update, insert):
        """Set callback handlers for update and insert events."""
        with self._lock:
            self.update_handler = update
            self.insert_handler = insert

    def initialize_conversation(self):
        """Populate the initial system prompt and seed conversation."""
        self.config = configuration.Config(
            default_config_filename=str(APP_DIR / "parameters.yaml"),
            override_config_filename=str(APP_DIR / "override.yaml"),
        ).data
        prompt = self.config["General"]["system_prompt"]
        response_lang = self.config["OpenAI"]["response_lang"]
        if response_lang is not None:
            prompt += f".  Respond exclusively in {response_lang}."

        self.update_conversation(
            persona=constants.PERSONA_SYSTEM,
            text=prompt,
            time_spoken=datetime.datetime.utcnow(),
        )
        initial_convo: dict = self.config["General"]["initial_convo"]
        for _, value in initial_convo.items():
            self.update_conversation(
                persona=value["role"],
                text=value["content"],
                time_spoken=datetime.datetime.utcnow(),
            )
        with self._lock:
            self.last_update = datetime.datetime.utcnow()
            self._initialized = True

    def clear_conversation_data(self):
        """Clear all conversation data and restore initial prompts."""
        with self._lock:
            for persona in self.transcript_data:
                self.transcript_data[persona].clear()
            self._initialized = False
        self.initialize_conversation()

    def update_conversation_by_id(self, persona: str, convo_id: int, text: str):
        """Update a single conversation row by its persisted id."""
        with self._lock:
            transcript = self.transcript_data.setdefault(persona, [])
            for index, (_, time_spoken, current_convo_id) in enumerate(transcript):
                if current_convo_id == convo_id:
                    new_convo_text = f"{persona}: [{text}]\n\n"
                    transcript[index] = (new_convo_text, time_spoken, convo_id)
                    break
            else:
                print(f"Conversation with ID {convo_id} not found for persona {persona}.")
                return

            should_update_db = self._initialized

        if should_update_db:
            convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
            convo_object.update_conversation(convo_id, text)

    def update_conversation(
        self,
        persona: str,
        text: str,
        time_spoken,
        update_previous: bool = False,
    ):
        """Insert or update a conversation fragment in memory and the database."""
        callback = None
        callback_args = ()

        with self._lock:
            transcript = self.transcript_data.setdefault(persona, [])
            convo_id = None
            convo_object = None

            if self._initialized:
                inv_id = appdb().get_invocation_id()
                convo_object = appdb().get_object(convodb.TABLE_NAME)
                convo_id = convo_object.get_max_convo_id(speaker=persona, inv_id=inv_id)

            convo_text = f"{persona}: [{text}]\n\n"

            should_update_previous = (
                update_previous
                and (
                    (persona.lower() == "you" and len(transcript) > 1)
                    or (persona.lower() != "you" and len(transcript) > 0)
                )
            )

            if should_update_previous:
                prev_element = transcript.pop()
                time_spoken = prev_element[1]
                if self._initialized and convo_object is not None:
                    convo_object.update_conversation(convo_id, text)
                    if persona.lower() != "assistant" and self.update_handler is not None:
                        callback = self.update_handler
                        ui_text = self._format_display_entry(persona, text, time_spoken, newline_count=1)
                        callback_args = (persona, ui_text)
            else:
                if (
                    self._initialized
                    and persona != constants.PERSONA_SYSTEM
                    and persona != constants.PERSONA_ASSISTANT
                    and convo_object is not None
                ):
                    convo_id = convo_object.insert_conversation(inv_id, time_spoken, persona, text)
                    if self.insert_handler is not None:
                        callback = self.insert_handler
                        ui_text = self._format_display_entry(persona, text, time_spoken, newline_count=1)
                        callback_args = (ui_text,)

            transcript.append((convo_text, time_spoken, convo_id))
            self.last_update = datetime.datetime.utcnow()

        if callback is not None:
            callback(*callback_args)

    def get_convo_id(self, persona: str, input_text: str):
        """Retrieve the persisted id for a conversation row."""
        with self._lock:
            if not self._initialized:
                return None

        cleaned_text = input_text.strip()
        if cleaned_text and cleaned_text[0] == "[":
            cleaned_text = cleaned_text[1:]
        if cleaned_text and cleaned_text[-1] == "]":
            cleaned_text = cleaned_text[:-1]

        inv_id = appdb().get_invocation_id()
        convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
        return convo_object.get_convo_id_by_speaker_and_text(
            speaker=persona,
            input_text=cleaned_text,
            inv_id=inv_id,
        )

    def on_convo_select(self, input_text: str):
        """Callback when a specific conversation row is selected in the UI."""
        end_speaker = input_text.find(":")
        if end_speaker == -1:
            self.context.previous_response = None
            return

        persona = input_text[:end_speaker].strip()
        convo_id = None
        with self._lock:
            transcript = self.transcript_data.get(persona, [])
            for first, _, third in transcript:
                if first.strip() == self._display_text_to_conversation_text(input_text).strip():
                    convo_id = third
                    break

        if not convo_id:
            self.context.previous_response = None
            return

        inv_id = appdb().get_invocation_id()
        llmr_object: llmrdb.LLMResponses = appdb().get_object(llmrdb.TABLE_NAME)
        response = llmr_object.get_text_by_invocation_and_conversation(inv_id, convo_id)
        self.context.previous_response = response if response else "No LLM response corresponding to this row"

    def get_conversation(self, sources: list | None = None, length: int = 0) -> str:
        """Return a merged transcript for the requested personas."""
        return self._get_conversation(sources=sources, length=length, display_timestamps=False)

    def get_display_conversation(self, sources: list | None = None, length: int = 0) -> str:
        """Return a merged transcript formatted for the transcript window."""
        return self._get_conversation(sources=sources, length=length, display_timestamps=True)

    def _get_conversation(
        self,
        sources: list | None = None,
        length: int = 0,
        display_timestamps: bool = False,
    ) -> str:
        """Return a merged transcript for the requested personas."""
        if sources is None:
            sources = [
                constants.PERSONA_YOU,
                constants.PERSONA_SPEAKER,
                constants.PERSONA_ASSISTANT,
                constants.PERSONA_SYSTEM,
            ]

        with self._lock:
            combined_transcript = list(
                merge(
                    *self._transcript_lists_for_sources(sources=sources, length=length),
                    key=lambda x: x[1],
                )
            )
            combined_transcript = combined_transcript[-length:]
            if display_timestamps:
                return "".join(
                    [
                        self._format_display_conversation_text(t[0], t[1])
                        for t in combined_transcript
                    ]
                )
            return "".join([t[0] for t in combined_transcript])

    @classmethod
    def _format_display_entry(
        cls,
        persona: str,
        text: str,
        time_spoken,
        newline_count: int = 2,
    ) -> str:
        """Format one transcript row for the desktop transcript view."""
        return f"{persona}: [{cls._format_timestamp(time_spoken)}] [{text}]" + ("\n" * newline_count)

    @classmethod
    def _format_display_conversation_text(cls, conversation_text: str, time_spoken) -> str:
        """Add a timestamp to a stored conversation row for display."""
        stripped_text = conversation_text.strip()
        speaker_end = stripped_text.find(":")
        if speaker_end == -1:
            return conversation_text

        persona = stripped_text[:speaker_end].strip()
        text = stripped_text[speaker_end + 1 :].strip()
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]

        return cls._format_display_entry(persona, text, time_spoken)

    @staticmethod
    def _format_timestamp(time_spoken) -> str:
        """Format a transcript timestamp in local clock time."""
        if hasattr(time_spoken, "strftime"):
            if time_spoken.tzinfo is None:
                time_spoken = time_spoken.replace(tzinfo=datetime.timezone.utc)
            return time_spoken.astimezone().strftime("%H:%M:%S")
        return str(time_spoken)

    @staticmethod
    def _display_text_to_conversation_text(input_text: str) -> str:
        """Remove a display timestamp from a transcript row."""
        stripped_text = input_text.strip()
        speaker_end = stripped_text.find(":")
        if speaker_end == -1:
            return input_text

        persona = stripped_text[:speaker_end].strip()
        remainder = stripped_text[speaker_end + 1 :].strip()
        if not remainder.startswith("["):
            return input_text

        timestamp_end = remainder.find("]")
        remaining_text = remainder[timestamp_end + 1 :].strip() if timestamp_end != -1 else ""
        timestamp_text = remainder[1:timestamp_end] if timestamp_end != -1 else ""
        if timestamp_end == -1 or not remaining_text.startswith("[") or not Conversation._is_display_timestamp(timestamp_text):
            return input_text

        return f"{persona}: {remaining_text}"

    @staticmethod
    def _is_display_timestamp(value: str) -> bool:
        """Return whether text matches the transcript display timestamp format."""
        parts = value.split(":")
        return len(parts) == 3 and all(part.isdigit() and len(part) == 2 for part in parts)

    def get_merged_conversation_summary(self, length: int = 0) -> list:
        """Return the conversation history formatted for summary prompts."""
        with self._lock:
            combined_transcript = self._flatten_transcript_lists(
                self._transcript_lists_for_sources(
                    sources=[
                        constants.PERSONA_YOU,
                        constants.PERSONA_SPEAKER,
                        constants.PERSONA_ASSISTANT,
                    ],
                    length=length,
                )
            )
            sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
            sorted_transcript = sorted_transcript[-length:]
            sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
            sorted_transcript.insert(
                0,
                (
                    f"{constants.PERSONA_SYSTEM}: [{self.config['General']['summary_prompt']}]\n\n",
                    datetime.datetime.now(),
                    -1,
                ),
            )
            return sorted_transcript

    def get_merged_conversation_response(self, length: int = 0) -> list:
        """Return the conversation history formatted for response prompts."""
        with self._lock:
            combined_transcript = self._flatten_transcript_lists(
                self._transcript_lists_for_sources(
                    sources=[
                        constants.PERSONA_YOU,
                        constants.PERSONA_SPEAKER,
                        constants.PERSONA_ASSISTANT,
                    ],
                    length=length,
                )
            )
            sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
            sorted_transcript = sorted_transcript[-length:]
            sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
            sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_SYSTEM][0])
            return sorted_transcript

    def _pretty_print_transcript(self, message: list):
        """Print a conversation transcript in a human-friendly format."""
        print("[")
        for item in message:
            print("  {")
            print(f"    {item[0].strip()}")
            print(f"    {item[1]}")
            print("  }")
        print("]")

    def _transcript_lists_for_sources(self, sources: list, length: int = 0) -> list[list]:
        """Return transcript lists matching exact or diarized source personas."""
        return [
            transcript[-length:]
            for persona, transcript in self.transcript_data.items()
            if self._persona_matches_sources(persona, sources)
        ]

    @staticmethod
    def _flatten_transcript_lists(transcript_lists: list[list]) -> list:
        """Flatten transcript list groups."""
        return [item for transcript in transcript_lists for item in transcript]

    @staticmethod
    def _persona_matches_sources(persona: str, sources: list) -> bool:
        """Return whether a persona should be included for requested sources."""
        if persona in sources:
            return True
        return any(persona.startswith(f"{source} ") for source in sources)
