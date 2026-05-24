# src/anm/gui/panels/_base.py
"""Base class for Phase 1 tool panels.

Layout:

    ┌─────────────────────────────────────────────────────────────────┐
    │ [icon] Tool name        Description       [Open file] [Run]     │  56px
    ├─────────────────────────────────────────────┬───────────────────┤
    │ content_area (PageThumbGrid)                │ inspector_area    │  flex
    │                                             │ (tool options +   │  280
    │                                             │  output dir +     │
    │                                             │  status)          │
    └─────────────────────────────────────────────┴───────────────────┘
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..catalog import get_tool
from ..styles import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    CAT_ACCENTS,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    body,
    heading,
    label_font,
)
from ._page_grid import PageThumbGrid

_INSPECTOR_W = 280
_HEADER_H = 64


class BaseToolPanel(ttk.Frame):
    """Common chrome shared by every Phase 1 tool panel."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        tool_id: str,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
    ) -> None:
        super().__init__(parent)
        self.tool_id = tool_id
        self.status_var = status_var
        self.progress_var = progress_var
        self.event_queue = event_queue

        self._source_path: Path | None = None
        self.custom_output_dir: Path | None = None
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        self._worker: threading.Thread | None = None
        self._running = False

        self._build_header()
        self._build_split_layout()
        self._build_inspector_footer()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        tool = get_tool(self.tool_id)
        cat_accent = CAT_ACCENTS.get(tool.cat if tool else "", ACCENT)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        hdr = tk.Frame(self, bg=SURFACE, height=_HEADER_H)
        hdr.grid(row=0, column=0, sticky="ew", columnspan=2)
        hdr.grid_propagate(False)
        hdr.columnconfigure(2, weight=1)

        # Icon pill
        pill = tk.Frame(hdr, bg=ACCENT_SOFT, width=36, height=36)
        pill.grid(row=0, column=0, padx=(20, 12), pady=14)
        pill.grid_propagate(False)
        tk.Label(
            pill,
            text=tool.icon if tool else "?",
            bg=ACCENT_SOFT,
            fg=cat_accent,
            font=body(16, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Title + description
        title_box = tk.Frame(hdr, bg=SURFACE)
        title_box.grid(row=0, column=1, sticky="w", pady=14)
        tk.Label(
            title_box,
            text=tool.label if tool else self.tool_id,
            bg=SURFACE,
            fg=TEXT,
            font=heading(15),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text=tool.desc if tool else "",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(11),
            anchor="w",
        ).pack(anchor="w")

        # Buttons
        btn_box = tk.Frame(hdr, bg=SURFACE)
        btn_box.grid(row=0, column=3, sticky="e", padx=(0, 20), pady=14)
        ttk.Button(btn_box, text="Open file", command=self._open_file).pack(side="left", padx=(0, 8))
        self._run_btn = ttk.Button(btn_box, text=self._run_label(), command=self._on_run_clicked)
        self._run_btn.pack(side="left")

        # Bottom border
        tk.Frame(self, bg=BORDER, height=1).grid(row=0, column=0, columnspan=2, sticky="sew")

    def _build_split_layout(self) -> None:
        # Content (col 0)
        self._content = tk.Frame(self, bg=BG)
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

        self._grid = PageThumbGrid(self._content)
        self._grid.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        # Vertical separator
        tk.Frame(self, bg=BORDER, width=1).grid(row=1, column=0, sticky="nse")

        # Inspector (col 1)
        self._inspector = tk.Frame(self, bg=SURFACE, width=_INSPECTOR_W)
        self._inspector.grid(row=1, column=1, sticky="ns")
        self._inspector.grid_propagate(False)
        self._inspector.columnconfigure(0, weight=1)

    def _build_inspector_footer(self) -> None:
        # Output directory row sits at the bottom of the inspector.
        # Subclasses populate the top portion via _build_inspector(inspector_area).
        self._footer = tk.Frame(self._inspector, bg=SURFACE)
        self._footer.grid(row=99, column=0, sticky="sew", padx=16, pady=(12, 16))
        self._inspector.rowconfigure(99, weight=0)

        tk.Label(
            self._footer,
            text="OUTPUT",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        ).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(self._footer, bg=SURFACE)
        row.pack(fill="x")
        tk.Entry(row, textvariable=self.output_dir_var, font=body(11)).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="…", width=3, command=self._choose_output_dir).pack(side="left", padx=(4, 0))

        # Status line
        tk.Label(
            self._footer,
            textvariable=self.status_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(11),
            wraplength=_INSPECTOR_W - 32,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------------
    # Subclass-facing API
    # ------------------------------------------------------------------

    @property
    def content_area(self) -> tk.Frame:
        return self._content

    @property
    def inspector_area(self) -> tk.Frame:
        return self._inspector

    @property
    def grid_widget(self) -> PageThumbGrid:
        return self._grid

    def _run_label(self) -> str:
        """Subclass overrides to change the primary-button text."""
        return "Run"

    def _build_inspector(self, parent: tk.Frame) -> None:
        """Override to add tool-specific widgets to *parent* (the inspector area).

        Subclasses call this explicitly after ``super().__init__()``::

            super().__init__(parent, tool_id="split", ...)
            self._build_inspector(self.inspector_area)
        """

    def _build_options(self) -> object:
        """Override to return the tool's Options dataclass, built from Tk vars.

        Called on the **main thread** by ``_on_run_clicked`` before the worker
        thread starts — never call Tk vars from the worker thread.
        """
        return None  # type: ignore[return-value]

    def _execute(self, source: Path, output_dir: Path, options: object) -> str:
        """Subclass runs the tool and returns a one-line success summary.

        *options* is the pre-built result of ``_build_options()``, captured
        on the main thread so Tk variables are never accessed from the worker.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self._load_pdf(Path(path))

    def _handle_drop(self, event: object) -> None:
        raw = getattr(event, "data", "")
        if not raw:
            return
        # tkinterdnd2 wraps paths-with-spaces in braces.
        first = raw.strip().split("} {")[0].lstrip("{").rstrip("}")
        path = Path(first)
        if path.suffix.lower() == ".pdf" and path.is_file():
            self._load_pdf(path)

    def _load_pdf(self, path: Path) -> None:
        self._source_path = path
        self.status_var.set(f"Loaded {path.name}")
        self._grid.load_pdf(path)
        self._on_pdf_loaded()

    def _on_pdf_loaded(self) -> None:
        """Override for per-tool reactions (e.g. update inspector preview)."""

    def _choose_output_dir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.output_dir_var.set(d)
            self.custom_output_dir = Path(d)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        if self._running:
            return
        if self._source_path is None:
            messagebox.showinfo("No file", "Open a PDF first.")
            return
        try:
            out_dir = Path(self.output_dir_var.get()).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Output directory", f"Cannot create folder: {exc}")
            return

        self._running = True
        self._run_btn.state(["disabled"])

        # Snapshot Tk variable state on the main thread — Tk vars are not
        # thread-safe and must not be read from the worker thread.
        options = self._build_options()
        source = self._source_path

        def _worker() -> None:
            try:
                summary = self._execute(source, out_dir, options)
                self.event_queue.put(("done", summary))
            except Exception as exc:  # noqa: BLE001 - surface to user
                self.event_queue.put(("error", str(exc)))

        self._worker = threading.Thread(target=_worker, daemon=True)
        self._worker.start()

    def _handle_event(self, event_type: str, payload: object) -> None:
        if event_type == "done":
            self.status_var.set(str(payload))
        elif event_type == "error":
            self.status_var.set("Failed.")
            messagebox.showerror("Tool failed", str(payload))
        self._running = False
        self._run_btn.state(["!disabled"])
