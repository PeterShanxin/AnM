"""Variant A – Icon Rail + Grouped Sidebar (VS Code / Explorer feel).

This frame wraps any tool panel with persistent navigation chrome:

    ┌──────┬────────────────────┬──────────────────────────────────┐
    │ Rail │ Sidebar            │ Tool content (swapped per tool)  │
    │ 56px │ 232px              │ flex                             │
    └──────┴────────────────────┴──────────────────────────────────┘

Public API
----------
``ToolChromeFrame.show_tool_panel(panel, tool_id, cat_id)``
    Swap the content area to *panel* and update the rail/sidebar selection.

``ToolChromeFrame.content_area``
    The ``tk.Frame`` that tool panels are parented to at creation time.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .catalog import CATEGORIES, ToolDef, tools_by_cat
from .styles import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    SURFACE,
    SURFACE_2,
    SURFACE_3,
    TEXT,
    TEXT_MUTED,
    body,
    heading,
    label_font,
)

# ──────────────────────────────────────────────────────────────────────────────
# Rail
# ──────────────────────────────────────────────────────────────────────────────

_RAIL_W = 56


class _RailItem(tk.Frame):
    """Single icon-button in the category rail. 40×40 inside a 56-px rail."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        icon: str,
        label: str,
        on_click: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=SURFACE_2, width=_RAIL_W, height=40,
                         cursor="hand2")
        self.pack_propagate(False)
        self._on_click = on_click
        self._active = False

        # 40×40 hit-square centred in the 56-px rail
        self._hit = tk.Frame(self, bg=SURFACE_2, width=40, height=40)
        self._hit.place(relx=0.5, rely=0.5, anchor="center")
        self._hit.pack_propagate(False)

        # Active indicator bar (left edge, 3-px accent strip)
        self._bar = tk.Frame(self, bg=SURFACE_2, width=3, height=24)
        self._bar.place(relx=0, rely=0.5, anchor="w")

        self._icon_lbl = tk.Label(
            self._hit,
            text=icon,
            bg=SURFACE_2,
            fg=TEXT_MUTED,
            font=body(15),
        )
        self._icon_lbl.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self, self._hit, self._icon_lbl):
            w.bind("<Button-1>", lambda _e: on_click(), add="+")
            w.bind("<Enter>", lambda _e: self._hover(True), add="+")
            w.bind("<Leave>", lambda _e: self._hover(False), add="+")

    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def _hover(self, entering: bool) -> None:
        if not self._active:
            bg = SURFACE_3 if entering else SURFACE_2
            self._hit.config(bg=bg)
            self._icon_lbl.config(bg=bg)

    def _refresh(self) -> None:
        if self._active:
            self._hit.config(bg=SURFACE_3)
            self._icon_lbl.config(bg=SURFACE_3, fg=ACCENT)
            self._bar.config(bg=ACCENT)
        else:
            self._hit.config(bg=SURFACE_2)
            self._icon_lbl.config(bg=SURFACE_2, fg=TEXT_MUTED)
            self._bar.config(bg=SURFACE_2)


class _CategoryRail(tk.Frame):
    """56-px fixed-width left rail with Home + category + utility icons."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_home: Callable[[], None],
        on_category: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            bg=SURFACE_2,
            width=_RAIL_W,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._on_category = on_category
        self._cat_items: dict[str, _RailItem] = {}
        self._active_cat: str | None = None

        self._build(on_home)

    def _build(self, on_home: Callable[[], None]) -> None:
        # Home — top with 8-px padding above
        home_item = _RailItem(self, icon="⌂", label="Home", on_click=on_home)
        home_item.pack(pady=(8, 4))

        # Hairline divider — 1-px line, 28-px wide, centred
        tk.Frame(self, bg=BORDER, height=1, width=28).pack(pady=6)

        # Category icons (gap 4 below each)
        icons = {"organize": "☰", "edit": "✏", "convert": "⇄", "secure": "⊕"}
        for cat in CATEGORIES:
            item = _RailItem(
                self,
                icon=icons.get(cat.id, cat.icon),
                label=cat.label,
                on_click=lambda cid=cat.id: self._select(cid),
            )
            item.pack(pady=(0, 4))
            self._cat_items[cat.id] = item

        # Spacer pushes utility icons to the bottom
        tk.Frame(self, bg=SURFACE_2).pack(fill="both", expand=True)

        # Utility icons at bottom
        _RailItem(self, icon="🔍", label="Search",
                  on_click=lambda: None).pack(pady=(0, 4))
        _RailItem(self, icon="⚙", label="Settings",
                  on_click=lambda: None).pack(pady=(0, 8))

    def select_category(self, cat_id: str) -> None:
        if self._active_cat and self._active_cat in self._cat_items:
            self._cat_items[self._active_cat].set_active(False)
        self._active_cat = cat_id
        if cat_id in self._cat_items:
            self._cat_items[cat_id].set_active(True)

    def _select(self, cat_id: str) -> None:
        self.select_category(cat_id)
        self._on_category(cat_id)


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────

_SIDEBAR_W = 232


class _SidebarToolRow(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        tool: ToolDef,
        *,
        active: bool = False,
        on_click: Callable[[], None],
    ) -> None:
        bg = ACCENT_SOFT if active else SURFACE
        super().__init__(parent, bg=bg, cursor="hand2")

        tk.Label(
            self,
            text=tool.icon,
            bg=bg,
            fg=ACCENT if active else TEXT_MUTED,
            font=body(13),
            width=2,
        ).pack(side="left", padx=(6, 4), pady=6)

        tk.Label(
            self,
            text=tool.label,
            bg=bg,
            fg=TEXT,
            font=body(12, "bold" if active else "normal"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True, pady=6)

        for w in (self, *self.winfo_children()):
            w.bind("<Button-1>", lambda _e: on_click(), add="+")
            w.bind("<Enter>", lambda _e: self._hover(True), add="+")
            w.bind("<Leave>", lambda _e: self._hover(False), add="+")

        self._active = active
        self._base_bg = bg

    def _hover(self, entering: bool) -> None:
        if not self._active:
            colour = SURFACE_3 if entering else SURFACE
            self.config(bg=colour)
            for c in self.winfo_children():
                try:
                    c.config(bg=colour)
                except tk.TclError:
                    pass


class _ToolSidebar(tk.Frame):
    """232-px sidebar listing tools for the currently active category."""

    def __init__(self, parent: tk.Widget, *, on_tool_click: Callable[[str], None]) -> None:
        super().__init__(parent, bg=SURFACE, width=_SIDEBAR_W)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._on_tool_click = on_tool_click
        self._active_tool: str | None = None
        self._cat_id: str | None = None

        # Header
        self._hdr_var = tk.StringVar(value="")
        self._header = tk.Frame(self, bg=SURFACE)
        self._header.pack(fill="x")
        tk.Label(
            self._header,
            textvariable=self._hdr_var,
            bg=SURFACE,
            fg=TEXT,
            font=heading(13),
            anchor="w",
        ).pack(side="left", padx=14, pady=(12, 6))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Tool list area
        self._list_frame = tk.Frame(self, bg=SURFACE)
        self._list_frame.pack(fill="both", expand=True, padx=6, pady=4)

        # Footer
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        tk.Label(
            self,
            text="  🕐  Recent files",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(11),
            anchor="w",
            pady=8,
        ).pack(fill="x")

    def show_category(self, cat_id: str, active_tool: str | None = None) -> None:
        cat = next((c for c in CATEGORIES if c.id == cat_id), None)
        if cat is None:
            return
        self._cat_id = cat_id
        self._active_tool = active_tool
        self._hdr_var.set(cat.label)

        # Rebuild tool rows
        for child in self._list_frame.winfo_children():
            child.destroy()

        for tool in tools_by_cat(cat_id):
            is_active = tool.id == active_tool
            _SidebarToolRow(
                self._list_frame,
                tool,
                active=is_active,
                on_click=lambda tid=tool.id: self._on_tool_click(tid),
            ).pack(fill="x", pady=1)


# ──────────────────────────────────────────────────────────────────────────────
# ToolChromeFrame (public)
# ──────────────────────────────────────────────────────────────────────────────


class ToolChromeFrame(ttk.Frame):
    """A-style in-tool chrome: rail + sidebar + swappable content area."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_home: Callable[[], None],
        on_tool_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self._on_home = on_home
        self._on_tool_navigate = on_tool_navigate
        self._current_panel: ttk.Frame | None = None
        self._current_tool_id: str | None = None

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        # Rail (col 0)
        self._rail = _CategoryRail(
            self,
            on_home=self._on_home,
            on_category=self._on_cat_selected,
        )
        self._rail.grid(row=0, column=0, sticky="ns")

        # Vertical separator (col 1)
        tk.Frame(self, bg=BORDER, width=1).grid(row=0, column=1, sticky="ns")

        # Sidebar (col 2 → 3)
        self._sidebar = _ToolSidebar(self, on_tool_click=self._on_tool_navigate)
        self._sidebar.grid(row=0, column=2, sticky="ns")

        # Vertical separator
        tk.Frame(self, bg=BORDER, width=1).grid(row=0, column=3, sticky="ns")

        # Content area (col 4)
        self._content = tk.Frame(self, bg=BG)
        self._content.grid(row=0, column=4, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)
        self.columnconfigure(4, weight=1)

    @property
    def content_area(self) -> tk.Frame:
        """Parent frame for tool panels — use this when constructing panels."""
        return self._content

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_tool_panel(
        self,
        panel: ttk.Frame,
        tool_id: str,
        cat_id: str,
    ) -> None:
        """Swap the content area to *panel* and sync rail/sidebar state."""
        if self._current_panel is not None:
            self._current_panel.grid_forget()

        panel.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel
        self._current_tool_id = tool_id

        self._rail.select_category(cat_id)
        self._sidebar.show_category(cat_id, active_tool=tool_id)

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_cat_selected(self, cat_id: str) -> None:
        """Rail category clicked — update sidebar to that category."""
        active = self._current_tool_id if self._get_current_cat() == cat_id else None
        self._sidebar.show_category(cat_id, active_tool=active)

    def _get_current_cat(self) -> str | None:
        if self._current_tool_id is None:
            return None
        from .catalog import get_tool
        tool = get_tool(self._current_tool_id)
        return tool.cat if tool else None
