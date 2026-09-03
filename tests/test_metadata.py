from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.metadata import MetadataOptions, read_metadata, write_metadata


def make_pdf(path: Path, num_pages: int = 1) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_read_metadata(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)

    meta = read_metadata(src)

    assert isinstance(meta, dict)


def test_write_metadata(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)
    out = tmp_path / "updated.pdf"

    result = write_metadata(
        src,
        MetadataOptions(fields={"title": "My Title", "author": "Test Author"}),
        output_path=out,
    )

    assert result.output_path == out
    assert out.is_file()
    assert result.metadata["title"] == "My Title"
    assert result.metadata["author"] == "Test Author"


def test_read_back_written_metadata(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)
    out = tmp_path / "updated.pdf"

    write_metadata(
        src,
        MetadataOptions(fields={"subject": "Testing", "keywords": "pdf,test"}),
        output_path=out,
    )
    meta = read_metadata(out)

    assert meta["subject"] == "Testing"
    assert meta["keywords"] == "pdf,test"


def test_clear_metadata_fields(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)
    with_meta = tmp_path / "with_meta.pdf"
    write_metadata(
        src,
        MetadataOptions(fields={"title": "Initial Title", "author": "Initial Author"}),
        output_path=with_meta,
    )

    cleared = tmp_path / "cleared.pdf"
    result = write_metadata(
        with_meta,
        MetadataOptions(fields={"title": ""}),
        output_path=cleared,
    )

    assert "title" not in result.metadata
    assert result.metadata.get("author") == "Initial Author"

    read_back = read_metadata(cleared)
    assert "title" not in read_back
    assert read_back.get("author") == "Initial Author"


def test_write_metadata_invalid_key(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)
    with pytest.raises(ValueError, match="Invalid metadata key"):
        write_metadata(
            src,
            MetadataOptions(fields={"badkey": "value"}),
            output_path=tmp_path / "out.pdf",
        )


def test_read_metadata_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_metadata(tmp_path / "missing.pdf")


def test_write_metadata_creates_output_dir(tmp_path: Path) -> None:
    src = tmp_path / "source.pdf"
    make_pdf(src)
    out = tmp_path / "nested" / "deep" / "out.pdf"

    write_metadata(src, MetadataOptions(fields={"title": "Test"}), output_path=out)

    assert out.is_file()
