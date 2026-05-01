from __future__ import annotations

from pathlib import Path
from threading import Event

import fitz
import pytest

from anm.models import AnnotationOptions, RunOptions
from anm.pipeline import (
    CancelledError,
    annotate_page,
    build_annotation_rect,
    process_pdfs,
    resolve_output_path,
)


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_resolve_output_path_defaults_to_output_folder(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"fake")

    output_path = resolve_output_path([pdf_path], RunOptions())

    assert output_path == tmp_path / "output" / "annotated-merged.pdf"


def test_build_annotation_rect_for_top_center() -> None:
    rect, _ = build_annotation_rect(
        fitz.Rect(0, 0, 600, 800),
        "sample.pdf",
        AnnotationOptions(position="top-center", font_size=12, margin=24),
    )

    assert rect.y0 == 24
    assert rect.x0 > 0
    assert rect.x1 < 600


def test_annotate_page_inserts_resolved_template_text(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()

    annotate_page(page, source, AnnotationOptions(), file_index=1, page_number=1, total_pages=1)

    assert "sample.pdf" in page.get_text()
    document.close()


def test_annotate_page_skips_blank_template(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "original")

    annotate_page(
        page,
        source,
        AnnotationOptions(text_template=" "),
        file_index=1,
        page_number=1,
        total_pages=1,
    )

    assert page.get_text().strip() == "original"
    assert page.get_drawings() == []
    document.close()


def test_process_pdfs_merges_in_selected_order_and_cleans_temp_dir(tmp_path: Path) -> None:
    source_a = tmp_path / "page2.pdf"
    source_b = tmp_path / "page10.pdf"
    make_pdf(source_a, "Second")
    make_pdf(source_b, "Tenth")

    result = process_pdfs(
        [source_b, source_a],
        AnnotationOptions(),
        RunOptions(save_intermediate=False, overwrite=True),
    )

    assert result.merged_pdf_path == tmp_path / "output" / "annotated-merged.pdf"
    assert result.merged_pdf_path.exists()
    assert not (tmp_path / "output" / ".tmp").exists()

    merged = fitz.open(result.merged_pdf_path)
    assert merged.page_count == 2
    merged.close()


def test_process_pdfs_keeps_intermediate_files_when_requested(tmp_path: Path) -> None:
    source = tmp_path / "page1.pdf"
    make_pdf(source, "hello")

    result = process_pdfs(
        [source],
        AnnotationOptions(),
        RunOptions(save_intermediate=True, overwrite=True),
    )

    assert result.intermediate_paths
    assert all(path.exists() for path in result.intermediate_paths)
    assert (tmp_path / "output" / "annotated").exists()


def test_process_pdfs_cleans_temp_dir_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "page1.pdf"
    make_pdf(source, "hello")

    from anm import pipeline

    original = pipeline.annotate_page

    def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        original(*args, **kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline, "annotate_page", explode)

    with pytest.raises(RuntimeError, match="boom"):
        process_pdfs([source], AnnotationOptions(), RunOptions(overwrite=True))

    assert not (tmp_path / "output" / ".tmp").exists()


def test_process_pdfs_supports_cancellation(tmp_path: Path) -> None:
    source = tmp_path / "page1.pdf"
    make_pdf(source, "hello")
    cancel_event = Event()
    cancel_event.set()

    with pytest.raises(CancelledError):
        process_pdfs(
            [source],
            AnnotationOptions(),
            RunOptions(overwrite=True),
            cancel_event=cancel_event,
        )
