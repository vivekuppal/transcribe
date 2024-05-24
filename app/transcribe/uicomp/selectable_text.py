from tkinter import Text, Scrollbar, END, SEL_FIRST, SEL_LAST
import customtkinter as ctk


class SelectableText(ctk.CTkFrame):
    """Custom TKinter Component to display multiple lines of text
    and support custom functionality on clicking a line of text.
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.text_widget = Text(self, wrap="word", undo=True, background='#252422')
        self.scrollbar = Scrollbar(self, command=self.text_widget.yview)
        self.text_widget.config(yscrollcommand=self.scrollbar.set)

        self.text_widget.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.text_widget.bind("<Button-1>", self.on_text_click)
        # Handler for left mouse click up
        # self.text_widget.bind("<ButtonRelease-1>", self.on_text_select)
        # Handler for double click
        # self.text_widget.bind("<Double-1>", self.on_double_click)

    def on_text_select(self, event):
        """Handler for left mouse click
        """
        try:
            selected_text = self.text_widget.get(SEL_FIRST, SEL_LAST)
            print(f"Selected text: {selected_text}")

            index = self.text_widget.index("@%s,%s" % (event.x, event.y))
            line_number = int(index.split(".")[0])

            # Get the text of the clicked line
            line_start = f"{line_number}.0"
            line_end = f"{line_number}.end"
            line_text = self.text_widget.get(line_start, line_end).strip()

            # Trigger an event (print the line text)
            print(f"Selected: {line_text}")
        except:
            pass  # No selection

    def on_double_click(self, event):
        """Handler for double click
        """
        index = self.text_widget.index("@%s,%s" % (event.x, event.y))
        line_start = self.text_widget.index("%s linestart" % index)
        line_end = self.text_widget.index("%s lineend" % index)
        self.text_widget.tag_add('SEL', line_start, line_end)
        self.text_widget.mark_set("insert", line_end)
        self.text_widget.see("insert")
        self.text_widget.focus()

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
        self.text_widget.insert(END, input_text + "\n")
        self.text_widget.configure(state="disabled")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = SelectableText()

    # Add a lot of lines of text
    lines_of_text = [f"Line {i}: This is an example of a long line of text that should wrap around the Text widget." for i in range(1, 101)]
    for line in lines_of_text:
        app.add_text_to_bottom(line)

    app.mainloop()
