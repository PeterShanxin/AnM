from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range


@dataclass(slots=True)
class ExtractOptions:
    page_spec: str = ""


@dataclass(slots=True)
class ExtractResult:
    output_path: Path
    pages_extracted: int = 0


def extract_pages(
    input_path: Path,
    options: ExtractOptions,
    *,
    output_path: Path,
) -> ExtractResult:
    """Extract selected pages from a PDF into a new file."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)

        out_doc = fitz.open()
        for idx in indices:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        out_doc.save(output_path)
        out_doc.close()

    return ExtractResult(output_path=output_path, pages_extracted=len(indices))
