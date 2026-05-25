from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.delete_pages import DeletePagesOptions, delete_pages


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_delete_middle_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])
    output = tmp_path / "out.pdf"

    result = delete_pages(source, DeletePagesOptions(page_spec="2"), output_path=output)

    assert result.pages_removed == 1
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "A" in doc[0].get_text()
    assert "C" in doc[1].get_text()
    doc.close()


def test_delete_range(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D", "E"])
    output = tmp_path / "out.pdf"

    result = delete_pages(source, DeletePagesOptions(page_spec="2-4"), output_path=output)

    assert result.pages_removed == 3
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "A" in doc[0].get_text()
    assert "E" in doc[1].get_text()
    doc.close()


def test_delete_all_pages_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])

    with pytest.raises(ValueError, match="Cannot delete all"):
        delete_pages(source, DeletePagesOptions(page_spec="all"), output_path=tmp_path / "out.pdf")


def test_delete_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        delete_pages(
            tmp_path / "missing.pdf",
            DeletePagesOptions(page_spec="1"),
            output_path=tmp_path / "out.pdf",
        )
