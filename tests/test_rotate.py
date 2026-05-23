from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.rotate import RotateOptions, rotate_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_rotate_all_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 3)
    output = tmp_path / "rotated.pdf"

    result = rotate_pdf(source, RotateOptions(angle=90, page_spec="all"), output_path=output)

    assert result.output_path == output
    doc = fitz.open(output)
    for page in doc:
        assert page.rotation == 90
    doc.close()


def test_rotate_specific_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 4)
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, RotateOptions(angle=180, page_spec="1,3"), output_path=output)

    doc = fitz.open(output)
    assert doc[0].rotation == 180
    assert doc[1].rotation == 0
    assert doc[2].rotation == 180
    assert doc[3].rotation == 0
    doc.close()


def test_rotate_270(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, RotateOptions(angle=270, page_spec="all"), output_path=output)

    doc = fitz.open(output)
    assert doc[0].rotation == 270
    doc.close()


def test_rotate_invalid_angle_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)

    with pytest.raises(ValueError, match="angle"):
        rotate_pdf(
            source,
            RotateOptions(angle=45, page_spec="all"),
            output_path=tmp_path / "out.pdf",
        )


def test_rotate_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rotate_pdf(
            tmp_path / "missing.pdf",
            RotateOptions(angle=90, page_spec="all"),
            output_path=tmp_path / "out.pdf",
        )
