from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Callable

import fitz

from .models import POSITION_CONFIG, AnnotationOptions, RunOptions, RunResult

ProgressCallback = Callable[[dict[str, object]], None]


class CancelledError(RuntimeError):
    """Raised when the current merge run is cancelled."""


def resolve_text_template(
    template: str,
    source_path: Path,
    file_index: int,
    page_number: int,
    total_pages: int,
) -> str:
    return template.format(
        filename=source_path.name,
        stem=source_path.stem,
        index=file_index,
        page_number=page_number,
        total_pages=total_pages,
    )


def build_annotation_rect(
    page_rect: fitz.Rect,
    text: str,
    options: AnnotationOptions,
) -> tuple[fitz.Rect, int]:
    horizontal, vertical = POSITION_CONFIG[options.position]
    padding_x = 6
    padding_y = 4
    font = fitz.Font("helv")
    text_width = fitz.get_text_length(text, fontsize=options.font_size)
    max_width = max(page_rect.width - (options.margin * 2), 80)
    width = min(text_width + (padding_x * 2), max_width)
    line_height = (font.ascender - font.descender) * options.font_size
    height = line_height + (padding_y * 2)

    if horizontal == "left":
        x0 = options.margin
    elif horizontal == "center":
        x0 = (page_rect.width - width) / 2
    else:
        x0 = page_rect.width - options.margin - width

    if vertical == "top":
        y0 = options.margin
    else:
        y0 = page_rect.height - options.margin - height

    rect = fitz.Rect(x0, y0, x0 + width, y0 + height)
    align_map = {"left": 0, "center": 1, "right": 2}
    return rect, align_map[horizontal]


def annotate_page(
    page: fitz.Page,
    source_path: Path,
    options: AnnotationOptions,
    file_index: int,
    page_number: int,
    total_pages: int,
) -> None:
    text = resolve_text_template(
        options.text_template,
        source_path,
        file_index,
        page_number,
        total_pages,
    )
    if not text.strip():
        return
    rect, align = build_annotation_rect(page.rect, text, options)
    page.draw_rect(
        rect,
        color=(1, 1, 1),
        fill=(1, 1, 1),
        stroke_opacity=options.box_opacity,
        fill_opacity=options.box_opacity,
    )
    page.insert_textbox(rect, text, fontsize=options.font_size, color=(0, 0, 0), align=align)


def default_output_dir(pdf_paths: list[Path]) -> Path:
    if not pdf_paths:
        return Path.cwd() / "output"
    return pdf_paths[0].resolve().parent / "output"


def resolve_output_path(pdf_paths: list[Path], options: RunOptions) -> Path:
    output_dir = (options.output_dir or default_output_dir(pdf_paths)).resolve()
    return output_dir / options.output_filename


def _emit(callback: ProgressCallback | None, **payload: object) -> None:
    if callback is not None:
        callback(payload)


def _check_cancel(cancel_event: object | None) -> None:
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise CancelledError("Merge cancelled.")


def process_pdfs(
    pdf_paths: list[Path],
    annotation_options: AnnotationOptions,
    run_options: RunOptions,
    progress_callback: ProgressCallback | None = None,
    cancel_event: object | None = None,
) -> RunResult:
    if not pdf_paths:
        raise FileNotFoundError("No PDF files selected.")

    output_dir = (run_options.output_dir or default_output_dir(pdf_paths)).resolve()
    annotated_dir = output_dir / "annotated"
    temp_dir = output_dir / ".tmp" / uuid.uuid4().hex
    merged_path = output_dir / run_options.output_filename

    if merged_path.exists() and not run_options.overwrite:
        raise FileExistsError(f"Output file already exists: {merged_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if run_options.save_intermediate:
        annotated_dir.mkdir(parents=True, exist_ok=True)
        working_dir = annotated_dir
    else:
        temp_dir.mkdir(parents=True, exist_ok=True)
        working_dir = temp_dir

    annotated_files: list[Path] = []

    try:
        total_files = len(pdf_paths)
        for file_index, source_path in enumerate(pdf_paths, start=1):
            _check_cancel(cancel_event)
            _emit(
                progress_callback,
                stage="file-start",
                current_file=file_index,
                total_files=total_files,
                path=str(source_path),
                message=f"Annotating {source_path.name}",
            )
            with fitz.open(source_path) as document:
                total_pages = document.page_count
                for page_number, page in enumerate(document, start=1):
                    _check_cancel(cancel_event)
                    annotate_page(
                        page,
                        source_path,
                        annotation_options,
                        file_index,
                        page_number,
                        total_pages,
                    )
                    _emit(
                        progress_callback,
                        stage="page",
                        current_file=file_index,
                        total_files=total_files,
                        current_page=page_number,
                        total_pages=total_pages,
                        path=str(source_path),
                        message=f"Annotated {source_path.name} page {page_number}/{total_pages}",
                    )
                annotated_path = working_dir / f"annotated_{source_path.name}"
                document.save(annotated_path)
                annotated_files.append(annotated_path)

        _check_cancel(cancel_event)
        _emit(progress_callback, stage="merge", message="Merging annotated files")
        with fitz.open() as merged_document:
            for annotated_path in annotated_files:
                _check_cancel(cancel_event)
                with fitz.open(annotated_path) as document:
                    merged_document.insert_pdf(document)
            merged_document.save(merged_path)

        _emit(progress_callback, stage="done", message=f"Created {merged_path}")
        return RunResult(
            merged_pdf_path=merged_path,
            intermediate_paths=annotated_files,
            output_dir=output_dir,
        )
    finally:
        if not run_options.save_intermediate and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            tmp_root = temp_dir.parent
            if tmp_root.exists() and not any(tmp_root.iterdir()):
                tmp_root.rmdir()


def render_preview_png(
    source_path: Path,
    annotation_options: AnnotationOptions,
    file_index: int = 1,
    scale: float = 1.0,
) -> bytes:
    with fitz.open(source_path) as source_document:
        preview_document = fitz.open()
        preview_document.insert_pdf(source_document, from_page=0, to_page=0)
        page = preview_document[0]
        annotate_page(
            page,
            source_path,
            annotation_options,
            file_index=file_index,
            page_number=1,
            total_pages=1,
        )
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        png_bytes = pixmap.tobytes("png")
        preview_document.close()
        return png_bytes


def open_output_folder(path: Path) -> None:
    resolved = path.resolve()
    if os.name == "nt":
        subprocess.Popen(["explorer", str(resolved)])
        return
    try:
        if shutil.which("open"):
            subprocess.Popen(["open", str(resolved)])
            return
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(resolved)])
    except OSError:
        return
