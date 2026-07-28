"""Run the password manager.

    python main.py
"""

import flet as ft

from passkit.gui.app import App


def main(page: ft.Page):
    App(page)


if __name__ == "__main__":
    ft.run(main)
