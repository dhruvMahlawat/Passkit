import flet as ft

from .. import config
from ..manager import LockedOutError, PasswordManager
from . import style


def setup_screen(page: ft.Page, manager: PasswordManager, on_done):
    pw = ft.TextField(label="Master password", password=True, can_reveal_password=True, border_radius=8)
    confirm = ft.TextField(label="Confirm password", password=True, can_reveal_password=True, border_radius=8)
    error = ft.Text("", color=style.DANGER, size=12)

    def submit(e):
        if len(pw.value) < config.MIN_MASTER_PASSWORD_LENGTH:
            error.value = f"Needs at least {config.MIN_MASTER_PASSWORD_LENGTH} characters."
            page.update()
            return
        if pw.value != confirm.value:
            error.value = "Passwords don't match."
            page.update()
            return
        manager.set_master_password(pw.value)
        on_done()

    content = ft.Column(
        [
            ft.Text("🔑", size=36),
            ft.Text("Welcome to Passkit", size=22, weight=ft.FontWeight.BOLD, color=style.TEXT),
            ft.Text("Set a master password to get started.", size=13, color=style.MUTED),
            ft.Container(height=8),
            style.warning_note(
                "There's no \"forgot password\" option. Your master password is the "
                "encryption key - lose it and everything in the vault is gone for good."
            ),
            pw,
            confirm,
            error,
            ft.Button(content="Create vault", on_click=submit, bgcolor=style.ACCENT, color="white", width=320),
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=style.card(content, width=380),
        alignment=ft.Alignment.CENTER,
        expand=True,
        bgcolor=style.BG,
    )


def login_screen(page: ft.Page, manager: PasswordManager, on_done):
    pw = ft.TextField(label="Master password", password=True, can_reveal_password=True, border_radius=8, autofocus=True)
    error = ft.Text("", color=style.DANGER, size=12)

    def submit(e):
        try:
            if manager.login(pw.value):
                on_done()
            else:
                error.value = "Wrong password."
                pw.value = ""
                page.update()
        except LockedOutError as exc:
            error.value = f"Too many attempts. Wait {exc.seconds_remaining:.0f}s."
            pw.value = ""
            page.update()

    pw.on_submit = submit

    content = ft.Column(
        [
            ft.Text("🔒", size=36),
            ft.Text("Passkit is locked", size=22, weight=ft.FontWeight.BOLD, color=style.TEXT),
            ft.Container(height=8),
            pw,
            error,
            ft.Button(content="Unlock", on_click=submit, bgcolor=style.ACCENT, color="white", width=320),
        ],
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=style.card(content, width=380),
        alignment=ft.Alignment.CENTER,
        expand=True,
        bgcolor=style.BG,
    )
