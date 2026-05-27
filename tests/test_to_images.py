from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.to_images import ImageFormat, ToImagesOptions, pdf_to_images


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_to_images_png(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 3)
    out = tmp_path / "images"

    result = pdf_to_images(src, ToImagesOptions(fmt=ImageFormat.PNG, dpi=72), output_dir=out)

    assert len(result.output_paths) == 3
    for p in result.output_paths:
        assert p.suffix == ".png"
        assert p.is_file()


def test_to_images_jpeg(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 2)
    out = tmp_path / "images"

    result = pdf_to_images(src, ToImagesOptions(fmt=ImageFormat.JPEG, dpi=150), output_dir=out)

    assert len(result.output_paths) == 2
    for p in result.output_paths:
        assert p.suffix == ".jpg"


def test_to_images_page_range(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 5)
    out = tmp_path / "images"

    result = pdf_to_images(
        src, ToImagesOptions(page_spec="1,3,5"), output_dir=out
    )

    assert len(result.output_paths) == 3


def test_to_images_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pdf_to_images(tmp_path / "missing.pdf", ToImagesOptions(), output_dir=tmp_path / "out")


def test_to_images_300dpi(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "images"

    result = pdf_to_images(src, ToImagesOptions(dpi=300), output_dir=out)

    assert len(result.output_paths) == 1
    assert result.output_paths[0].is_file()
