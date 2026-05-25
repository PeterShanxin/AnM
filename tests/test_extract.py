from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.extract import ExtractOptions, extract_pages


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_specific_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D", "E"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="2,4"), output_path=output)

    assert result.pages_extracted == 2
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "B" in doc[0].get_text()
    assert "D" in doc[1].get_text()
    doc.close()


def test_extract_range(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="2-4"), output_path=output)

    assert result.pages_extracted == 3
    doc = fitz.open(output)
    assert doc.page_count == 3
    doc.close()


def test_extract_all(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="all"), output_path=output)

    assert result.pages_extracted == 2


def test_extract_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_pages(
            tmp_path / "missing.pdf",
            ExtractOptions(page_spec="1"),
            output_path=tmp_path / "out.pdf",
        )
