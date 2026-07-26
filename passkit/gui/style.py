from tkinter import ttk

BG = "#f5f6f8"
SURFACE = "#ffffff"
BORDER = "#dfe2e6"
TEXT = "#1f2430"
MUTED = "#6b7280"
ACCENT = "#3b5bdb"
ACCENT_DARK = "#2f4bc0"
DANGER = "#d64545"
SUCCESS = "#2f9e44"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_MONO = ("Consolas", 11)

STRENGTH_COLORS = {"weak": DANGER, "medium": "#e8912d", "strong": SUCCESS}


def apply(root):
    root.configure(bg=BG)

    style = ttk.Style(root)
    # 'clam' is the only built-in theme that actually respects color overrides
    # on Windows/Linux/macOS consistently.
    style.theme_use("clam")

    style.configure("TFrame", background=BG)
    style.configure("Surface.TFrame", background=SURFACE)

    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
    style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT, font=FONT)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT)
    style.configure("Surface.Muted.TLabel", background=SURFACE, foreground=MUTED, font=FONT)

    style.configure(
        "Accent.TButton",
        font=FONT_BOLD,
        foreground="white",
        background=ACCENT,
        borderwidth=0,
        padding=(14, 8),
    )
    style.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", BORDER)])

    style.configure(
        "Secondary.TButton",
        font=FONT,
        foreground=TEXT,
        background=SURFACE,
        borderwidth=1,
        padding=(12, 7),
    )
    style.map("Secondary.TButton", background=[("active", BG)])

    style.configure(
        "Danger.TButton",
        font=FONT_BOLD,
        foreground="white",
        background=DANGER,
        borderwidth=0,
        padding=(14, 8),
    )
    style.map("Danger.TButton", background=[("active", "#b83a3a")])

    style.configure("TEntry", padding=6, fieldbackground=SURFACE, font=FONT)

    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        rowheight=28,
        font=FONT,
        borderwidth=0,
    )
    style.configure("Treeview.Heading", font=FONT_BOLD, background=BG, foreground=MUTED, relief="flat")
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])


def center(dialog, width, height):
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")
