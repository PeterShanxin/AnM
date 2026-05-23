from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.reorder import ReorderOptions, reorder_pdf


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_reorder_reverses(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])
    output = tmp_path / "reordered.pdf"

    reorder_pdf(source, ReorderOptions(order=[3, 2, 1]), output_path=output)

    doc = fitz.open(output)
    assert doc.page_count == 3
    assert "C" in doc[0].get_text()
    assert "B" in doc[1].get_text()
    assert "A" in doc[2].get_text()
    doc.close()


def test_reorder_subset_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])

    with pytest.raises(ValueError, match="must include every page exactly once"):
        reorder_pdf(source, ReorderOptions(order=[1, 2]), output_path=tmp_path / "out.pdf")


def test_reorder_duplicates_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])

    with pytest.raises(ValueError, match="must include every page exactly once"):
        reorder_pdf(source, ReorderOptions(order=[1, 1]), output_path=tmp_path / "out.pdf")


def test_reorder_identity(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["X", "Y"])
    output = tmp_path / "out.pdf"

    reorder_pdf(source, ReorderOptions(order=[1, 2]), output_path=output)

    doc = fitz.open(output)
    assert "X" in doc[0].get_text()
    assert "Y" in doc[1].get_text()
    doc.close()
