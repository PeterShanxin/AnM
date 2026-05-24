from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .page_range import parse_page_range


class SplitMode(enum.Enum):
    RANGES = "ranges"
    EVERY_N = "every_n"
    EACH_PAGE = "each_page"


@dataclass(slots=True)
class SplitOptions:
    mode: SplitMode = SplitMode.EACH_PAGE
    page_spec: str = ""
    every_n: int = 1


@dataclass(slots=True)
class SplitResult:
    output_paths: list[Path] = field(default_factory=list)


def split_pdf(
    input_path: Path,
    options: SplitOptions,
    *,
    output_dir: Path,
) -> SplitResult:
    """Split a PDF into multiple files based on the given mode."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    with fitz.open(input_path) as doc:
        total = doc.page_count
        if total == 0:
            raise ValueError(f"{input_path.name} has no pages.")

        chunks = _compute_chunks(options, total)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.stem
        output_paths: list[Path] = []

        for chunk_index, page_indices in enumerate(chunks, start=1):
            out_doc = fitz.open()
            for page_index in page_indices:
                out_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)

            name = _chunk_filename(stem, page_indices, chunk_index, options.mode)
            out_path = output_dir / name
            out_doc.save(out_path)
            out_doc.close()
            output_paths.append(out_path)

    return SplitResult(output_paths=output_paths)


def _compute_chunks(options: SplitOptions, total: int) -> list[list[int]]:
    if options.mode == SplitMode.EACH_PAGE:
        return [[i] for i in range(total)]

    if options.mode == SplitMode.EVERY_N:
        if options.every_n <= 0:
            raise ValueError(
                f"every_n must be a positive integer, got {options.every_n}"
            )
        n = options.every_n
        return [list(range(i, min(i + n, total))) for i in range(0, total, n)]

    if options.mode == SplitMode.RANGES:
        # Parse each comma-separated segment individually so that boundaries
        # between user-specified segments are always honoured.  Merging via a
        # flat sorted list (the old approach) collapsed contiguous segments
        # like "1-2,3-4" into a single chunk.
        chunks: list[list[int]] = []
        for seg in options.page_spec.split(","):
            seg = seg.strip()
            if seg:
                indices = parse_page_range(seg, total_pages=total)
                if indices:
                    chunks.append(indices)
        return chunks

    raise ValueError(f"Unknown split mode: {options.mode}")


def _chunk_filename(stem: str, indices: list[int], chunk_index: int, mode: SplitMode) -> str:
    if mode == SplitMode.EACH_PAGE:
        return f"{stem}_page_{indices[0] + 1}.pdf"
    if len(indices) == 1:
        return f"{stem}_page_{indices[0] + 1}.pdf"
    return f"{stem}_pages_{indices[0] + 1}-{indices[-1] + 1}.pdf"
