"""Desktop display helpers for transcript, popup, and edit interactions."""

from __future__ import annotations

import datetime
import tkinter as tk
from io import BytesIO

import customtkinter as ctk
import pyperclip
from PIL import Image, ImageTk


class DesktopDisplayManager:
    """Encapsulate widget-facing display updates for the desktop UI."""

    def __init__(self, ui_font_size: int = 20):
        self.ui = None
        self.ui_font_size = ui_font_size
        self.popup_window = None
        self.last_transcript_ui_update_time: datetime.datetime | None = None

    def bind_ui(self, ui):
        """Attach the active UI instance."""
        self.ui = ui

    def update_initial_transcripts(self, runtime):
        """Populate the initial transcript and start polling the response view."""
        self.update_transcript_ui(runtime.transcriber, self.ui.transcript_text, runtime)
        self.update_response_ui(
            runtime.responder,
            self.ui.response_textbox,
            self.ui.update_interval_slider_label,
            self.ui.update_interval_slider,
            runtime,
        )
        runtime.convo.set_handlers(self.queue_update_last_row, self.queue_add_transcript_line)

    def update_last_row(self, speaker: str, input_text: str):
        """Replace the latest transcript row for a speaker."""
        self.ui.transcript_text.delete_row_starting_with(start_text=speaker)
        self.ui.transcript_text.replace_multiple_newlines()
        self.ui.transcript_text.add_text_to_bottom("\n")
        self.ui.transcript_text.add_text_to_bottom(input_text)
        self.ui.transcript_text.scroll_to_bottom()

    def queue_update_last_row(self, speaker: str, input_text: str):
        """Queue transcript row replacement on the Tk thread."""
        self.ui.enqueue_ui_action(self.update_last_row, speaker, input_text)

    def queue_add_transcript_line(self, input_text: str):
        """Queue transcript insertion on the Tk thread."""
        self.ui.enqueue_ui_action(self.ui.transcript_text.add_text_to_bottom, input_text)

    def write_response_text(self, response_string: str):
        """Render a response string into the response textbox."""
        self.ui.response_textbox.configure(state="normal")
        if response_string:
            self.write_in_textbox(self.ui.response_textbox, response_string)
        self.ui.response_textbox.configure(state="disabled")
        self.ui.response_textbox.see("end")

    def close_popup(self):
        """Close the active popup, if present."""
        if self.popup_window is None:
            return

        try:
            self.popup_window.destroy()
        finally:
            self.popup_window = None

    def show_loading_popup(self, title: str, msg: str):
        """Create a temporary loading popup."""
        self.close_popup()
        popup = ctk.CTkToplevel(self.ui)
        popup.geometry("220x80")
        popup.title(title)
        label = ctk.CTkLabel(popup, text=msg, font=("Arial", 12), text_color="#FFFCF2")
        label.pack(side="top", fill="x", pady=10, padx=10)
        popup.lift()
        self.popup_window = popup

    def show_message_popup(self, title: str, msg: str):
        """Create a text popup with copy and close actions."""
        self.close_popup()
        popup = ctk.CTkToplevel(self.ui)
        popup.geometry("380x710")
        popup.title(title)
        txtbox = ctk.CTkTextbox(
            popup,
            width=350,
            height=600,
            font=("Arial", self.ui_font_size),
            text_color="#FFFCF2",
            wrap="word",
        )
        txtbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        txtbox.insert("0.0", msg)

        def copy_summary_to_clipboard():
            pyperclip.copy(txtbox.get("0.0", "end-1c"))

        copy_button = ctk.CTkButton(popup, text="Copy to Clipboard", command=copy_summary_to_clipboard)
        copy_button.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        close_button = ctk.CTkButton(popup, text="Close", command=self.close_popup)
        close_button.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        popup.lift()
        self.popup_window = popup

    def show_word_cloud_popup(self, title: str, word_cloud):
        """Create a word-cloud popup."""
        self.close_popup()
        popup = ctk.CTkToplevel(self.ui)
        popup.geometry("380x400")
        popup.title(title)

        buffer = BytesIO()
        word_cloud.to_image().save(buffer, format="PNG")
        buffer.seek(0)
        img = Image.open(buffer)
        img_tk = ImageTk.PhotoImage(img)

        word_cloud_label = ctk.CTkLabel(popup, image=img_tk, text="")
        word_cloud_label.image = img_tk
        word_cloud_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        close_button = ctk.CTkButton(popup, text="Close", command=self.close_popup)
        close_button.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        popup.lift()
        self.popup_window = popup

    def edit_current_line(self, runtime):
        """Open an editor for the current transcript line."""
        current_line = self.ui.transcript_text.text_widget.index("insert linestart")
        current_line_text = self.ui.transcript_text.text_widget.get(current_line, f"{current_line} lineend")
        end_speaker = current_line_text.find(":")
        if end_speaker == -1:
            return

        speaker = current_line_text[:end_speaker].strip()
        speaker_text = current_line_text[end_speaker + 1 :].strip().strip("[]")

        edit_window = tk.Toplevel(self.ui)
        edit_window.title("Edit Line")
        edit_window.configure(background="#252422")

        edit_text = tk.Text(
            edit_window,
            wrap="word",
            height=10,
            width=50,
            bg="#252422",
            font=("Arial", 20),
            foreground="#639cdc",
        )
        edit_text.pack(expand=True, fill="both")
        edit_text.insert(tk.END, speaker_text)

        def save_edit():
            new_text = edit_text.get("1.0", tk.END).strip()
            text_widget = self.ui.transcript_text.text_widget
            text_widget.configure(state="normal")
            text_widget.delete(current_line, f"{current_line} lineend")
            text_widget.insert(current_line, f"{speaker}: {new_text}")
            text_widget.configure(state="disabled")

            convo_id = runtime.convo.get_convo_id(persona=speaker, input_text=speaker_text)
            runtime.convo.update_conversation_by_id(persona=speaker, convo_id=convo_id, text=new_text)
            edit_window.destroy()

        ctk.CTkButton(edit_window, text="Save", command=save_edit).pack(side=ctk.LEFT, padx=10, pady=10)
        ctk.CTkButton(edit_window, text="Cancel", command=edit_window.destroy).pack(
            side=ctk.RIGHT,
            padx=10,
            pady=10,
        )

    def update_transcript_ui(self, transcriber, textbox, runtime):
        """Refresh the transcript textbox if conversation state changed."""
        if (
            self.last_transcript_ui_update_time is None
            or self.last_transcript_ui_update_time < runtime.convo.last_update
        ):
            transcript_strings = transcriber.get_transcript()
            if isinstance(transcript_strings, list):
                for line in transcript_strings:
                    textbox.add_text_to_bottom(line)
            else:
                textbox.add_text_to_bottom(transcript_strings)
            textbox.scroll_to_bottom()
            self.last_transcript_ui_update_time = datetime.datetime.utcnow()

    def update_response_ui(self, responder, textbox, update_interval_slider_label, update_interval_slider, runtime):
        """Refresh the response textbox and reschedule polling."""
        response = None

        if runtime.responder.enabled or runtime.update_response_now:
            response = responder.response

        if runtime.previous_response is not None:
            response = runtime.previous_response

        if response:
            textbox.configure(state="normal")
            self.write_in_textbox(textbox, response)
            textbox.configure(state="disabled")
            textbox.see("end")

        update_interval = int(update_interval_slider.get())
        responder.update_response_interval(update_interval)
        update_interval_slider_label.configure(text=f"LLM Response interval: {update_interval} seconds")

        textbox.after(
            300,
            self.update_response_ui,
            responder,
            textbox,
            update_interval_slider_label,
            update_interval_slider,
            runtime,
        )

    @staticmethod
    def write_in_textbox(textbox, text: str):
        """Update a textbox while preserving current selection."""
        selected_ranges = textbox.tag_ranges("sel")
        textbox.delete("0.0", "end")
        textbox.insert("0.0", text)
        if len(selected_ranges):
            textbox.tag_add("sel", selected_ranges[0], selected_ranges[1])
