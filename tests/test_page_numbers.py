from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.page_numbers import PageNumbersOptions, add_page_numbers


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_add_page_numbers_default(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 3)
    out = tmp_path / "numbered.pdf"

    result = add_page_numbers(src, PageNumbersOptions(), output_path=out)

    assert result.output_path == out
    assert result.pages_numbered == 3
    assert out.is_file()
    with fitz.open(out) as doc:
        assert doc.page_count == 3


def test_add_page_numbers_skip_first(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 5)
    out = tmp_path / "numbered.pdf"

    result = add_page_numbers(
        src, PageNumbersOptions(skip_first_n=2), output_path=out
    )

    assert result.pages_numbered == 3


def test_add_page_numbers_custom_format(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 2)
    out = tmp_path / "numbered.pdf"

    result = add_page_numbers(
        src, PageNumbersOptions(fmt="- {page} -", start_number=10), output_path=out
    )

    assert result.pages_numbered == 2


def test_add_page_numbers_all_positions(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    positions = [
        "top-left", "top-center", "top-right",
        "bottom-left", "bottom-center", "bottom-right",
    ]
    for pos in positions:
        out = tmp_path / f"numbered_{pos}.pdf"
        result = add_page_numbers(
            src, PageNumbersOptions(position=pos), output_path=out
        )
        assert result.pages_numbered == 1


def test_add_page_numbers_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        add_page_numbers(
            tmp_path / "missing.pdf", PageNumbersOptions(), output_path=tmp_path / "out.pdf"
        )


def test_add_page_numbers_invalid_position(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    with pytest.raises(ValueError, match="Invalid position"):
        add_page_numbers(
            src, PageNumbersOptions(position="middle"), output_path=tmp_path / "out.pdf"
        )


def test_add_page_numbers_invalid_options(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src, 1)
    out = tmp_path / "out.pdf"

    with pytest.raises(ValueError, match="skip_first_n"):
        add_page_numbers(src, PageNumbersOptions(skip_first_n=-1), output_path=out)

    with pytest.raises(ValueError, match="font_size"):
        add_page_numbers(src, PageNumbersOptions(font_size=0), output_path=out)

    with pytest.raises(ValueError, match="opacity"):
        add_page_numbers(src, PageNumbersOptions(opacity=1.5), output_path=out)

    with pytest.raises(ValueError, match="margin"):
        add_page_numbers(src, PageNumbersOptions(margin=-5), output_path=out)

    with pytest.raises(ValueError, match="Invalid page numbers format"):
        add_page_numbers(src, PageNumbersOptions(fmt="Page {bad_token}"), output_path=out)
