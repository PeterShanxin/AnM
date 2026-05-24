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
