import unittest
from tkinter import Tk
# from customtkinter import CTk

# Assuming SelectableTextComponent is defined in a module named selectable_text_component
from app.transcribe.uicomp.selectable_text import SelectableText


class TestSelectableText(unittest.TestCase):
    def setUp(self):
        # Set up a root window and the component for testing
        self.root = Tk()
        self.root.withdraw()  # Hide the root window
        self.component = SelectableText(self.root)
        self.component.pack()

    def tearDown(self):
        self.component.destroy()
        self.root.destroy()

    def test_insert_text_at_top(self):
        self.component.add_text_to_top("First line at top")
        result = self.component.text_widget.get("1.0", "2.0").strip()
        self.assertEqual(result, "First line at top")

    def test_insert_text_at_bottom(self):
        self.component.add_text_to_bottom("First line at bottom")
        result = self.component.text_widget.get("end-2l", "end-1l").strip()
        self.assertEqual(result, "First line at bottom")

    def test_scroll_to_top(self):
        self.component.add_text_to_top("Line 1\nLine 2\nLine 3\n")
        self.component.scroll_to_bottom()
        self.component.scroll_to_top()
        self.assertEqual(self.component.text_widget.yview()[0], 0.0)

    def test_scroll_to_bottom(self):
        self.component.add_text_to_bottom("Line 1\nLine 2\nLine 3\n")
        self.component.scroll_to_bottom()
        self.assertEqual(self.component.text_widget.yview()[1], 1.0)

    def test_delete_last_two_rows(self):
        self.component.add_text_to_bottom("Line 1")
        self.component.add_text_to_bottom("Line 2")
        self.component.add_text_to_bottom("Line 3")
        self.component.delete_last_2_row()
        result = self.component.text_widget.get("1.0", "end").strip()
        self.assertEqual(result, "Line 1")

    def test_clear_all_text(self):
        self.component.add_text_to_bottom("Line 1")
        self.component.add_text_to_bottom("Line 2")
        self.component.clear_all_text()
        result = self.component.text_widget.get("1.0", "end").strip()
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
