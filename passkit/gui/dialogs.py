import tkinter as tk
from tkinter import messagebox, ttk

from .. import config
from ..manager import LockedOutError, PasswordManager
from . import style


def _new_dialog(parent, title, width, height):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=style.BG)
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()
    style.center(dialog, width, height)
    return dialog


def setup_master_password(parent, manager: PasswordManager, on_done):
    """First-run dialog: pick a master password."""
    dialog = _new_dialog(parent, "Set up your vault", 380, 300)

    ttk.Label(dialog, text="Welcome 👋", style="Title.TLabel").pack(pady=(24, 4))
    ttk.Label(
        dialog,
        text="Choose a master password. There's no recovery\nif you lose it, so pick something you'll remember.",
        style="Muted.TLabel",
        justify="center",
    ).pack(pady=(0, 20))

    form = ttk.Frame(dialog)
    form.pack(padx=30, fill="x")

    ttk.Label(form, text="Master password").pack(anchor="w")
    pw_entry = ttk.Entry(form, show="•")
    pw_entry.pack(fill="x", pady=(2, 10))

    ttk.Label(form, text="Confirm password").pack(anchor="w")
    confirm_entry = ttk.Entry(form, show="•")
    confirm_entry.pack(fill="x", pady=(2, 4))

    error_label = ttk.Label(form, text="", foreground=style.DANGER, background=style.BG)
    error_label.pack(anchor="w", pady=(4, 0))

    def submit(event=None):
        password = pw_entry.get()
        confirm = confirm_entry.get()

        if len(password) < config.MIN_MASTER_PASSWORD_LENGTH:
            error_label.config(text=f"Needs at least {config.MIN_MASTER_PASSWORD_LENGTH} characters.")
            return
        if password != confirm:
            error_label.config(text="Passwords don't match.")
            return

        manager.set_master_password(password)
        dialog.destroy()
        on_done()

    ttk.Button(dialog, text="Create vault", style="Accent.TButton", command=submit).pack(pady=18)
    pw_entry.focus()
    dialog.bind("<Return>", submit)


def login(parent, manager: PasswordManager, on_done):
    dialog = _new_dialog(parent, "Unlock vault", 340, 220)

    ttk.Label(dialog, text="🔒 Vault Locked", style="Title.TLabel").pack(pady=(24, 12))
    pw_entry = ttk.Entry(dialog, show="•")
    pw_entry.pack(padx=30, fill="x")

    error_label = ttk.Label(dialog, text="", foreground=style.DANGER, background=style.BG)
    error_label.pack(pady=(8, 0))

    def submit(event=None):
        try:
            if manager.login(pw_entry.get()):
                dialog.destroy()
                on_done()
            else:
                error_label.config(text="Wrong password.")
                pw_entry.delete(0, tk.END)
        except LockedOutError as exc:
            error_label.config(text=f"Too many attempts. Wait {exc.seconds_remaining:.0f}s.")
            pw_entry.delete(0, tk.END)

    ttk.Button(dialog, text="Unlock", style="Accent.TButton", command=submit).pack(pady=16)
    pw_entry.focus()
    dialog.bind("<Return>", submit)
    dialog.protocol("WM_DELETE_WINDOW", lambda: parent.destroy())


def _strength_row(parent, get_password):
    """A small label that updates live to show weak/medium/strong."""
    label = ttk.Label(parent, text="", style="Surface.Muted.TLabel")

    def refresh(*_):
        pw = get_password()
        if not pw:
            label.config(text="")
            return
        strength = PasswordManager.password_strength(pw)
        label.config(text=f"Strength: {strength}", foreground=style.STRENGTH_COLORS[strength])

    return label, refresh


def add_or_edit_entry(parent, manager: PasswordManager, on_saved, entry=None):
    """entry is an Entry (decrypted) when editing, None when adding new."""
    is_edit = entry is not None
    dialog = _new_dialog(parent, "Edit entry" if is_edit else "Add entry", 380, 340)

    ttk.Label(dialog, text="Edit entry" if is_edit else "Add new entry", style="Title.TLabel").pack(pady=(20, 14))

    form = ttk.Frame(dialog)
    form.pack(padx=30, fill="x")

    ttk.Label(form, text="Website / service").pack(anchor="w")
    website_entry = ttk.Entry(form)
    website_entry.pack(fill="x", pady=(2, 10))

    ttk.Label(form, text="Username / email").pack(anchor="w")
    username_entry = ttk.Entry(form)
    username_entry.pack(fill="x", pady=(2, 10))

    ttk.Label(form, text="Password").pack(anchor="w")
    pw_row = ttk.Frame(form)
    pw_row.pack(fill="x", pady=(2, 2))
    pw_entry = ttk.Entry(pw_row, show="•")
    pw_entry.pack(side="left", fill="x", expand=True)

    def fill_generated():
        pw_entry.delete(0, tk.END)
        pw_entry.insert(0, manager.generate_password())

    ttk.Button(pw_row, text="Generate", style="Secondary.TButton", command=fill_generated).pack(side="left", padx=(8, 0))

    strength_label, refresh_strength = _strength_row(form, pw_entry.get)
    strength_label.pack(anchor="w", pady=(2, 0))
    strength_var = tk.StringVar()
    pw_entry.configure(textvariable=strength_var)
    strength_var.trace_add("write", refresh_strength)

    if is_edit:
        website_entry.insert(0, entry.website)
        username_entry.insert(0, entry.username)
        pw_entry.insert(0, entry.password)

    error_label = ttk.Label(dialog, text="", foreground=style.DANGER, background=style.BG)
    error_label.pack(pady=(4, 0))

    def submit(event=None):
        website = website_entry.get().strip()
        username = username_entry.get().strip()
        password = pw_entry.get()

        if not website or not username or not password:
            error_label.config(text="All fields are required.")
            return

        if is_edit:
            manager.update_entry(entry.id, website, username, password)
        else:
            manager.add_entry(website, username, password)

        dialog.destroy()
        on_saved()

    ttk.Button(dialog, text="Save", style="Accent.TButton", command=submit).pack(pady=16)
    website_entry.focus()
    dialog.bind("<Return>", submit)


def generate_password(parent, manager: PasswordManager, on_copy):
    dialog = _new_dialog(parent, "Generate password", 380, 300)

    ttk.Label(dialog, text="Password Generator", style="Title.TLabel").pack(pady=(20, 14))

    form = ttk.Frame(dialog)
    form.pack(padx=30, fill="x")

    ttk.Label(form, text="Length").pack(anchor="w")
    length_var = tk.IntVar(value=config.DEFAULT_PASSWORD_LENGTH)
    ttk.Spinbox(
        form, from_=config.MIN_PASSWORD_LENGTH, to=config.MAX_PASSWORD_LENGTH, textvariable=length_var, width=8
    ).pack(anchor="w", pady=(2, 10))

    symbols_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(form, text="Include symbols", variable=symbols_var).pack(anchor="w", pady=(0, 12))

    result_var = tk.StringVar()
    result_entry = ttk.Entry(form, textvariable=result_var, font=style.FONT_MONO, state="readonly")
    result_entry.pack(fill="x")

    def roll():
        result_var.set(manager.generate_password(length_var.get(), symbols_var.get()))

    roll()

    button_row = ttk.Frame(dialog)
    button_row.pack(pady=18)
    ttk.Button(button_row, text="Regenerate", style="Secondary.TButton", command=roll).pack(side="left", padx=6)
    ttk.Button(
        button_row, text="Copy", style="Accent.TButton", command=lambda: on_copy(result_var.get())
    ).pack(side="left", padx=6)


def view_entry(parent, entry, on_copy):
    dialog = _new_dialog(parent, "Entry details", 380, 280)

    ttk.Label(dialog, text=entry.website, style="Title.TLabel").pack(pady=(20, 14))

    form = ttk.Frame(dialog)
    form.pack(padx=30, fill="x")

    ttk.Label(form, text="Username").pack(anchor="w")
    ttk.Label(form, text=entry.username, style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

    ttk.Label(form, text="Password").pack(anchor="w")
    pw_row = ttk.Frame(form)
    pw_row.pack(fill="x", pady=(2, 0))

    masked = "•" * len(entry.password)
    pw_var = tk.StringVar(value=masked)
    ttk.Label(pw_row, textvariable=pw_var, font=style.FONT_MONO).pack(side="left")

    def toggle():
        pw_var.set(entry.password if show_var.get() else masked)

    show_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(pw_row, text="Show", variable=show_var, command=toggle).pack(side="left", padx=(10, 0))

    ttk.Label(form, text=f"Last modified {entry.modified_at[:19].replace('T', ' ')}", style="Muted.TLabel").pack(
        anchor="w", pady=(14, 0)
    )

    ttk.Button(
        dialog, text="Copy password", style="Accent.TButton", command=lambda: on_copy(entry.password)
    ).pack(pady=18)
