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
        imgs = doc.get_page_images(0)
        assert len(imgs) == 1
        pix = fitz.Pixmap(doc, imgs[0][0])
        assert pix.width == 200
        assert pix.height == 200
        page_pix = doc[0].get_pixmap()
        assert page_pix.width > 0


def test_compress_with_grayscale_image(tmp_path: Path) -> None:
    src = tmp_path / "gray.pdf"
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 100, 100), 0)
    pix.clear_with(128)
    page.insert_image(fitz.Rect(50, 50, 150, 150), pixmap=pix)
    doc.save(src)
    doc.close()

    out = tmp_path / "compressed_gray.pdf"
    compress_pdf(src, CompressOptions(quality=CompressQuality.MEDIUM), output_path=out)

    assert out.is_file()
    with fitz.open(out) as doc2:
        imgs = doc2.get_page_images(0)
        assert len(imgs) == 1
        pix2 = fitz.Pixmap(doc2, imgs[0][0])
        assert pix2.width == 100
        assert pix2.height == 100


def test_compress_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compress_pdf(tmp_path / "missing.pdf", CompressOptions(), output_path=tmp_path / "out.pdf")


def test_compress_creates_output_dir(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "nested" / "deep" / "out.pdf"

    compress_pdf(src, CompressOptions(), output_path=out)

    assert out.is_file()
