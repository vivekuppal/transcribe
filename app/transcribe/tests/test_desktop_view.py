"""Unit tests for desktop view construction helpers."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.transcribe.desktop.view import DesktopViewBuilder


class FakeMenu:
    """Menu double that captures construction options and cascade entries."""

    created = []

    def __init__(self, master=None, **kwargs):
        self.master = master
        self.kwargs = kwargs
        self.cascades = []
        self.__class__.created.append(self)

    def add_cascade(self, **kwargs):
        self.cascades.append(kwargs)


class TestDesktopViewBuilder(unittest.TestCase):
    def setUp(self):
        FakeMenu.created = []
        self.builder = DesktopViewBuilder()
        self.ui = SimpleNamespace(
            ui_font_size=20,
            option_add_calls=[],
            config_calls=[],
            option_add=lambda pattern, value: self.ui.option_add_calls.append((pattern, value)),
            config=lambda **kwargs: self.ui.config_calls.append(kwargs),
        )

    def test_create_menus_uses_menu_font(self):
        with patch("app.transcribe.desktop.view.tk.Menu", FakeMenu):
            self.builder.create_menus(self.ui)

        menu_font = ("Arial", 12)
        self.assertEqual(self.ui.option_add_calls, [("*Menu.font", menu_font)])
        self.assertEqual([menu.kwargs["font"] for menu in FakeMenu.created], [menu_font] * 4)
        self.assertEqual(
            [cascade["label"] for cascade in self.ui.menubar.cascades],
            ["File", "Edit", "Help"],
        )
        self.assertEqual(self.ui.config_calls, [{"menu": self.ui.menubar}])


if __name__ == "__main__":
    unittest.main()
