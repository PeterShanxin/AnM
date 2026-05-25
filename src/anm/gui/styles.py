"""Design tokens for the AnM GUI — mirrors app.css :root (light theme)."""

from __future__ import annotations

# ── Backgrounds ────────────────────────────────────────────────────────────────
BG            = "#f3f3f3"   # window / canvas background
SURFACE       = "#ffffff"   # cards, panels
SURFACE_2     = "#fafafa"   # subtle surface (rail bg)
SURFACE_3     = "#f0f0f0"   # hover / active state

# ── Borders ────────────────────────────────────────────────────────────────────
BORDER        = "#e6e6e6"
BORDER_STRONG = "#d6d6d6"

# ── Text ───────────────────────────────────────────────────────────────────────
TEXT          = "#1a1a1a"
TEXT_MUTED    = "#5c5c5c"
TEXT_SUBTLE   = "#8a8a8a"

# ── Accent ─────────────────────────────────────────────────────────────────────
ACCENT        = "#0067c0"
ACCENT_SOFT   = "#cfe4f5"
DANGER        = "#c42b1c"

# ── Category accent colours (dot + icon tints) ─────────────────────────────────
CAT_ACCENTS: dict[str, str] = {
    "organize": "#5B6CFF",
    "edit":     "#E47A2E",
    "convert":  "#2BA876",
    "secure":   "#A24EC7",
}

# ── Fonts ──────────────────────────────────────────────────────────────────────
_FF = "Segoe UI"          # primary; Variable Text not universally available


def body(size: int = 13, weight: str = "normal") -> tuple[str, int, str]:
    return (_FF, size, weight)


def label_font(size: int = 11) -> tuple[str, int, str]:
    return (_FF, size, "normal")


def heading(size: int = 13) -> tuple[str, int, str]:
    return (_FF, size, "bold")


def configure_ttk(root: object) -> None:
    """Apply project-wide ttk styling that mirrors `.anm-btn` from app.css.

    Call once at app start, after the root window exists.
    """
    from tkinter import ttk

    style = ttk.Style(root)  # type: ignore[arg-type]
    try:
        style.theme_use("clam")  # clam supports the most styling options
    except Exception:
        pass

    # Plain button — neutral surface with a border-strong outline
    style.configure(
        "TButton",
        background=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        focusthickness=0,
        focuscolor=SURFACE,
        relief="flat",
        padding=(14, 4),
        font=(_FF, 11),
    )
    style.map(
        "TButton",
        background=[("active", SURFACE_3), ("pressed", SURFACE_3)],
        bordercolor=[("active", BORDER_STRONG)],
    )

    # Primary action — accent fill, accent text colour
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="#ffffff",
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        focusthickness=0,
        relief="flat",
        padding=(14, 4),
        font=(_FF, 11, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#0073d2"), ("pressed", "#005ba8")],
        foreground=[("active", "#ffffff")],
    )
