from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range


@dataclass(slots=True)
class DeletePagesOptions:
    page_spec: str = ""


@dataclass(slots=True)
class DeletePagesResult:
    output_path: Path
    pages_removed: int = 0


def delete_pages(
    input_path: Path,
    options: DeletePagesOptions,
    *,
    output_path: Path,
) -> DeletePagesResult:
    """Remove selected pages from a PDF."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        total = doc.page_count
        to_delete = parse_page_range(options.page_spec, total_pages=total)

        if len(to_delete) >= total:
            raise ValueError("Cannot delete all pages from a PDF.")

        keep = [i for i in range(total) if i not in set(to_delete)]
        out_doc = fitz.open()
        for idx in keep:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        out_doc.save(output_path)
        out_doc.close()

    return DeletePagesResult(output_path=output_path, pages_removed=len(to_delete))
