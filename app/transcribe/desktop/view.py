"""Desktop view-building helpers for the main application window."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

try:
    from .. import prompts
    from ..uicomp.selectable_text import SelectableText
except ImportError:
    import prompts
    from uicomp.selectable_text import SelectableText

from tsutils.language import LANGUAGES_DICT


class DesktopViewBuilder:
    """Build the desktop window layout and widgets."""

    def build(self, ui, config: dict):
        """Create all widgets required by the desktop window."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ui.title("Transcribe")
        ui.configure(bg="#252422")
        ui.geometry("1200x800")

        ui.main_frame = ctk.CTkFrame(ui)
        ui.main_frame.pack(fill="both", expand=True)

        self.create_menus(ui)
        self.create_transcript_panel(ui)
        self.create_response_panel(ui)
        self.create_bottom_controls(ui, config)

    def create_menus(self, ui):
        """Create the window menu shells without binding commands."""
        ui.menubar = tk.Menu(ui)
        ui.filemenu = tk.Menu(ui.menubar, tearoff=False)
        ui.editmenu = tk.Menu(ui.menubar, tearoff=False)
        ui.helpmenu = tk.Menu(ui.menubar, tearoff=False)

        ui.menubar.add_cascade(label="File", menu=ui.filemenu)
        ui.menubar.add_cascade(label="Edit", menu=ui.editmenu)
        ui.menubar.add_cascade(label="Help", menu=ui.helpmenu)
        ui.config(menu=ui.menubar)

    def create_transcript_panel(self, ui):
        """Create the transcript panel."""
        ui.transcript_text = SelectableText(ui.main_frame)
        ui.transcript_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ui.transcript_text.set_callbacks(ui.global_vars.convo.on_convo_select)

    def create_response_panel(self, ui):
        """Create the response panel."""
        ui.right_frame = ctk.CTkFrame(ui.main_frame)
        ui.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ui.min_response_textbox_width = 300
        ui.response_textbox = ctk.CTkTextbox(
            ui.right_frame,
            ui.min_response_textbox_width,
            font=("Arial", ui.ui_font_size),
            text_color="#639cdc",
            wrap="word",
        )
        ui.response_textbox.pack(fill="both", expand=True)
        ui.response_textbox.insert("0.0", prompts.INITIAL_RESPONSE)

    def create_bottom_controls(self, ui, config: dict):
        """Create the bottom control strip and widgets."""
        ui.bottom_frame = ctk.CTkFrame(ui, border_color="white", border_width=2)
        ui.bottom_frame.pack(side="bottom", fill="both", pady=10)

        response_enabled = bool(config["General"]["continuous_response"])
        button_text = (
            "Suggest Responses Continuously"
            if not response_enabled
            else "Do Not Suggest Responses Continuously"
        )
        ui.continuous_response_button = ctk.CTkButton(ui.bottom_frame, text=button_text)
        ui.continuous_response_button.grid(row=0, column=4, padx=10, pady=3, sticky="nsew")

        ui.response_now_button = ctk.CTkButton(ui.bottom_frame, text="Suggest Response Now")
        ui.response_now_button.grid(row=1, column=4, padx=10, pady=3, sticky="nsew")

        ui.read_response_now_button = ctk.CTkButton(ui.bottom_frame, text="Suggest Response and Read")
        ui.read_response_now_button.grid(row=2, column=4, padx=10, pady=3, sticky="nsew")

        ui.summarize_button = ctk.CTkButton(ui.bottom_frame, text="Summarize")
        ui.summarize_button.grid(row=3, column=4, padx=10, pady=3, sticky="nsew")

        ui.word_cloud_button = ctk.CTkButton(ui.bottom_frame, text="Display Word Cloud")
        ui.word_cloud_button.grid(row=4, column=4, padx=10, pady=3, sticky="nsew")

        ui.update_interval_slider_label = ctk.CTkLabel(
            ui.bottom_frame,
            text="",
            font=("Arial", 12),
            text_color="#FFFCF2",
        )
        ui.update_interval_slider_label.grid(row=0, column=0, columnspan=4, padx=10, pady=3, sticky="nsew")

        ui.update_interval_slider = ctk.CTkSlider(
            ui.bottom_frame,
            from_=1,
            to=30,
            width=300,
            number_of_steps=29,
        )
        ui.update_interval_slider.set(config["General"]["llm_response_interval"])
        ui.update_interval_slider.grid(row=1, column=0, columnspan=4, padx=10, pady=3, sticky="nsew")

        label_text = f"LLM Response interval: {int(ui.update_interval_slider.get())} seconds"
        ui.update_interval_slider_label.configure(text=label_text)

        audio_lang_label = ctk.CTkLabel(
            ui.bottom_frame,
            text="Audio Lang: ",
            font=("Arial", 12),
            text_color="#FFFCF2",
        )
        audio_lang_label.grid(row=2, column=0, padx=10, pady=3, sticky="nw")

        ui.audio_lang_combobox = ctk.CTkOptionMenu(
            ui.bottom_frame,
            width=15,
            values=list(LANGUAGES_DICT.values()),
        )
        ui.audio_lang_combobox.set(config["OpenAI"]["audio_lang"])
        ui.audio_lang_combobox.grid(row=2, column=1, ipadx=60, padx=10, pady=3, sticky="ne")

        response_lang_label = ctk.CTkLabel(
            ui.bottom_frame,
            text="Response Lang: ",
            font=("Arial", 12),
            text_color="#FFFCF2",
        )
        response_lang_label.grid(row=2, column=2, padx=10, pady=3, sticky="nw")

        ui.response_lang_combobox = ctk.CTkOptionMenu(
            ui.bottom_frame,
            width=15,
            values=list(LANGUAGES_DICT.values()),
        )
        ui.response_lang_combobox.set(config["OpenAI"]["response_lang"])
        ui.response_lang_combobox.grid(row=2, column=3, ipadx=60, padx=10, pady=3, sticky="ne")

        ui.github_link = ctk.CTkLabel(
            ui.bottom_frame,
            text="Star the Github Repo",
            text_color="#639cdc",
            cursor="hand2",
        )
        ui.github_link.grid(row=3, column=0, padx=10, pady=3, sticky="wn")

        ui.issue_link = ctk.CTkLabel(
            ui.bottom_frame,
            text="Report an issue",
            text_color="#639cdc",
            cursor="hand2",
        )
        ui.issue_link.grid(row=3, column=1, padx=10, pady=3, sticky="wn")
