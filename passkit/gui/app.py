import asyncio
import time

import flet as ft

from .. import config
from ..manager import PasswordManager
from . import dialogs, screens, style

IDLE_LOCK_SECONDS = 120


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "Passkit"
        page.bgcolor = style.BG
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0

        page.window.full_screen = True
        page.window.frameless = True

        # A single AnimatedSwitcher holds whatever screen is active, so
        # switching between login/setup/main fades instead of hard-cutting.
        self.switcher = ft.AnimatedSwitcher(
            content=ft.Container(),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=250,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )
        page.controls = [self.switcher]

        self.manager = PasswordManager()
        self._search = ""
        self._idle_deadline = 0.0
        self._idle_watch_running = False

        if self.manager.has_master_password():
            self._show_login()
        else:
            self._show_setup()

    def _set_screen(self, control):
        self.switcher.content = control
        self.page.update()

    # --- screen switching ------------------------------------------------

    def _show_setup(self):
        self._set_screen(screens.setup_screen(self.page, self.manager, self._on_unlocked))

    def _show_login(self):
        self._set_screen(screens.login_screen(self.page, self.manager, self._on_unlocked))

    def _on_unlocked(self):
        self._build_main_view()
        self._reset_idle_timer()

    def _lock_now(self, e=None):
        self.manager.lock()
        self._show_login()

    def _reset_idle_timer(self):
        # A plain-thread timer isn't safe to touch page state from, so this
        # runs as a task on Flet's own event loop instead - it just wakes up
        # again whenever the deadline moves and checks if it's expired.
        self._idle_deadline = time.monotonic() + IDLE_LOCK_SECONDS
        if not self._idle_watch_running:
            self._idle_watch_running = True
            self.page.run_task(self._idle_watch)

    async def _idle_watch(self):
        while True:
            remaining = self._idle_deadline - time.monotonic()
            if remaining <= 0:
                self._idle_watch_running = False
                self._lock_now()
                return
            await asyncio.sleep(remaining)

    # --- main view -----------------------------------------------------

    def _build_main_view(self):
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("🔑 Passkit", size=20, weight=ft.FontWeight.BOLD, color=style.TEXT),
                    ft.Row(
                        [
                            ft.TextButton("Change master password", on_click=self._open_change_password),
                            ft.OutlinedButton("Lock", icon=ft.Icons.LOCK, on_click=self._lock_now),
                            ft.IconButton(icon=ft.Icons.CLOSE, tooltip="Quit", on_click=self._quit),
                        ]
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(24, 20, 24, 10),
        )

        self.search_field = ft.TextField(
            hint_text="Search entries", prefix_icon=ft.Icons.SEARCH, border_radius=20,
            filled=True, bgcolor=style.SURFACE_ALT, border_color=style.BORDER,
            width=260, height=42, content_padding=ft.Padding(16, 8, 16, 8),
            on_change=self._on_search,
        )

        toolbar = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Button(
                                content="Add entry", icon=ft.Icons.ADD,
                                bgcolor=style.ACCENT, color="white",
                                on_click=self._open_add_dialog,
                            ),
                            ft.OutlinedButton(
                                "Generate password", icon=ft.Icons.CASINO,
                                on_click=self._open_generator,
                            ),
                        ],
                        spacing=10,
                    ),
                    self.search_field,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(24, 0, 24, 14),
        )

        self.list_view = ft.ListView(expand=True, spacing=8, padding=ft.Padding(24, 0, 24, 20))
        self.status = ft.Container(
            content=ft.Text("", size=12, color=style.MUTED),
            padding=ft.Padding(24, 6, 24, 12),
        )

        main_view = ft.Column(
            [header, toolbar, ft.Container(content=self.list_view, expand=True), self.status],
            expand=True,
            spacing=0,
        )
        self._set_screen(main_view)
        self._refresh_list()
        self.page.update()

    def _quit(self, e=None):
        self.page.run_task(self.page.window.close)



    def _on_search(self, e):
        self._search = self.search_field.value.strip()
        self._refresh_list()
        self.page.update()

    def _refresh_list(self):
        entries = self.manager.list_entries(self._search)
        rows = [self._entry_row(meta) for meta in entries]
        for row in rows:
            row.opacity = 0
            row.offset = ft.Offset(0, 0.06)
        self.list_view.controls = rows

        if entries:
            self.status.content.value = f"{len(entries)} saved entr{'y' if len(entries) == 1 else 'ies'}"
        elif self._search:
            self.status.content.value = "No matches for that search"
        else:
            self.status.content.value = "No entries yet - click \"Add entry\" to save your first one"

        if rows:
            self.page.run_task(self._reveal_rows, rows)

    async def _reveal_rows(self, rows):
        # A short stagger per row so the list feels like it's settling into
        # place rather than just appearing - purely cosmetic, capped low so
        # a big list doesn't take forever to finish revealing.
        self.page.update()
        for i, row in enumerate(rows):
            await asyncio.sleep(min(i, 12) * 0.02)
            row.opacity = 1
            row.offset = ft.Offset(0, 0)
            row.update()

    def _entry_row(self, meta):
        initial = meta.website[:1].upper() or "?"

        def open_menu_action(action):
            def handler(e):
                self._reset_idle_timer()
                if action == "view":
                    entry = self.manager.get_entry(meta.id, meta)
                    dialogs.view_entry(self.page, entry, self._copy_to_clipboard)
                    self.page.update()
                elif action == "edit":
                    entry = self.manager.get_entry(meta.id, meta)
                    dialogs.add_or_edit_entry(self.page, self.manager, self._on_list_changed, entry=entry)
                    self.page.update()
                elif action == "delete":
                    self.manager.delete_entry(meta.id)
                    self._on_list_changed()
            return handler

        avatar = ft.Container(
            content=ft.Text(initial, weight=ft.FontWeight.BOLD, color="white"),
            width=38, height=38, border_radius=10, bgcolor=style.ACCENT,
            alignment=ft.Alignment.CENTER,
        )

        row = ft.Container(
            content=ft.Row(
                [
                    avatar,
                    ft.Column(
                        [
                            ft.Text(meta.website, weight=ft.FontWeight.BOLD, color=style.TEXT),
                            ft.Text(meta.username, size=12, color=style.MUTED),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Text(meta.modified_at[:10], size=12, color=style.MUTED),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        items=[
                            ft.PopupMenuItem(content="View", icon=ft.Icons.VISIBILITY, on_click=open_menu_action("view")),
                            ft.PopupMenuItem(content="Edit", icon=ft.Icons.EDIT, on_click=open_menu_action("edit")),
                            ft.PopupMenuItem(content="Delete", icon=ft.Icons.DELETE, on_click=open_menu_action("delete")),
                        ],
                    ),
                ],
                spacing=14,
            ),
            padding=12,
            bgcolor=style.SURFACE,
            border_radius=12,
            border=ft.Border.all(1, style.BORDER),
            on_click=open_menu_action("view"),
            ink=True,
            scale=1.0,
            animate=150,
            animate_opacity=250,
            animate_offset=250,
            animate_scale=150,
        )

        def on_hover(e):
            hovering = e.data == "true"
            row.bgcolor = style.SURFACE_ALT if hovering else style.SURFACE
            row.scale = 1.01 if hovering else 1.0
            row.update()

        row.on_hover = on_hover
        return row


    def _on_list_changed(self):
        self._refresh_list()
        self.page.update()

    # --- actions -----------------------------------------------------------

    def _open_add_dialog(self, e):
        self._reset_idle_timer()
        dialogs.add_or_edit_entry(self.page, self.manager, self._on_list_changed)
        self.page.update()

    def _open_generator(self, e):
        self._reset_idle_timer()
        dialogs.generate_password(self.page, self.manager, self._copy_to_clipboard)
        self.page.update()

    def _open_change_password(self, e):
        self._reset_idle_timer()
        dialogs.change_master_password(self.page, self.manager, self._on_list_changed)
        self.page.update()

    def _copy_to_clipboard(self, password: str):
        self.page.pop_dialog()

        async def do_copy():
            await ft.Clipboard().set(password)
            self.page.show_dialog(ft.SnackBar(content=ft.Text(f"Copied - clears in {config.CLIPBOARD_CLEAR_SECONDS}s")))
            self.page.update()
            await asyncio.sleep(config.CLIPBOARD_CLEAR_SECONDS)
            current = await ft.Clipboard().get()
            if current == password:
                await ft.Clipboard().set("")

        self.page.run_task(do_copy)
