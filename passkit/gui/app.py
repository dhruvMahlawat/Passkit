import tkinter as tk
from tkinter import messagebox, ttk

from .. import config
from ..manager import PasswordManager
from . import dialogs, style

IDLE_LOCK_SECONDS = 120  # auto-lock the vault after 2 minutes of no activity


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Password Manager")
        self.root.geometry("760x560")
        self.root.minsize(620, 420)
        style.apply(root)

        self.manager = PasswordManager()
        self._clipboard_token = None  # guards against clearing someone else's copy
        self._idle_job = None

        if self.manager.has_master_password():
            dialogs.login(self.root, self.manager, self._on_unlocked)
        else:
            dialogs.setup_master_password(self.root, self.manager, self._on_unlocked)

    # --- lifecycle ---------------------------------------------------------

    def _on_unlocked(self):
        self._build_main_view()
        self._reset_idle_timer()

    def _build_main_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        header = ttk.Frame(self.root, padding=(20, 16, 20, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Password Manager", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Lock 🔒", style="Secondary.TButton", command=self._lock_now).pack(side="right")

        toolbar = ttk.Frame(self.root, padding=(20, 0, 20, 10))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="+ Add", style="Accent.TButton", command=self._open_add_dialog).pack(side="left")
        ttk.Button(
            toolbar, text="Generate password", style="Secondary.TButton", command=self._open_generator
        ).pack(side="left", padx=(8, 0))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=28)
        search_entry.pack(side="right")
        ttk.Label(toolbar, text="Search").pack(side="right", padx=(0, 8))

        body = ttk.Frame(self.root, padding=(20, 0, 20, 20))
        body.pack(fill="both", expand=True)

        columns = ("website", "username", "modified")
        self.tree = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("website", text="Website")
        self.tree.heading("username", text="Username")
        self.tree.heading("modified", text="Last modified")
        self.tree.column("website", width=220)
        self.tree.column("username", width=200)
        self.tree.column("modified", width=140)

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._open_selected())
        self.tree.bind("<Button-3>", self._show_context_menu)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="View", command=self._open_selected)
        self.context_menu.add_command(label="Edit", command=self._edit_selected)
        self.context_menu.add_command(label="Delete", command=self._delete_selected)

        self.status = ttk.Label(self.root, text="", style="Muted.TLabel", padding=(20, 4))
        self.status.pack(fill="x", side="bottom")

        for event in ("<Button-1>", "<Key>"):
            self.root.bind_all(event, lambda e: self._reset_idle_timer(), add="+")

        self._refresh_list()

    def _lock_now(self, *_):
        self.manager.lock()
        dialogs.login(self.root, self.manager, self._on_unlocked)

    def _reset_idle_timer(self):
        if self._idle_job:
            self.root.after_cancel(self._idle_job)
        self._idle_job = self.root.after(IDLE_LOCK_SECONDS * 1000, self._lock_now)

    # --- list rendering ------------------------------------------------

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self._entries_by_row = {}
        entries = self.manager.list_entries(self.search_var.get().strip())
        for meta in entries:
            modified = meta.modified_at[:10] if meta.modified_at else "-"
            row_id = self.tree.insert("", "end", values=(meta.website, meta.username, modified))
            self._entries_by_row[row_id] = meta
        self.status.config(text=f"{len(entries)} saved" if entries else "No entries yet")

    def _selected_meta(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self._entries_by_row.get(selection[0])

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.context_menu.post(event.x_root, event.y_root)

    # --- actions -----------------------------------------------------------

    def _open_add_dialog(self):
        dialogs.add_or_edit_entry(self.root, self.manager, self._refresh_list)

    def _edit_selected(self):
        meta = self._selected_meta()
        if not meta:
            messagebox.showwarning("No selection", "Pick an entry first.")
            return
        entry = self.manager.get_entry(meta.id, meta)
        dialogs.add_or_edit_entry(self.root, self.manager, self._refresh_list, entry=entry)

    def _open_selected(self):
        meta = self._selected_meta()
        if not meta:
            return
        entry = self.manager.get_entry(meta.id, meta)
        dialogs.view_entry(self.root, entry, self._copy_to_clipboard)

    def _delete_selected(self):
        meta = self._selected_meta()
        if not meta:
            messagebox.showwarning("No selection", "Pick an entry first.")
            return
        if messagebox.askyesno("Delete entry", f"Delete the saved entry for {meta.website}?"):
            self.manager.delete_entry(meta.id)
            self._refresh_list()

    def _open_generator(self):
        dialogs.generate_password(self.root, self.manager, self._copy_to_clipboard)

    def _copy_to_clipboard(self, password: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(password)
        self._clipboard_token = password
        self.status.config(text=f"Copied - clipboard clears in {config.CLIPBOARD_CLEAR_SECONDS}s")
        self.root.after(config.CLIPBOARD_CLEAR_SECONDS * 1000, lambda: self._clear_clipboard(password))

    def _clear_clipboard(self, password: str):
        # Only wipe it if the clipboard still holds what we put there -
        # otherwise we'd be nuking whatever the user copied since.
        try:
            if self.root.clipboard_get() == password:
                self.root.clipboard_clear()
        except tk.TclError:
            pass
