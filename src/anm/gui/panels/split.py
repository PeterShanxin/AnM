# src/anm/gui/panels/split.py
"""GUI panel for the Split tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ...tools.split import SplitMode, SplitOptions, split_pdf
from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ._base import BaseToolPanel


class SplitPanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
        **kwargs: object,
    ) -> None:
        self._mode_var = tk.StringVar(value="each_page")
        self._range_var = tk.StringVar(value="1-")
        self._every_n_var = tk.IntVar(value=1)
        super().__init__(
            parent,
            tool_id="split",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
            **kwargs,
        )
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Split"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        mode_label = tk.Label(
            section,
            text="SPLIT MODE",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        )
        mode_label.pack(anchor="w", pady=(0, 6))

        for value, label, desc in [
            ("each_page", "Each page", "One file per page"),
            ("ranges", "By page ranges", "e.g. 1-5, 8, 12-24"),
            ("every_n", "Every N pages", "Fixed-size chunks"),
        ]:
            row = tk.Frame(section, bg=SURFACE)
            row.pack(fill="x", pady=2)
            ttk.Radiobutton(
                row, text=label, value=value, variable=self._mode_var
            ).pack(anchor="w")
            desc_label = tk.Label(
                row,
                text=f"   {desc}",
                bg=SURFACE,
                fg=TEXT_MUTED,
                font=label_font(10),
            )
            desc_label.pack(anchor="w")

        ranges_label = tk.Label(
            section,
            text="PAGE RANGES",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        )
        ranges_label.pack(anchor="w", pady=(12, 4))
        tk.Entry(section, textvariable=self._range_var, font=body(11)).pack(
            fill="x"
        )

        n_label = tk.Label(
            section,
            text="N (every N pages)",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        )
        n_label.pack(anchor="w", pady=(12, 4))
        tk.Spinbox(
            section,
            from_=1,
            to=999,
            textvariable=self._every_n_var,
            width=8,
        ).pack(anchor="w")

    def _build_options(self) -> SplitOptions:
        mode_map = {
            "each_page": SplitMode.EACH_PAGE,
            "ranges":    SplitMode.RANGES,
            "every_n":   SplitMode.EVERY_N,
        }
        return SplitOptions(
            mode=mode_map[self._mode_var.get()],
            page_spec=self._range_var.get(),
            every_n=self._every_n_var.get(),
        )

    def _execute(self, source: Path, output_dir: Path, options: object) -> str:
        assert isinstance(options, SplitOptions)
        result = split_pdf(source, options, output_dir=output_dir)
        return f"Wrote {len(result.output_paths)} file(s) to {output_dir}"
