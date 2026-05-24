"""Scrollable grid of PDF page thumbnails rendered with PyMuPDF."""

from __future__ import annotations

import base64
import tkinter as tk
from pathlib import Path
from typing import Callable

import fitz

from ..styles import ACCENT, BG, BORDER_STRONG, DANGER, SURFACE, TEXT_SUBTLE, label_font

# Default thumbnail width in pixels (height derives from page aspect).
_THUMB_W = 80
_GAP = 12


class PageThumbGrid(tk.Frame):
    """Scrollable grid showing one thumbnail per page of a loaded PDF.

    Optional click handling: pass ``on_page_click(page_idx)`` to receive
    0-based page indices when the user clicks a thumbnail.  The grid also
    exposes a ``mark(indices, style)`` method so tool panels can highlight
    pages (e.g. as deletion or split-point markers).
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_page_click: Callable[[int], None] | None = None,
        thumb_width: int = _THUMB_W,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._on_page_click = on_page_click
        self._thumb_w = thumb_width
        self._photos: list[tk.PhotoImage] = []  # keep refs alive
        self._cards: dict[int, tk.Frame] = {}
        self._marked: dict[int, str] = {}  # page_idx → style key
        self.page_count = 0

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self._vscroll = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vscroll.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vscroll.grid(row=0, column=1, sticky="ns")

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(self._win, width=e.width),
        )
        self._canvas.bind(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"),
        )

        self._empty_label = tk.Label(
            self._inner,
            text="Drop a PDF here or click Open file",
            bg=BG,
            fg=TEXT_SUBTLE,
            font=label_font(12),
            pady=60,
        )
        self._empty_label.pack()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_pdf(self, path: Path) -> None:
        """Render thumbnails for every page of *path*."""
        for child in self._inner.winfo_children():
            child.destroy()
        self._photos.clear()
        self._cards.clear()
        self._marked.clear()
        self.page_count = 0

        with fitz.open(path) as doc:
            self.page_count = doc.page_count
            for i, page in enumerate(doc):
                photo = self._render(page)
                self._photos.append(photo)
                self._add_card(i, photo)

        self._relayout()

    def mark(self, indices: list[int], style: str = "select") -> None:
        """Highlight *indices* with the given style (``select`` / ``delete``)."""
        for idx in list(self._marked.keys()):
            self._apply_style(idx, None)
        self._marked.clear()
        for idx in indices:
            if 0 <= idx < self.page_count:
                self._marked[idx] = style
                self._apply_style(idx, style)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render(self, page: fitz.Page) -> tk.PhotoImage:
        scale = self._thumb_w / page.rect.width
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        # Tk PhotoImage accepts base64-encoded GIF or PNG.
        data = base64.b64encode(pix.tobytes("png"))
        return tk.PhotoImage(data=data)

    def _add_card(self, idx: int, photo: tk.PhotoImage) -> None:
        card = tk.Frame(
            self._inner,
            bg=SURFACE,
            highlightbackground=BORDER_STRONG,
            highlightthickness=1,
        )
        lbl = tk.Label(
            card,
            image=photo,
            bg=SURFACE,
            cursor="hand2" if self._on_page_click else "",
        )
        lbl.pack(padx=4, pady=(4, 0))
        tk.Label(
            card,
            text=str(idx + 1),
            bg=SURFACE,
            fg=TEXT_SUBTLE,
            font=label_font(10),
        ).pack(pady=(2, 4))

        if self._on_page_click is not None:
            for w in (card, lbl):
                w.bind("<Button-1>", lambda _e, i=idx: self._on_page_click(i))

        self._cards[idx] = card

    def _relayout(self) -> None:
        """Place cards in a 6-column grid."""
        cols = 6
        for i, (idx, card) in enumerate(sorted(self._cards.items())):
            card.grid_forget()
            card.grid(
                row=i // cols,
                column=i % cols,
                padx=_GAP // 2,
                pady=_GAP // 2,
                sticky="n",
            )
        for c in range(cols):
            self._inner.columnconfigure(c, weight=1)

    def _apply_style(self, idx: int, style: str | None) -> None:
        card = self._cards.get(idx)
        if card is None:
            return
        if style == "select":
            card.config(highlightbackground=ACCENT, highlightthickness=2)
        elif style == "delete":
            card.config(highlightbackground=DANGER, highlightthickness=2)
        else:
            card.config(highlightbackground=BORDER_STRONG, highlightthickness=1)
