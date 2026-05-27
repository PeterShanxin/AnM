from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.compress import CompressOptions, CompressQuality, compress_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def make_pdf_with_image(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200), 0)
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(fitz.Rect(50, 50, 250, 250), pixmap=pix)
    doc.save(path)
    doc.close()


def test_compress_high(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 3)
    out = tmp_path / "compressed.pdf"

    result = compress_pdf(src, CompressOptions(quality=CompressQuality.HIGH), output_path=out)

    assert result.output_path == out
    assert out.is_file()
    assert result.original_size > 0
    assert result.compressed_size > 0
    with fitz.open(out) as doc:
        assert doc.page_count == 3


def test_compress_medium(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 2)
    out = tmp_path / "compressed.pdf"

    result = compress_pdf(src, CompressOptions(quality=CompressQuality.MEDIUM), output_path=out)

    assert out.is_file()
    assert result.compressed_size > 0


def test_compress_with_image(tmp_path: Path) -> None:
    src = tmp_path / "img.pdf"
    make_pdf_with_image(src)
    out = tmp_path / "compressed.pdf"

    compress_pdf(src, CompressOptions(quality=CompressQuality.LOW), output_path=out)

    assert out.is_file()
    with fitz.open(out) as doc:
        assert doc.page_count == 1


def test_compress_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compress_pdf(tmp_path / "missing.pdf", CompressOptions(), output_path=tmp_path / "out.pdf")


def test_compress_creates_output_dir(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "nested" / "deep" / "out.pdf"

    compress_pdf(src, CompressOptions(), output_path=out)

    assert out.is_file()
