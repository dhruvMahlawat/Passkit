import flet as ft

from .. import config
from ..manager import PasswordManager
from . import style


def add_or_edit_entry(page: ft.Page, manager: PasswordManager, on_saved, entry=None):
    is_edit = entry is not None

    website = ft.TextField(label="Website / service", value=entry.website if is_edit else "", border_radius=8)
    username = ft.TextField(label="Username / email", value=entry.username if is_edit else "", border_radius=8)
    password = ft.TextField(
        label="Password", value=entry.password if is_edit else "",
        password=True, can_reveal_password=True, border_radius=8, expand=True,
    )
    bar, refresh_bar = style.strength_bar(width=260)
    error = ft.Text("", color=style.DANGER, size=12)

    def on_password_change(e):
        refresh_bar(password.value, manager.password_strength)
        page.update()

    password.on_change = on_password_change

    def generate(e):
        password.value = manager.generate_password()
        refresh_bar(password.value, manager.password_strength)
        page.update()

    def submit(e):
        w, u, p = website.value.strip(), username.value.strip(), password.value
        if not w or not u or not p:
            error.value = "All fields are required."
            page.update()
            return
        if is_edit:
            manager.update_entry(entry.id, w, u, p)
        else:
            manager.add_entry(w, u, p)
        page.pop_dialog()
        on_saved()

    if is_edit:
        refresh_bar(password.value, manager.password_strength)

    dialog = ft.AlertDialog(
        title=ft.Text("Edit entry" if is_edit else "Add new entry", color=style.TEXT),
        bgcolor=style.SURFACE,
        content=ft.Container(
            width=340,
            content=ft.Column(
                [
                    website,
                    username,
                    ft.Row([password, ft.IconButton(icon=ft.Icons.CASINO, tooltip="Generate", on_click=generate)]),
                    bar,
                    error,
                ],
                spacing=12,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
            ft.Button(content="Save", on_click=submit, bgcolor=style.ACCENT, color="white"),
        ],
    )
    page.show_dialog(dialog)


def generate_password(page: ft.Page, manager: PasswordManager, on_copy):
    length = ft.TextField(label="Length", value=str(config.DEFAULT_PASSWORD_LENGTH), width=100, border_radius=8)
    symbols = ft.Checkbox(label="Include symbols", value=True)
    result = ft.TextField(value="", read_only=True, text_style=ft.TextStyle(font_family="monospace"), border_radius=8)
    bar, refresh_bar = style.strength_bar(width=280)

    def roll(e=None):
        try:
            n = max(config.MIN_PASSWORD_LENGTH, min(config.MAX_PASSWORD_LENGTH, int(length.value)))
        except ValueError:
            n = config.DEFAULT_PASSWORD_LENGTH
        pw = manager.generate_password(n, symbols.value)
        result.value = pw
        refresh_bar(pw, manager.password_strength)
        page.update()

    roll()

    dialog = ft.AlertDialog(
        title=ft.Text("Password Generator", color=style.TEXT),
        bgcolor=style.SURFACE,
        content=ft.Container(
            width=340,
            content=ft.Column([length, symbols, result, bar], spacing=14, tight=True),
        ),
        actions=[
            ft.TextButton("Regenerate", on_click=roll),
            ft.Button(content="Copy", on_click=lambda e: on_copy(result.value), bgcolor=style.ACCENT, color="white"),
        ],
    )
    page.show_dialog(dialog)


def view_entry(page: ft.Page, entry, on_copy):
    masked = "•" * len(entry.password)
    pw_text = ft.Text(masked, size=15, font_family="monospace")

    def toggle(e):
        pw_text.value = entry.password if pw_text.value == masked else masked
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text(entry.website, color=style.TEXT),
        bgcolor=style.SURFACE,
        content=ft.Container(
            width=320,
            content=ft.Column(
                [
                    ft.Text("Username", size=12, color=style.MUTED),
                    ft.Text(entry.username, color=style.TEXT),
                    ft.Container(height=6),
                    ft.Text("Password", size=12, color=style.MUTED),
                    ft.Row([pw_text, ft.IconButton(icon=ft.Icons.VISIBILITY, on_click=toggle)]),
                    ft.Text(
                        f"Last modified {entry.modified_at[:19].replace('T', ' ')}",
                        size=11, color=style.MUTED,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
            ft.Button(
                content="Copy password", bgcolor=style.ACCENT, color="white",
                on_click=lambda e: on_copy(entry.password),
            ),
        ],
    )
    page.show_dialog(dialog)


def change_master_password(page: ft.Page, manager: PasswordManager, on_done):
    current = ft.TextField(label="Current master password", password=True, can_reveal_password=True, border_radius=8)
    new = ft.TextField(label="New master password", password=True, can_reveal_password=True, border_radius=8)
    confirm = ft.TextField(label="Confirm new password", password=True, can_reveal_password=True, border_radius=8)
    error = ft.Text("", color=style.DANGER, size=12)

    def submit(e):
        if new.value != confirm.value:
            error.value = "New passwords don't match."
            page.update()
            return
        try:
            manager.change_master_password(current.value, new.value)
        except ValueError as exc:
            error.value = str(exc)
            page.update()
            return
        page.pop_dialog()
        on_done()

    dialog = ft.AlertDialog(
        title=ft.Text("Change master password", color=style.TEXT),
        bgcolor=style.SURFACE,
        content=ft.Container(
            width=340,
            content=ft.Column(
                [
                    ft.Text("Every saved entry gets re-encrypted with the new password.", size=12, color=style.MUTED),
                    style.warning_note("Still no recovery option - make sure you'll remember the new one."),
                    current,
                    new,
                    confirm,
                    error,
                ],
                spacing=12,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
            ft.Button(content="Change password", on_click=submit, bgcolor=style.ACCENT, color="white"),
        ],
    )
    page.show_dialog(dialog)
