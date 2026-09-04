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


def test_compress_preserves_decode_array_rgb_render(tmp_path: Path) -> None:
    src = tmp_path / "decode_inv_rgb.pdf"
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    # Red image (255, 0, 0)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 0)
    pix.clear_with(0)
    for y in range(20):
        for x in range(20):
            pix.set_pixel(x, y, (255, 0, 0))
    page.insert_image(fitz.Rect(10, 10, 90, 90), pixmap=pix)
    xref = doc.get_page_images(0)[0][0]
    # Invert RGB channels with /Decode: [1 0 1 0 1 0]
    doc.xref_set_key(xref, "Decode", "[1 0 1 0 1 0]")
    doc.save(src)
    doc.close()

    # Source renders cyan (0, 255, 255)
    with fitz.open(src) as doc_src:
        src_pix = doc_src[0].get_pixmap()
        orig_color = src_pix.pixel(50, 50)
        assert orig_color[0] < 50 and orig_color[1] > 200 and orig_color[2] > 200

    out = tmp_path / "compressed_rgb.pdf"
    compress_pdf(src, CompressOptions(quality=CompressQuality.MEDIUM), output_path=out)

    with fitz.open(out) as doc_out:
        comp_pix = doc_out[0].get_pixmap()
        comp_color = comp_pix.pixel(50, 50)
        # Must still render cyan within JPEG compression tolerance, NOT red
        assert comp_color[0] < 50, f"Expected red channel < 50, got {comp_color[0]}"
        assert comp_color[1] > 200, f"Expected green channel > 200, got {comp_color[1]}"
        assert comp_color[2] > 200, f"Expected blue channel > 200, got {comp_color[2]}"
        max_delta = max(abs(s - o) for s, o in zip(orig_color, comp_color))
        assert max_delta <= 15, f"Rendered color deviated too far from source: delta {max_delta}"


def test_compress_preserves_decode_array_grayscale_render(tmp_path: Path) -> None:
    src = tmp_path / "decode_inv_gray.pdf"
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    # Black pixel samples in grayscale
    pix = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 20, 20), 0)
    pix.clear_with(0)
    page.insert_image(fitz.Rect(10, 10, 90, 90), pixmap=pix)
    xref = doc.get_page_images(0)[0][0]
    # Invert grayscale channel with /Decode: [1 0] -> black becomes white
    doc.xref_set_key(xref, "Decode", "[1 0]")
    doc.save(src)
    doc.close()

    with fitz.open(src) as doc_src:
        src_pix = doc_src[0].get_pixmap()
        orig_color = src_pix.pixel(50, 50)
        assert orig_color[0] > 240, f"Expected source white, got {orig_color}"

    out = tmp_path / "compressed_gray.pdf"
    compress_pdf(src, CompressOptions(quality=CompressQuality.MEDIUM), output_path=out)

    with fitz.open(out) as doc_out:
        comp_pix = doc_out[0].get_pixmap()
        comp_color = comp_pix.pixel(50, 50)
        # Must still render white, NOT black
        assert comp_color[0] > 240, f"Expected compressed white, got {comp_color}"


def test_compress_skips_transparent_and_masked_images(tmp_path: Path) -> None:
    src = tmp_path / "masked.pdf"
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    # RGBA image with alpha
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 30, 30), 1)
    pix.clear_with(128)
    page.insert_image(fitz.Rect(10, 10, 90, 90), pixmap=pix)
    doc.save(src)
    doc.close()

    out = tmp_path / "compressed_masked.pdf"
    compress_pdf(src, CompressOptions(quality=CompressQuality.LOW), output_path=out)

    with fitz.open(out) as doc_out:
        imgs = doc_out.get_page_images(0)
        # Either SMask was preserved or the image remained unflattened
        assert imgs[0][1] != 0 or fitz.Pixmap(doc_out, imgs[0][0]).alpha
