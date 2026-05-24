# src/anm/gui/panels/reorder.py
"""GUI panel for the Reorder tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ...tools.reorder import ReorderOptions, reorder_pdf
from ._base import BaseToolPanel


class ReorderPanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
    ) -> None:
        self._order_var = tk.StringVar(value="")
        super().__init__(
            parent,
            tool_id="reorder",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
        )
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Reorder"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(section, text="PAGE ORDER", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(0, 4))
        tk.Entry(section, textvariable=self._order_var, font=body(11)).pack(fill="x")
        tk.Label(
            section,
            text='Comma-separated 1-based numbers covering every page once (e.g. "3, 1, 2")',
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
            wraplength=240,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _on_pdf_loaded(self) -> None:
        # Default to natural order so user can edit from a populated state.
        self._order_var.set(", ".join(str(i + 1) for i in range(self.grid_widget.page_count)))

    def _build_options(self) -> ReorderOptions:
        parts = [p.strip() for p in self._order_var.get().split(",") if p.strip()]
        order = [int(p) for p in parts]
        return ReorderOptions(order=order)

    def _execute(self, source: Path, output_dir: Path) -> str:
        out_path = output_dir / f"{source.stem}_reordered.pdf"
        reorder_pdf(source, self._build_options(), output_path=out_path)
        return f"Reordered → {out_path.name}"
