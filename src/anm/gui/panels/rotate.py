# src/anm/gui/panels/rotate.py
"""GUI panel for the Rotate tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ...tools.rotate import RotateOptions, rotate_pdf
from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ._base import BaseToolPanel


class RotatePanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
        **kwargs: object,
    ) -> None:
        self._page_spec_var = tk.StringVar(value="all")
        self._angle_var = tk.IntVar(value=90)
        super().__init__(
            parent,
            tool_id="rotate",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
            **kwargs,
        )
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Rotate"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(
            section, text="PAGES", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)
        ).pack(anchor="w", pady=(0, 4))
        tk.Entry(section, textvariable=self._page_spec_var, font=body(11)).pack(fill="x")
        tk.Label(
            section,
            text='Use "all" or e.g. "1-3, 5"',
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            section, text="ANGLE", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)
        ).pack(anchor="w", pady=(12, 4))
        angles = tk.Frame(section, bg=SURFACE)
        angles.pack(fill="x")
        for angle in (90, 180, 270):
            ttk.Radiobutton(
                angles, text=f"{angle}°", value=angle, variable=self._angle_var
            ).pack(side="left", padx=(0, 12))

    def _build_options(self) -> RotateOptions:
        return RotateOptions(
            page_spec=self._page_spec_var.get(),
            angle=self._angle_var.get(),
        )

    def _execute(self, source: Path, output_dir: Path, options: object) -> str:
        assert isinstance(options, RotateOptions)
        out_path = output_dir / f"{source.stem}_rotated.pdf"
        result = rotate_pdf(source, options, output_path=out_path)
        return f"Rotated {result.pages_rotated} page(s) → {out_path.name}"
