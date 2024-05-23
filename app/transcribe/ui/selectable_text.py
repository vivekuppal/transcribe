from tkinter import Text
import customtkinter as ctk


class SelectableText(ctk.CTk):
    """
    A CustomTkinter application that displays a lot of lines of text,
    where each line can wrap and is selectable to trigger an event on selection.
    """
    def __init__(self, title: str, geometry: str):
        """
        Initialize the SelectableText application.
        """
        super().__init__()

        self.title(title)
        self.geometry(geometry)

        # Create a frame to hold the Text widget and the scrollbar
        self.text_frame = ctk.CTkFrame(self)
        self.text_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Create a Text widget
        self.text_widget = Text(self.text_frame, wrap="word",
                                bg=ctk.ThemeManager.theme['CTkFrame']['fg_color'][1],
                                fg="white")
        self.text_widget.pack(side="left", fill="both", expand=True)

        # Create a Scrollbar and attach it to the Text widget
        self.scrollbar = ctk.CTkScrollbar(self.text_frame, command=self.text_widget.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.config(yscrollcommand=self.scrollbar.set)

        # Bind click event to the Text widget
        self.text_widget.bind("<Button-1>", self.on_text_click)

        # Make the Text widget read-only
        self.text_widget.configure(state="disabled")

        # Create a frame for the buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=20, pady=10)

        # Create buttons to scroll to the top and bottom
        self.scroll_top_button = ctk.CTkButton(self.button_frame,
                                               text="Scroll to Top",
                                               command=self.scroll_to_top)
        self.scroll_top_button.pack(side="left", padx=10)

        self.scroll_bottom_button = ctk.CTkButton(self.button_frame,
                                                  text="Scroll to Bottom",
                                                  command=self.scroll_to_bottom)
        self.scroll_bottom_button.pack(side="left", padx=10)

        # Create buttons to add text to the top and bottom
        self.add_top_button = ctk.CTkButton(self.button_frame,
                                            text="Add Text to Top",
                                            command=self.add_text_to_top)
        self.add_top_button.pack(side="left", padx=10)

        self.add_bottom_button = ctk.CTkButton(self.button_frame,
                                               text="Add Text to Bottom",
                                               command=self.add_text_to_bottom)
        self.add_bottom_button.pack(side="left", padx=10)

    def on_text_click(self, event):
        """
        Handle the click event on the Text widget.

        Args:
            event (tkinter.Event): The event object containing event details.
        """
        # Get the index of the clicked line
        index = self.text_widget.index("@%s,%s" % (event.x, event.y))
        line_number = int(index.split(".")[0])

        # Get the text of the clicked line
        line_start = f"{line_number}.0"
        line_end = f"{line_number}.end"
        line_text = self.text_widget.get(line_start, line_end).strip()

        # Trigger an event (print the line text)
        print(f"Selected: {line_text}")

    def scroll_to_top(self):
        """
        Scroll the Text widget to the top.
        """
        self.text_widget.yview_moveto(0)

    def scroll_to_bottom(self):
        """
        Scroll the Text widget to the bottom.
        """
        self.text_widget.yview_moveto(1)

    def add_text_to_top(self, input_text: str):
        """
        Add text to the top of the Text widget.
        """
        self.text_widget.configure(state="normal")
        self.text_widget.insert("1.0", input_text + "\n")
        self.text_widget.configure(state="disabled")

    def add_text_to_bottom(self, input_text: str):
        """
        Add text to the bottom of the Text widget.
        """
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", input_text + "\n")
        self.text_widget.configure(state="disabled")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = SelectableText('Simple Selectable text example', '600x400')

    # Add a lot of lines of text
    lines_of_text = [f"Line {i}: This is an example of a long line of text that should wrap around the Text widget." for i in range(1, 101)]
    for line in lines_of_text:
        app.add_text_to_bottom(line)

    app.mainloop()
