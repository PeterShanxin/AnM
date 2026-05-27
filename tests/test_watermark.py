from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.watermark import WatermarkMode, WatermarkOptions, watermark_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_watermark_diagonal(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 2)
    out = tmp_path / "wm.pdf"

    result = watermark_pdf(
        src, WatermarkOptions(text="DRAFT", mode=WatermarkMode.DIAGONAL), output_path=out
    )

    assert result.output_path == out
    assert result.pages_stamped == 2
    assert out.is_file()


def test_watermark_tiled(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "wm.pdf"

    result = watermark_pdf(
        src, WatermarkOptions(text="SECRET", mode=WatermarkMode.TILED), output_path=out
    )

    assert result.pages_stamped == 1
    assert out.is_file()


def test_watermark_header(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "wm.pdf"

    result = watermark_pdf(
        src, WatermarkOptions(text="TOP", mode=WatermarkMode.HEADER), output_path=out
    )

    assert result.pages_stamped == 1


def test_watermark_footer(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "wm.pdf"

    result = watermark_pdf(
        src, WatermarkOptions(text="BOTTOM", mode=WatermarkMode.FOOTER), output_path=out
    )

    assert result.pages_stamped == 1


def test_watermark_page_range(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 5)
    out = tmp_path / "wm.pdf"

    result = watermark_pdf(
        src, WatermarkOptions(text="MARK", page_spec="1,3"), output_path=out
    )

    assert result.pages_stamped == 2


def test_watermark_empty_text_raises(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    with pytest.raises(ValueError, match="empty"):
        watermark_pdf(src, WatermarkOptions(text="   "), output_path=tmp_path / "wm.pdf")


def test_watermark_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        watermark_pdf(
            tmp_path / "missing.pdf", WatermarkOptions(), output_path=tmp_path / "wm.pdf"
        )
