# Phase 1 GUI Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build five tkinter tool panels (Split, Rotate, Reorder, Delete Pages, Extract) that plug into the `ToolChromeFrame` content area and wire up the Phase 1 tool library to the GUI.

**Architecture:** A shared `BaseToolPanel` provides the tool header, two-column layout (content area + 280-px inspector), file-loading (filedialog + DnD), threaded execution, and status/progress wiring. A reusable `PageThumbGrid` renders PyMuPDF page thumbnails on demand. Each tool panel subclasses `BaseToolPanel` and supplies (a) inspector widgets, (b) `_build_options()` returning the tool's Options dataclass, and (c) a `_run_tool()` callable that invokes the library function. Visual design follows `variant-a.jsx SplitToolBody` from the design bundle.

**Tech Stack:** Python 3.14, tkinter/ttk, PyMuPDF (fitz, already installed), tkinterdnd2 (DnD, already installed), pytest.

---

## File Structure

```
src/anm/gui/panels/
├── __init__.py            — re-exports panel classes
├── _base.py               — BaseToolPanel, RunSpec dataclass
├── _page_grid.py          — PageThumbGrid widget with fitz rendering
├── split.py               — SplitPanel
├── rotate.py              — RotatePanel
├── reorder.py             — ReorderPanel
├── delete_pages.py        — DeletePagesPanel
└── extract.py             — ExtractPanel

src/anm/gui/hub.py         — modified: _create_tool_panel handles all 6 keys

tests/test_panels.py       — new: smoke tests for each panel
```

---

## Task 1: PageThumbGrid widget

**Files:**
- Create: `src/anm/gui/panels/__init__.py`
- Create: `src/anm/gui/panels/_page_grid.py`
- Test: `tests/test_panels.py`

- [ ] **Step 1: Create empty `__init__.py`**

```python
# src/anm/gui/panels/__init__.py
"""Tool panels for the Phase 1 page-operation tools."""
```

- [ ] **Step 2: Write failing test for PageThumbGrid**

```python
# tests/test_panels.py
from __future__ import annotations

import sys
from pathlib import Path

import fitz
import pytest

_HEADLESS = "win" not in sys.platform and not __import__("os").environ.get("DISPLAY")


def _make_pdf(path: Path, num_pages: int = 3) -> Path:
    doc = fitz.open()
    for _ in range(num_pages):
        doc.new_page(width=200, height=300)
    doc.save(path)
    doc.close()
    return path


@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_page_thumb_grid_loads_pdf(tmp_path: Path) -> None:
    import tkinter as tk
    from anm.gui.panels._page_grid import PageThumbGrid

    pdf = _make_pdf(tmp_path / "src.pdf", num_pages=4)

    root = tk.Tk()
    root.withdraw()
    try:
        grid = PageThumbGrid(root)
        grid.load_pdf(pdf)
        assert grid.page_count == 4
    finally:
        root.destroy()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_page_thumb_grid_loads_pdf -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'anm.gui.panels._page_grid'`

- [ ] **Step 4: Implement PageThumbGrid**

```python
# src/anm/gui/panels/_page_grid.py
"""Scrollable grid of PDF page thumbnails rendered with PyMuPDF."""

from __future__ import annotations

import base64
import io
import tkinter as tk
from pathlib import Path
from typing import Callable

import fitz

from ..styles import BG, BORDER, BORDER_STRONG, SURFACE, TEXT_SUBTLE, label_font

# Default thumbnail width in pixels (height derives from page aspect).
_THUMB_W = 80
_GAP = 12


class PageThumbGrid(tk.Frame):
    """Scrollable grid showing one thumbnail per page of a loaded PDF.

    Optional click handling: pass ``on_page_click(page_idx)`` to receive
    0-based page indices when the user clicks a thumbnail.  The grid also
    exposes ``marked_pages`` so tool panels can highlight pages (e.g. as
    deletion or split-point markers) by calling ``mark(indices, style)``.
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

        self._inner.bind("<Configure>", lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._win, width=e.width))
        self._canvas.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))

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
        card = tk.Frame(self._inner, bg=SURFACE, highlightbackground=BORDER_STRONG, highlightthickness=1)
        lbl = tk.Label(card, image=photo, bg=SURFACE, cursor="hand2" if self._on_page_click else "")
        lbl.pack(padx=4, pady=(4, 0))
        tk.Label(card, text=str(idx + 1), bg=SURFACE, fg=TEXT_SUBTLE, font=label_font(10)).pack(pady=(2, 4))

        if self._on_page_click is not None:
            for w in (card, lbl):
                w.bind("<Button-1>", lambda _e, i=idx: self._on_page_click(i))

        self._cards[idx] = card

    def _relayout(self) -> None:
        """Place cards in a 6-column grid (re-runs when window resizes)."""
        cols = 6
        for i, (idx, card) in enumerate(sorted(self._cards.items())):
            card.grid_forget()
            card.grid(row=i // cols, column=i % cols, padx=_GAP // 2, pady=_GAP // 2, sticky="n")
        for c in range(cols):
            self._inner.columnconfigure(c, weight=1)

    def _apply_style(self, idx: int, style: str | None) -> None:
        card = self._cards.get(idx)
        if card is None:
            return
        if style == "select":
            card.config(highlightbackground="#0067c0", highlightthickness=2)
        elif style == "delete":
            card.config(highlightbackground="#c42b1c", highlightthickness=2)
        else:
            card.config(highlightbackground=BORDER_STRONG, highlightthickness=1)
```

- [ ] **Step 5: Run test to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_page_thumb_grid_loads_pdf -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/anm/gui/panels/__init__.py src/anm/gui/panels/_page_grid.py tests/test_panels.py
git commit -m "feat(gui): add PageThumbGrid widget with PyMuPDF rendering"
```

---

## Task 2: BaseToolPanel

**Files:**
- Create: `src/anm/gui/panels/_base.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test for BaseToolPanel header**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_base_panel_has_header_and_split_layout(tmp_path: Path) -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels._base import BaseToolPanel

    root = tk.Tk()
    root.withdraw()
    try:
        panel = BaseToolPanel(
            root,
            tool_id="split",
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        assert panel.content_area is not None
        assert panel.inspector_area is not None
        assert panel._source_path is None
    finally:
        root.destroy()
```

- [ ] **Step 2: Run test to verify fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_base_panel_has_header_and_split_layout -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'anm.gui.panels._base'`

- [ ] **Step 3: Implement BaseToolPanel**

```python
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
from typing import Callable

from ..catalog import get_tool
from ..styles import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    BORDER_STRONG,
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
        """Subclass adds tool-specific widgets to *parent* (the inspector area)."""

    def _execute(self, source: Path, output_dir: Path) -> str:
        """Subclass runs the tool and returns a one-line success summary."""
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

        def _worker() -> None:
            try:
                summary = self._execute(self._source_path, out_dir)
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
```

- [ ] **Step 4: Run test to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/_base.py tests/test_panels.py
git commit -m "feat(gui): add BaseToolPanel with header, layout, and threaded run"
```

---

## Task 3: SplitPanel

**Files:**
- Create: `src/anm/gui/panels/split.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test for SplitPanel options**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_split_panel_builds_options_for_each_mode() -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels.split import SplitPanel
    from anm.tools.split import SplitMode

    root = tk.Tk()
    root.withdraw()
    try:
        panel = SplitPanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        # default mode
        opts = panel._build_options()
        assert opts.mode == SplitMode.EACH_PAGE

        panel._mode_var.set("ranges")
        panel._range_var.set("1-3,5")
        opts = panel._build_options()
        assert opts.mode == SplitMode.RANGES
        assert opts.page_spec == "1-3,5"

        panel._mode_var.set("every_n")
        panel._every_n_var.set(3)
        opts = panel._build_options()
        assert opts.mode == SplitMode.EVERY_N
        assert opts.every_n == 3
    finally:
        root.destroy()
```

- [ ] **Step 2: Run test to verify fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_split_panel_builds_options_for_each_mode -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement SplitPanel**

```python
# src/anm/gui/panels/split.py
"""GUI panel for the Split tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ...tools.split import SplitMode, SplitOptions, split_pdf
from ._base import BaseToolPanel


class SplitPanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
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
        )
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Split"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(section, text="SPLIT MODE", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(0, 6))

        for value, label, desc in [
            ("each_page", "Each page",     "One file per page"),
            ("ranges",    "By page ranges", "e.g. 1-5, 8, 12-24"),
            ("every_n",   "Every N pages",  "Fixed-size chunks"),
        ]:
            row = tk.Frame(section, bg=SURFACE)
            row.pack(fill="x", pady=2)
            ttk.Radiobutton(row, text=label, value=value, variable=self._mode_var).pack(anchor="w")
            tk.Label(row, text=f"   {desc}", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w")

        tk.Label(section, text="PAGE RANGES", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(12, 4))
        tk.Entry(section, textvariable=self._range_var, font=body(11)).pack(fill="x")

        tk.Label(section, text="N (every N pages)", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(12, 4))
        tk.Spinbox(section, from_=1, to=999, textvariable=self._every_n_var, width=8).pack(anchor="w")

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

    def _execute(self, source: Path, output_dir: Path) -> str:
        result = split_pdf(source, self._build_options(), output_dir=output_dir)
        return f"Wrote {len(result.output_paths)} file(s) to {output_dir}"
```

- [ ] **Step 4: Run test to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/split.py tests/test_panels.py
git commit -m "feat(gui): add SplitPanel with mode radio + range/N inputs"
```

---

## Task 4: RotatePanel

**Files:**
- Create: `src/anm/gui/panels/rotate.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_rotate_panel_builds_options() -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels.rotate import RotatePanel

    root = tk.Tk()
    root.withdraw()
    try:
        panel = RotatePanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        panel._page_spec_var.set("1-3")
        panel._angle_var.set(180)
        opts = panel._build_options()
        assert opts.page_spec == "1-3"
        assert opts.angle == 180
    finally:
        root.destroy()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_rotate_panel_builds_options -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement RotatePanel**

```python
# src/anm/gui/panels/rotate.py
"""GUI panel for the Rotate tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ...tools.rotate import RotateOptions, rotate_pdf
from ._base import BaseToolPanel


class RotatePanel(BaseToolPanel):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
    ) -> None:
        self._page_spec_var = tk.StringVar(value="all")
        self._angle_var = tk.IntVar(value=90)
        super().__init__(
            parent,
            tool_id="rotate",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
        )
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Rotate"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(section, text="PAGES", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(0, 4))
        tk.Entry(section, textvariable=self._page_spec_var, font=body(11)).pack(fill="x")
        tk.Label(section, text='Use "all" or e.g. "1-3, 5"', bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(2, 0))

        tk.Label(section, text="ANGLE", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(12, 4))
        angles = tk.Frame(section, bg=SURFACE)
        angles.pack(fill="x")
        for angle in (90, 180, 270):
            ttk.Radiobutton(angles, text=f"{angle}°", value=angle, variable=self._angle_var).pack(side="left", padx=(0, 12))

    def _build_options(self) -> RotateOptions:
        return RotateOptions(
            page_spec=self._page_spec_var.get(),
            angle=self._angle_var.get(),
        )

    def _execute(self, source: Path, output_dir: Path) -> str:
        out_path = output_dir / f"{source.stem}_rotated.pdf"
        rotate_pdf(source, self._build_options(), output_path=out_path)
        return f"Rotated → {out_path.name}"
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/rotate.py tests/test_panels.py
git commit -m "feat(gui): add RotatePanel with page-spec + angle radio"
```

---

## Task 5: ReorderPanel

**Files:**
- Create: `src/anm/gui/panels/reorder.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_reorder_panel_parses_order() -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels.reorder import ReorderPanel

    root = tk.Tk()
    root.withdraw()
    try:
        panel = ReorderPanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        panel._order_var.set("3, 1, 2")
        opts = panel._build_options()
        assert opts.order == [3, 1, 2]
    finally:
        root.destroy()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_reorder_panel_parses_order -v`
Expected: FAIL.

- [ ] **Step 3: Implement ReorderPanel**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/reorder.py tests/test_panels.py
git commit -m "feat(gui): add ReorderPanel with comma-separated order input"
```

---

## Task 6: DeletePagesPanel

**Files:**
- Create: `src/anm/gui/panels/delete_pages.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_delete_pages_panel_builds_options() -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels.delete_pages import DeletePagesPanel

    root = tk.Tk()
    root.withdraw()
    try:
        panel = DeletePagesPanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        panel._page_spec_var.set("2, 4-6")
        opts = panel._build_options()
        assert opts.page_spec == "2, 4-6"
    finally:
        root.destroy()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_delete_pages_panel_builds_options -v`
Expected: FAIL.

- [ ] **Step 3: Implement DeletePagesPanel**

```python
# src/anm/gui/panels/delete_pages.py
"""GUI panel for the Delete Pages tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ...tools.delete_pages import DeletePagesOptions, delete_pages
from ...tools.page_range import parse_page_range
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

        tk.Label(section, text="PAGES TO DELETE", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(0, 4))
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
            indices = parse_page_range(self._page_spec_var.get(), total_pages=self.grid_widget.page_count)
        except ValueError:
            return
        self.grid_widget.mark(indices, style="delete")

    def _build_options(self) -> DeletePagesOptions:
        return DeletePagesOptions(page_spec=self._page_spec_var.get())

    def _execute(self, source: Path, output_dir: Path) -> str:
        out_path = output_dir / f"{source.stem}_trimmed.pdf"
        delete_pages(source, self._build_options(), output_path=out_path)
        return f"Saved → {out_path.name}"
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/delete_pages.py tests/test_panels.py
git commit -m "feat(gui): add DeletePagesPanel with live red mark overlay"
```

---

## Task 7: ExtractPanel

**Files:**
- Create: `src/anm/gui/panels/extract.py`
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_extract_panel_builds_options() -> None:
    import queue
    import tkinter as tk
    from anm.gui.panels.extract import ExtractPanel

    root = tk.Tk()
    root.withdraw()
    try:
        panel = ExtractPanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        panel._page_spec_var.set("1-3,5")
        opts = panel._build_options()
        assert opts.page_spec == "1-3,5"
    finally:
        root.destroy()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_extract_panel_builds_options -v`
Expected: FAIL.

- [ ] **Step 3: Implement ExtractPanel**

```python
# src/anm/gui/panels/extract.py
"""GUI panel for the Extract tool."""

from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..styles import SURFACE, TEXT_MUTED, body, label_font
from ...tools.extract import ExtractOptions, extract_pages
from ...tools.page_range import parse_page_range
from ._base import BaseToolPanel


class ExtractPanel(BaseToolPanel):
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
            tool_id="extract",
            status_var=status_var,
            progress_var=progress_var,
            event_queue=event_queue,
        )
        self._page_spec_var.trace_add("write", lambda *_: self._update_marks())
        self._build_inspector(self.inspector_area)

    def _run_label(self) -> str:
        return "Extract"

    def _build_inspector(self, parent: tk.Frame) -> None:
        section = tk.Frame(parent, bg=SURFACE)
        section.grid(row=0, column=0, sticky="new", padx=16, pady=16)

        tk.Label(section, text="PAGES TO EXTRACT", bg=SURFACE, fg=TEXT_MUTED, font=label_font(10)).pack(anchor="w", pady=(0, 4))
        tk.Entry(section, textvariable=self._page_spec_var, font=body(11)).pack(fill="x")
        tk.Label(
            section,
            text='e.g. "1-3, 5" or "all"',
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=label_font(10),
        ).pack(anchor="w", pady=(2, 0))

    def _update_marks(self) -> None:
        if self.grid_widget.page_count == 0:
            return
        try:
            indices = parse_page_range(self._page_spec_var.get(), total_pages=self.grid_widget.page_count)
        except ValueError:
            return
        self.grid_widget.mark(indices, style="select")

    def _build_options(self) -> ExtractOptions:
        return ExtractOptions(page_spec=self._page_spec_var.get())

    def _execute(self, source: Path, output_dir: Path) -> str:
        out_path = output_dir / f"{source.stem}_extract.pdf"
        extract_pages(source, self._build_options(), output_path=out_path)
        return f"Saved → {out_path.name}"
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/anm/gui/panels/extract.py tests/test_panels.py
git commit -m "feat(gui): add ExtractPanel with live blue selection overlay"
```

---

## Task 8: Wire panels into the hub

**Files:**
- Modify: `src/anm/gui/panels/__init__.py`
- Modify: `src/anm/gui/hub.py:107-122` (`_create_tool_panel`)
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_hub_can_navigate_to_each_phase1_tool() -> None:
    import tkinter as tk
    from anm.gui import PDFAnnotatorApp

    app = PDFAnnotatorApp()
    app.withdraw()
    try:
        for tool_id in ("split", "rotate", "reorder", "delete", "extract"):
            app._on_home_tool_select(tool_id)
            assert app._active_panel is not None
            assert type(app._active_panel).__name__.endswith("Panel")
    finally:
        app.destroy()
```

- [ ] **Step 2: Run to confirm fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_hub_can_navigate_to_each_phase1_tool -v`
Expected: FAIL — `_create_tool_panel` raises `ValueError: Unknown panel key: 'split'`.

- [ ] **Step 3: Re-export panel classes**

Replace `src/anm/gui/panels/__init__.py` content:

```python
"""Tool panels for the Phase 1 page-operation tools."""

from .delete_pages import DeletePagesPanel
from .extract import ExtractPanel
from .reorder import ReorderPanel
from .rotate import RotatePanel
from .split import SplitPanel

__all__ = [
    "DeletePagesPanel",
    "ExtractPanel",
    "ReorderPanel",
    "RotatePanel",
    "SplitPanel",
]
```

- [ ] **Step 4: Extend `_create_tool_panel` in `hub.py`**

In `src/anm/gui/hub.py`, replace the `_create_tool_panel` method:

```python
    def _create_tool_panel(self, key: str) -> ttk.Frame:
        parent = self._tool_chrome.content_area
        common = {
            "status_var":   self.status_var,
            "progress_var": self.progress_var,
            "event_queue":  self.event_queue,
        }
        if key == "annotate_merge":
            from .annotate_merge import AnnotateMergePanel
            return AnnotateMergePanel(parent, **common)
        if key == "split":
            from .panels.split import SplitPanel
            return SplitPanel(parent, **common)
        if key == "rotate":
            from .panels.rotate import RotatePanel
            return RotatePanel(parent, **common)
        if key == "reorder":
            from .panels.reorder import ReorderPanel
            return ReorderPanel(parent, **common)
        if key == "delete_pages":
            from .panels.delete_pages import DeletePagesPanel
            return DeletePagesPanel(parent, **common)
        if key == "extract":
            from .panels.extract import ExtractPanel
            return ExtractPanel(parent, **common)
        raise ValueError(f"Unknown panel key: {key!r}")
```

- [ ] **Step 5: Run integration test to confirm pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py -v`
Expected: 8 passed

- [ ] **Step 6: Run full suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: 75 passed

- [ ] **Step 7: Commit**

```bash
git add src/anm/gui/panels/__init__.py src/anm/gui/hub.py tests/test_panels.py
git commit -m "feat(gui): wire all five Phase 1 panels into the hub"
```

---

## Task 9: End-to-end smoke (real PDF + run)

**Files:**
- Modify: `tests/test_panels.py`

- [ ] **Step 1: Write end-to-end test**

Append to `tests/test_panels.py`:

```python
@pytest.mark.skipif(_HEADLESS, reason="Tk requires a display")
def test_split_panel_runs_each_page_end_to_end(tmp_path: Path) -> None:
    import queue
    import threading
    import time
    import tkinter as tk
    from anm.gui.panels.split import SplitPanel

    pdf = _make_pdf(tmp_path / "src.pdf", num_pages=3)
    out_dir = tmp_path / "out"

    root = tk.Tk()
    root.withdraw()
    try:
        panel = SplitPanel(
            root,
            status_var=tk.StringVar(),
            progress_var=tk.DoubleVar(),
            event_queue=queue.Queue(),
        )
        panel._load_pdf(pdf)
        panel.output_dir_var.set(str(out_dir))
        panel._on_run_clicked()
        # Wait for the worker thread to finish.
        for _ in range(50):
            if not panel._running and not panel.event_queue.empty():
                break
            time.sleep(0.05)
            # Pump the queue ourselves (no mainloop running).
            try:
                evt_type, payload = panel.event_queue.get_nowait()
                panel._handle_event(evt_type, payload)
            except queue.Empty:
                pass
        assert len(list(out_dir.glob("*.pdf"))) == 3
    finally:
        root.destroy()
```

- [ ] **Step 2: Run end-to-end test**

Run: `.venv/Scripts/python.exe -m pytest tests/test_panels.py::test_split_panel_runs_each_page_end_to_end -v`
Expected: PASS (1 passed)

- [ ] **Step 3: Run full suite once more**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: 76 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_panels.py
git commit -m "test(gui): add end-to-end split-panel smoke test"
```

---

## Self-Review

- **Spec coverage:** every Phase 1 tool (split, rotate, reorder, delete, extract) gets one panel; the hub routes to each; thumbnails render real pages; live overlays for delete/extract; threaded run; output dir picker. ✓
- **Placeholders:** none — every step shows the literal code to write.
- **Type consistency:** all panels share the `BaseToolPanel.__init__(parent, *, tool_id, status_var, progress_var, event_queue)` signature; `_build_options()` returns the matching `*Options` dataclass from `anm.tools.*`; hub passes the same three kwargs to every constructor.
