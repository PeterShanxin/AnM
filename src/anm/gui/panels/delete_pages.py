# src/anm/gui/panels/delete_pages.py
"""GUI panel for the Delete Pages tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path

from ...tools.delete_pages import DeletePagesOptions, delete_pages
from ...tools.page_range import parse_page_range
from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ._base import BaseToolPanel


class DeletePagesPanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
    ) -> None:
        self._page_spec_var = tk.StringVar(value="")
        super().__init__(
            parent,
            tool_id="delete",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
        )
        self._page_spec_var.trace_add("write", lambda *_: self._update_marks())
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Delete"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(
            section, text="PAGES TO DELETE", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)
        ).pack(anchor="w", pady=(0, 4))
        tk.Entry(section, textvariable=self._page_spec_var, font=body(11)).pack(fill="x")
        tk.Label(
            section,
            text='e.g. "2, 4-6"',
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        ).pack(anchor="w", pady=(2, 0))

    def _update_marks(self) -> None:
        if self.grid_widget.page_count == 0:
            return
        try:
            indices = parse_page_range(
                self._page_spec_var.get(), total_pages=self.grid_widget.page_count
            )
        except ValueError:
            return
        self.grid_widget.mark(indices, style="delete")

    def _build_options(self) -> DeletePagesOptions:
        return DeletePagesOptions(page_spec=self._page_spec_var.get())

    def _execute(self, source: Path, output_dir: Path, options: object) -> str:
        assert isinstance(options, DeletePagesOptions)
        out_path = output_dir / f"{source.stem}_trimmed.pdf"
        delete_pages(source, options, output_path=out_path)
        return f"Saved → {out_path.name}"
