"""Desktop service helpers that do not depend on Tk widgets."""

from __future__ import annotations

import datetime
import re
import webbrowser

import pyperclip
from wordcloud import WordCloud

try:
    from .. import constants
except ImportError:
    import constants

from tsutils import configuration, utilities


class ActionLogService:
    """Persist user actions for the current desktop session."""

    def __init__(
        self,
        app_name: str = "Transcribe",
        get_data_path=utilities.get_data_path,
        incrementing_filename=utilities.incrementing_filename,
        open_file=open,
        now_provider=datetime.datetime.now,
    ):
        self.app_name = app_name
        self.get_data_path = get_data_path
        self.incrementing_filename = incrementing_filename
        self.open_file = open_file
        self.now_provider = now_provider
        self.log_filename: str | None = None

    def capture(self, action_text: str):
        """Append a UI action to the session log."""
        if not self.log_filename:
            data_dir = self.get_data_path(app_name=self.app_name)
            self.log_filename = self.incrementing_filename(
                filename=f"{data_dir}/logs/ui",
                extension="txt",
            )

        with self.open_file(self.log_filename, mode="a", encoding="utf-8") as ui_file:
            ui_file.write(f"{self.now_provider()}: {action_text}\n")


class SettingsService:
    """Persist mutable desktop settings and apply them to runtime state."""

    def __init__(self, config_factory=configuration.Config, utcnow_provider=datetime.datetime.utcnow):
        self.config_factory = config_factory
        self.utcnow_provider = utcnow_provider

    def save_llm_response_interval(self, slider_value) -> int:
        """Persist the LLM response interval."""
        interval = int(slider_value)
        config_obj = self.config_factory()
        config_obj.add_override_value({"General": {"llm_response_interval": interval}})
        return interval

    def save_audio_language(self, lang: str, stt_model):
        """Persist the STT language and update the live model."""
        stt_model.set_lang(lang)
        config_obj = self.config_factory()
        config_obj.add_override_value({"OpenAI": {"audio_lang": lang}})

    def build_response_prompt(self, system_prompt: str, response_lang: str | None) -> str:
        """Build the system prompt for the chosen response language."""
        if response_lang is None:
            return system_prompt
        return f"{system_prompt}.  Respond exclusively in {response_lang}."

    def save_response_language(self, lang: str, convo):
        """Persist the response language and update the active system prompt."""
        config_obj = self.config_factory()
        config_obj.add_override_value({"OpenAI": {"response_lang": lang}})
        config_data = config_obj.data

        prompt = self.build_response_prompt(
            system_prompt=config_data["General"]["system_prompt"],
            response_lang=config_data["OpenAI"]["response_lang"],
        )
        convo.update_conversation(
            persona=constants.PERSONA_SYSTEM,
            text=prompt,
            time_spoken=self.utcnow_provider(),
            update_previous=True,
        )


class TranscriptIOService:
    """Handle transcript copy/save actions without depending on Tk."""

    def __init__(self, clipboard_copy=pyperclip.copy, open_file=open):
        self.clipboard_copy = clipboard_copy
        self.open_file = open_file

    def copy_transcript(self, transcript: str):
        """Copy transcript text to the clipboard."""
        self.clipboard_copy(transcript)

    def save_transcript(self, transcript: str, filename: str):
        """Save transcript text to a file."""
        with self.open_file(filename, mode="w", encoding="utf-8") as file_handle:
            file_handle.write(transcript)


class BrowserService:
    """Open external browser links."""

    def __init__(self, browser_open=webbrowser.open):
        self.browser_open = browser_open

    def open_link(self, url: str):
        """Open a URL in the default browser."""
        self.browser_open(url=url, new=2)


class ConversationInsightsService:
    """Create derived desktop artifacts from conversation text."""

    def __init__(self, word_cloud_factory=WordCloud):
        self.word_cloud_factory = word_cloud_factory

    def normalize_word_cloud_text(self, words: str) -> str:
        """Strip persona labels before generating a word cloud."""
        return re.sub(r"^(You|Speaker|assistant):\s*", "", words, flags=re.MULTILINE)

    def build_word_cloud(self, words: str):
        """Create a word cloud from conversation text."""
        processed_text = self.normalize_word_cloud_text(words)
        word_cloud = self.word_cloud_factory(
            background_color="white",
            colormap="binary",
            width=500,
            height=500,
        )
        return word_cloud.generate(processed_text[80:])
