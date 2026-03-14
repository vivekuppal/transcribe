"""Desktop command and event binding helpers."""

from __future__ import annotations

from tktooltip import ToolTip

from tsutils import utilities


class DesktopCommandBinder:
    """Bind menu items, widget commands, and availability state."""

    def __init__(self, api_key_validator=utilities.is_api_key_valid, tooltip_factory=ToolTip):
        self.api_key_validator = api_key_validator
        self.tooltip_factory = tooltip_factory

    def bind(self, ui, config: dict):
        """Bind all commands and availability checks for the main window."""
        self.bind_buttons(ui)
        self.bind_menus(ui)
        self.bind_links(ui)
        self.bind_context_menu(ui)
        self.apply_backend_availability(ui, config)

    def bind_buttons(self, ui):
        """Bind button and selection widget callbacks."""
        ui.continuous_response_button.configure(command=ui.freeze_unfreeze)
        ui.response_now_button.configure(command=ui.get_response_now)
        ui.read_response_now_button.configure(command=ui.update_response_ui_and_read_now)
        ui.summarize_button.configure(command=ui.summarize)
        ui.word_cloud_button.configure(command=ui.word_cloud)
        ui.update_interval_slider.configure(command=ui.update_interval_slider_value)
        ui.audio_lang_combobox.configure(command=ui.set_audio_language)
        ui.response_lang_combobox.configure(command=ui.set_response_language)

    def bind_menus(self, ui):
        """Populate and bind the menu commands."""
        ui.filemenu.add_command(label="Save Transcript to File", command=ui.save_file)
        ui.filemenu.add_command(label="Pause Transcription", command=ui.set_transcript_state)
        ui.filemenu.add_command(label="Quit", command=ui.quit)

        ui.editmenu.add_command(label="Clear Audio Transcript", command=ui.clear_transcript)
        ui.editmenu.add_command(label="Copy Transcript to Clipboard", command=ui.copy_to_clipboard)
        ui.editmenu.add_command(label="Disable Speaker", command=ui.enable_disable_speaker)
        ui.editmenu.add_command(label="Disable Microphone", command=ui.enable_disable_microphone)

        ui.helpmenu.add_command(label="Github Repo", command=ui.open_github)
        ui.helpmenu.add_command(label="Star the Github repo", command=ui.open_github)
        ui.helpmenu.add_command(label="Report an Issue", command=ui.open_support)

    def bind_links(self, ui):
        """Bind clickable label links."""
        ui.github_link.bind(
            "<Button-1>",
            lambda event: ui.open_link("https://github.com/vivekuppal/transcribe?referer=desktop"),
        )
        ui.issue_link.bind(
            "<Button-1>",
            lambda event: ui.open_link(
                "https://github.com/vivekuppal/transcribe/issues/new?referer=desktop"
            ),
        )

    def bind_context_menu(self, ui):
        """Populate transcript context-menu actions."""
        ui.transcript_text.add_right_click_menu(
            label="Generate response for selected text",
            command=ui.get_response_selected_now,
        )
        ui.transcript_text.add_right_click_menu(label="Save Transcript to File", command=ui.save_file)
        ui.transcript_text.add_right_click_menu(label="Clear Audio Transcript", command=ui.clear_transcript)
        ui.transcript_text.add_right_click_menu(
            label="Copy Transcript to Clipboard",
            command=ui.copy_to_clipboard,
        )
        ui.transcript_text.add_right_click_menu(label="Edit line", command=ui.edit_current_line)
        ui.transcript_text.add_right_menu_separator()
        ui.transcript_text.add_right_click_menu(label="Quit", command=ui.quit)

    def get_provider_settings(self, config: dict):
        """Return API settings for the configured chat provider."""
        provider = config["General"]["chat_inference_provider"]
        if provider == "openai":
            return (
                config["OpenAI"]["api_key"],
                config["OpenAI"]["base_url"],
                config["OpenAI"]["ai_model"],
            )
        if provider == "together":
            return (
                config["Together"]["api_key"],
                config["Together"]["base_url"],
                config["Together"]["ai_model"],
            )
        return None

    def apply_backend_availability(self, ui, config: dict):
        """Disable backend-dependent actions when API access is unavailable."""
        provider_settings = self.get_provider_settings(config)
        if provider_settings is None:
            return

        api_key, base_url, model = provider_settings
        if self.api_key_validator(api_key=api_key, base_url=base_url, model=model):
            return

        self.disable_backend_buttons(ui)

    def disable_backend_buttons(self, ui):
        """Disable controls that depend on backend connectivity."""
        disabled_buttons = [
            ui.continuous_response_button,
            ui.response_now_button,
            ui.read_response_now_button,
            ui.summarize_button,
        ]
        for button in disabled_buttons:
            button.configure(state="disabled")

        tooltip_message = "Add API Key in override.yaml to enable button"
        for button in disabled_buttons:
            self.tooltip_factory(
                button,
                msg=tooltip_message,
                delay=0.01,
                follow=True,
                parent_kwargs={"padx": 3, "pady": 3},
                padx=7,
                pady=7,
            )
