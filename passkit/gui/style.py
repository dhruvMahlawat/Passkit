import flet as ft

BG = "#15151d"
SURFACE = "#1e1f2b"
SURFACE_ALT = "#262838"
BORDER = "#33354a"
TEXT = "#f2f2f7"
MUTED = "#8b8da3"
ACCENT = "#7c5cff"
ACCENT_DARK = "#6a4ce0"
DANGER = "#ef5164"
SUCCESS = "#39c17f"
WARN_BG = "#332916"
WARN_BORDER = "#7a5a1f"
WARN_TEXT = "#e0ac3f"

STRENGTH_COLORS = {"weak": DANGER, "medium": "#e0a13a", "strong": SUCCESS}


def drag_strip(page):
    """A thin invisible strip at the top of a frameless screen that lets you
    drag the window - there's no OS titlebar to grab otherwise.
    """
    def start_drag(e):
        page.run_task(page.window.start_dragging)

    return ft.GestureDetector(
        content=ft.Container(height=32, bgcolor=BG),
        on_pan_start=start_drag,
    )


def card(content, width=380, padding=28):
    return ft.Container(
        content=content,
        width=width,
        padding=padding,
        bgcolor=SURFACE,
        border_radius=16,
        border=ft.Border.all(1, BORDER),
    )


def warning_note(text):
    return ft.Container(
        content=ft.Row(
            [
                ft.Text("⚠", size=16),
                ft.Text(text, size=12, color=WARN_TEXT, expand=True),
            ],
            spacing=10,
        ),
        bgcolor=WARN_BG,
        border=ft.Border.all(1, WARN_BORDER),
        border_radius=10,
        padding=12,
    )


def strength_bar(width=280):
    """Returns (control, refresh_fn). refresh_fn(password) updates the bar."""
    bar = ft.ProgressBar(value=0, width=width, height=6, border_radius=3, bgcolor=BORDER)
    label = ft.Text("", size=12, color=MUTED)
    fill = {"weak": 0.33, "medium": 0.66, "strong": 1.0}

    def refresh(password, strength_fn):
        if not password:
            bar.value = 0
            label.value = ""
            return
        strength = strength_fn(password)
        bar.value = fill[strength]
        bar.color = STRENGTH_COLORS[strength]
        label.value = strength.capitalize()
        label.color = STRENGTH_COLORS[strength]

    return ft.Column([bar, label], spacing=4), refresh
