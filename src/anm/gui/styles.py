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


def _safe_style_call(fn, *args, **kwargs) -> None:
    """Best-effort ttk styling.

    ``ttk.Style.configure`` and ``style.map`` accept theme-specific options
    (``bordercolor``, ``lightcolor``, ``darkcolor``, ``focuscolor`` …) that
    raise ``tkinter.TclError`` on builds without the ``clam`` theme.  We
    swallow those so the legacy ``--tk`` GUI still launches with default
    styling, even when the platform tk is limited.
    """
    import tkinter as tk

    try:
        fn(*args, **kwargs)
    except tk.TclError:
        # Retry with only universally supported keys to keep some styling.
        safe = {
            k: v
            for k, v in kwargs.items()
            if k in {"background", "foreground", "relief", "padding", "font"}
        }
        try:
            fn(*args, **safe)
        except tk.TclError:
            pass


def configure_ttk(root: object) -> None:
    """Apply project-wide ttk styling that mirrors `.anm-btn` from app.css.

    Call once at app start, after the root window exists.  Tolerates Tk
    builds that don't ship the ``clam`` theme or that reject theme-specific
    options — see ``_safe_style_call``.
    """
    from tkinter import ttk

    style = ttk.Style(root)  # type: ignore[arg-type]
    try:
        style.theme_use("clam")  # clam supports the most styling options
    except Exception:
        pass

    # Plain button — neutral surface with a border-strong outline
    _safe_style_call(
        style.configure,
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
    _safe_style_call(
        style.map,
        "TButton",
        background=[("active", SURFACE_3), ("pressed", SURFACE_3)],
        bordercolor=[("active", BORDER_STRONG)],
    )

    # Primary action — accent fill, accent text colour
    _safe_style_call(
        style.configure,
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
    _safe_style_call(
        style.map,
        "Accent.TButton",
        background=[("active", "#0073d2"), ("pressed", "#005ba8")],
        foreground=[("active", "#ffffff")],
    )
