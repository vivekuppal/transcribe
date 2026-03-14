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
            transcript = self.transcript_data[persona]
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
            transcript = self.transcript_data[persona]
            convo_id = None
            convo_object = None

            if self._initialized:
                inv_id = appdb().get_invocation_id()
                convo_object = appdb().get_object(convodb.TABLE_NAME)
                convo_id = convo_object.get_max_convo_id(speaker=persona, inv_id=inv_id)

            convo_text = f"{persona}: [{text}]\n\n"
            ui_text = f"{persona}: [{text}]\n"

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
            transcript = self.transcript_data[persona]
            for first, _, third in transcript:
                if first.strip() == input_text.strip():
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
                    self.transcript_data[constants.PERSONA_YOU][-length:]
                    if constants.PERSONA_YOU in sources
                    else [],
                    self.transcript_data[constants.PERSONA_SPEAKER][-length:]
                    if constants.PERSONA_SPEAKER in sources
                    else [],
                    self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
                    if constants.PERSONA_ASSISTANT in sources
                    else [],
                    self.transcript_data[constants.PERSONA_SYSTEM][-length:]
                    if constants.PERSONA_SYSTEM in sources
                    else [],
                    key=lambda x: x[1],
                )
            )
            combined_transcript = combined_transcript[-length:]
            return "".join([t[0] for t in combined_transcript])

    def get_merged_conversation_summary(self, length: int = 0) -> list:
        """Return the conversation history formatted for summary prompts."""
        with self._lock:
            combined_transcript = (
                self.transcript_data[constants.PERSONA_YOU][-length:]
                + self.transcript_data[constants.PERSONA_SPEAKER][-length:]
                + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
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
            combined_transcript = (
                self.transcript_data[constants.PERSONA_YOU][-length:]
                + self.transcript_data[constants.PERSONA_SPEAKER][-length:]
                + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
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
