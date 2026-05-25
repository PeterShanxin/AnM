from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.split import SplitMode, SplitOptions, split_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_split_by_ranges(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 5)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.RANGES, page_spec="1-2,4"),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 2
    doc1 = fitz.open(result.output_paths[0])
    assert doc1.page_count == 2
    doc1.close()
    doc2 = fitz.open(result.output_paths[1])
    assert doc2.page_count == 1
    doc2.close()


def test_split_every_n(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 7)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.EVERY_N, every_n=3),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 3
    counts = [fitz.open(p).page_count for p in result.output_paths]
    assert counts == [3, 3, 1]


def test_split_each_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 4)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.EACH_PAGE),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 4
    for p in result.output_paths:
        doc = fitz.open(p)
        assert doc.page_count == 1
        doc.close()


def test_split_empty_pdf_raises(tmp_path: Path) -> None:
    # Test that empty or invalid PDFs raise an error
    # PyMuPDF doesn't allow creating PDFs with 0 pages, so we use a corrupt file
    source = tmp_path / "empty.pdf"
    # Create a minimal PDF header that has no valid page objects
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")

    # Expect an error when processing invalid PDF
    # FileDataError is raised by fitz when it can't properly open the file
    with pytest.raises(fitz.FileDataError):
        split_pdf(source, SplitOptions(mode=SplitMode.EACH_PAGE), output_dir=tmp_path / "out")


def test_split_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        split_pdf(
            tmp_path / "missing.pdf",
            SplitOptions(mode=SplitMode.EACH_PAGE),
            output_dir=tmp_path / "out",
        )


def test_split_creates_output_dir(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 2)
    out = tmp_path / "nested" / "deep" / "out"

    result = split_pdf(source, SplitOptions(mode=SplitMode.EACH_PAGE), output_dir=out)

    assert out.is_dir()
    assert len(result.output_paths) == 2
