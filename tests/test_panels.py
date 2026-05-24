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
