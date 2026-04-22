from __future__ import annotations

from pathlib import Path

import pytest

from anm.gui import PDFAnnotatorApp


@pytest.mark.skipif(
    "win" not in __import__("sys").platform and not __import__("os").environ.get("DISPLAY"),
    reason="Tk requires a display",
)
def test_app_instantiates_and_models_file_order(tmp_path: Path) -> None:
    for name in ["page2.pdf", "page10.pdf"]:
        (tmp_path / name).write_bytes(b"")

    app = PDFAnnotatorApp()
    app.withdraw()
    app.add_paths([tmp_path])

    rows = app.model.get_display_rows()
    assert [row[1] for row in rows] == ["page2.pdf", "page10.pdf"]
    assert "output" in app.output_dir_var.get()

    app.destroy()
