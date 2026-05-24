"""Variant B – Tool Hub Launcher (Acrobat-style home screen).

Opens to a grid of all tools grouped by category.  Clicking a card
calls ``on_tool_select(tool_id)``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .catalog import CATEGORIES, ToolDef, tools_by_cat
from .styles import (
    ACCENT,
    BG,
    BORDER,
    BORDER_STRONG,
    CAT_ACCENTS,
    SURFACE,
    SURFACE_2,
    SURFACE_3,
    TEXT,
    TEXT_MUTED,
    TEXT_SUBTLE,
    body,
    heading,
    label_font,
)

# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _add_hover(widget: tk.Widget, enter_bg: str, leave_bg: str) -> None:
    """Recursively bind enter/leave to recolour *widget* and all descendants."""
    def _set(w: tk.Widget, colour: str) -> None:
        try:
            w.config(bg=colour)
        except tk.TclError:
            pass
        for child in w.winfo_children():
            _set(child, colour)

    widget.bind("<Enter>", lambda _e: _set(widget, enter_bg), add="+")
    widget.bind("<Leave>", lambda _e: _set(widget, leave_bg), add="+")
    for child in widget.winfo_children():
        child.bind("<Enter>", lambda _e: _set(widget, enter_bg), add="+")
        child.bind("<Leave>", lambda _e: _set(widget, leave_bg), add="+")


# ──────────────────────────────────────────────────────────────────────────────
# Tool card
# ──────────────────────────────────────────────────────────────────────────────


class _ToolCard(tk.Frame):
    """Clickable card that represents a single tool."""

    def __init__(
        self,
        parent: tk.Widget,
        tool: ToolDef,
        on_click: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            highlightthickness=1,
            cursor="hand2",
        )
        cat_accent = CAT_ACCENTS.get(tool.cat, ACCENT)

        # Icon pill ─────────────────────────────────────────────────────────
        icon_bg = _blend_hex(cat_accent, SURFACE, 0.13)
        icon_frame = tk.Frame(self, bg=icon_bg, width=32, height=32)
        icon_frame.grid(row=0, column=0, sticky="nw", padx=12, pady=(12, 0))
        icon_frame.grid_propagate(False)
        tk.Label(
            icon_frame,
            text=tool.icon,
            bg=icon_bg,
            fg=cat_accent,
            font=body(13, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Tool name ─────────────────────────────────────────────────────────
        tk.Label(
            self,
            text=tool.label,
            bg=SURFACE,
            fg=TEXT,
            font=body(12, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 0))

        # Description ───────────────────────────────────────────────────────
        tk.Label(
            self,
            text=tool.desc,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(11),
            anchor="nw",
            justify="left",
            wraplength=150,
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 12))

        self.columnconfigure(0, weight=1)

        # "Coming soon" dim if no panel ─────────────────────────────────────
        if tool.panel_key is None:
            self.config(highlightbackground=BORDER)
            for child in self.winfo_children():
                try:
                    child.config(fg=TEXT_SUBTLE)
                except tk.TclError:
                    pass

        # Click / hover bindings ────────────────────────────────────────────
        def _click(_event: object) -> None:
            if tool.panel_key is not None:
                on_click()

        for w in (self, *self.winfo_children(), *_all_children(self)):
            w.bind("<Button-1>", _click, add="+")

        _add_hover(self, SURFACE_3, SURFACE)


# ──────────────────────────────────────────────────────────────────────────────
# Top bar
# ──────────────────────────────────────────────────────────────────────────────


class _TopBar(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=SURFACE, height=64)
        self.pack_propagate(False)
        self.grid_propagate(False)

        # Logo ──────────────────────────────────────────────────────────────
        logo_frame = tk.Frame(self, bg="#d24726", width=22, height=22)
        logo_frame.pack(side="left", padx=(20, 8), pady=0, anchor="center")
        logo_frame.pack_propagate(False)
        tk.Label(
            logo_frame, text="A", bg="#d24726", fg="white", font=body(9, "bold")
        ).place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self, text="AnM", bg=SURFACE, fg=TEXT, font=heading(16)).pack(
            side="left", padx=(0, 16), anchor="center"
        )

        # Search bar ────────────────────────────────────────────────────────
        search_frame = tk.Frame(
            self,
            bg=SURFACE_2,
            highlightbackground=BORDER,
            highlightthickness=1,
            width=380,
            height=34,
        )
        search_frame.pack(side="left", anchor="center", padx=(0, 12))
        search_frame.pack_propagate(False)
        tk.Label(
            search_frame,
            text="  🔍  Search tools and files…",
            bg=SURFACE_2,
            fg=TEXT_SUBTLE,
            font=body(12),
            anchor="w",
        ).pack(fill="both", expand=True, padx=4)

        # Buttons ───────────────────────────────────────────────────────────
        _btn(self, "Open").pack(side="left", anchor="center", padx=4)
        _btn(self, "⚙", ghost=True).pack(side="left", anchor="center", padx=(0, 16))


# ──────────────────────────────────────────────────────────────────────────────
# HubHomePanel (public)
# ──────────────────────────────────────────────────────────────────────────────


class HubHomePanel(ttk.Frame):
    """Variant B – launcher grid.  ``on_tool_select(tool_id)`` fires on click."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_tool_select: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self._on_tool_select = on_tool_select
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top bar ───────────────────────────────────────────────────────
        top = _TopBar(self)
        top.grid(row=0, column=0, sticky="ew")
        _hsep(self).grid(row=0, column=0, sticky="sew", ipady=0)

        # Scrollable body ───────────────────────────────────────────────
        body_frame = tk.Frame(self, bg=BG)
        body_frame.grid(row=1, column=0, sticky="nsew")
        body_frame.columnconfigure(0, weight=1)
        body_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(body_frame, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(body_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        body_frame.columnconfigure(0, weight=1)
        body_frame.rowconfigure(0, weight=1)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.columnconfigure(0, weight=1)

        def _on_inner_configure(_event: object) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: object) -> None:
            canvas.itemconfig(win_id, width=event.width)  # type: ignore[attr-defined]

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Build sections ────────────────────────────────────────────────
        row = 0

        # Category sections
        for cat in CATEGORIES:
            _CategorySection(
                inner,
                cat_id=cat.id,
                cat_label=cat.label,
                on_tool_select=self._on_tool_select,
            ).grid(row=row, column=0, sticky="ew", padx=28, pady=(20, 0))
            row += 1

        # Bottom spacer
        tk.Frame(inner, bg=BG, height=24).grid(row=row, column=0)


# ──────────────────────────────────────────────────────────────────────────────
# Category section
# ──────────────────────────────────────────────────────────────────────────────


class _CategorySection(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        cat_id: str,
        cat_label: str,
        on_tool_select: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg=BG)
        self.columnconfigure(0, weight=1)
        self._build(cat_id, cat_label, on_tool_select)

    def _build(
        self,
        cat_id: str,
        cat_label: str,
        on_tool_select: Callable[[str], None],
    ) -> None:
        accent = CAT_ACCENTS.get(cat_id, ACCENT)

        # Section header ────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        hdr.columnconfigure(2, weight=1)

        tk.Frame(hdr, bg=accent, width=8, height=8).grid(
            row=0, column=0, padx=(0, 8)
        )
        tk.Label(
            hdr,
            text=cat_label.upper(),
            bg=BG,
            fg=TEXT_MUTED,
            font=label_font(11),
        ).grid(row=0, column=1, sticky="w")
        tk.Frame(hdr, bg=BORDER, height=1).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

        # Tool card grid ────────────────────────────────────────────────
        grid_frame = tk.Frame(self, bg=BG)
        grid_frame.grid(row=1, column=0, sticky="ew")

        cols = 4
        for i in range(cols):
            grid_frame.columnconfigure(i, weight=1, uniform="card")

        for idx, tool in enumerate(tools_by_cat(cat_id)):
            card = _ToolCard(
                grid_frame,
                tool,
                on_click=lambda tid=tool.id: on_tool_select(tid),
            )
            card.grid(
                row=idx // cols,
                column=idx % cols,
                sticky="nsew",
                padx=(0 if idx % cols == 0 else 6, 0),
                pady=(0, 6),
            )


# ──────────────────────────────────────────────────────────────────────────────
# Tiny helpers
# ──────────────────────────────────────────────────────────────────────────────


def _btn(parent: tk.Widget, text: str, *, ghost: bool = False) -> tk.Label:
    bg = SURFACE if not ghost else SURFACE
    lbl = tk.Label(
        parent,
        text=f"  {text}  ",
        bg=bg,
        fg=TEXT,
        font=body(12),
        relief="flat",
        highlightbackground=BORDER_STRONG if not ghost else BORDER,
        highlightthickness=1,
        padx=4,
        pady=4,
        cursor="hand2",
    )
    _add_hover(lbl, SURFACE_3, bg)
    return lbl


def _hsep(parent: tk.Widget) -> ttk.Separator:
    return ttk.Separator(parent, orient="horizontal")


def _all_children(widget: tk.Widget) -> list[tk.Widget]:
    result: list[tk.Widget] = []
    for child in widget.winfo_children():
        result.append(child)
        result.extend(_all_children(child))
    return result


def _blend_hex(hex_a: str, hex_b: str, t: float) -> str:
    """Linearly interpolate two hex colours; t=0 → hex_b, t=1 → hex_a."""
    a = tuple(int(hex_a.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(hex_b.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    mixed = tuple(int(b[i] + t * (a[i] - b[i])) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


