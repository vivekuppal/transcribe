from tkinter import Text, Scrollbar, END, SEL_FIRST, SEL_LAST
import customtkinter as ctk


class SelectableText(ctk.CTkFrame):
    """Custom TKinter Component to display multiple lines of text
    and support custom functionality on clicking a line of text.
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.text_widget = Text(self, wrap="word", undo=True,
                                background='#252422', font=("Arial", 20),
                                foreground='#639cdc',)
        self.scrollbar = Scrollbar(self, command=self.text_widget.yview)
        self.text_widget.config(yscrollcommand=self.scrollbar.set)

        self.text_widget.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.text_widget.bind("<Button-1>", self.on_text_click)
        # Handler for left mouse click up
        # self.text_widget.bind("<ButtonRelease-1>", self.on_text_select)
        # Handler for double click
        # self.text_widget.bind("<Double-1>", self.on_double_click)

        # Define the tag for highlighting
        self.text_widget.tag_configure("highlight", background="white")
        self.on_text_click_cb = None

    def set_callbacks(self, onTextClick):
        """Set callback handlers
        """
        self.on_text_click_cb = onTextClick

    def clear_all_text(self):
        """Clear all text from the component
        """
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", END)
        self.text_widget.configure(state="disabled")

    def on_text_click(self, event):
        """Handle the click event on the Text widget."""
        # Remove the previous highlight
        self.text_widget.tag_remove("highlight", "1.0", END)

        # Get the index of the clicked line
        index = self.text_widget.index("@%s,%s" % (event.x, event.y))
        line_number = int(index.split(".")[0])

        # Get the text of the clicked line
        line_start = f"{line_number}.0"
        line_end = f"{line_number}.end"
        line_text = self.text_widget.get(line_start, line_end).strip()

        # Add the highlight tag to the clicked line
        self.text_widget.tag_add("highlight", line_start, line_end)
        self.on_text_click_cb(line_text)

        # Trigger an event (print the line text)
        # print(f"Selected: {line_text}")

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

    def delete_row_starting_with(self, start_text: str):
        """Delete the row that starts with the given text."""
        self.text_widget.configure(state="normal")
        last_line_index = int(self.text_widget.index('end-1c').split('.')[0])

        for line_number in range(last_line_index, 0, -1):
            line_start = f"{line_number}.0"
            line_end = f"{line_number}.end"
            line_text = self.text_widget.get(line_start, line_end).strip()
            if line_text.startswith(start_text):
                self.text_widget.delete(line_start, f"{line_number + 1}.0")
                break

        self.text_widget.configure(state="disabled")

    def replace_multiple_newlines(self):
        """Replace multiple consecutive lines with only newline characters with a single newline character.
        """
        self.text_widget.configure(state="normal")
        current_index = "1.0"
        while True:
            current_index = self.text_widget.search("\n\n\n", current_index, END)
            if not current_index:
                break
            next_index = self.text_widget.index(f"{current_index} + 1c")
            self.text_widget.delete(current_index, next_index)
        self.text_widget.configure(state="disabled")

    def delete_last_2_row(self):
        """Delete last 2 rows of text
        """
        self.text_widget.configure(state="normal")
        last_index = self.text_widget.index("end-1c linestart")
        second_last_index = self.text_widget.index("%s -1 lines" % last_index)
        self.text_widget.delete(second_last_index, "end-1c")
        self.text_widget.configure(state="disabled")

    def get_text_last_3_rows(self) -> str:
        last_index = self.text_widget.index("end-1c linestart")
        second_last_index = self.text_widget.index("%s -1 lines" % last_index)
        third_last_index = self.text_widget.index("%s -1 lines" % second_last_index)
        line_text = self.text_widget.get(third_last_index, "end-1c")
        return line_text


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = SelectableText()

    # Add a lot of lines of text
    lines_of_text = [f"Line {i}: This is an example of a long line of text that should wrap around the Text widget." for i in range(1, 101)]
    for line in lines_of_text:
        app.add_text_to_bottom(line)

    app.mainloop()
