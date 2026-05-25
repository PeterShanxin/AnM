from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz


@dataclass(slots=True)
class ReorderOptions:
    order: list[int] = field(default_factory=list)


@dataclass(slots=True)
class ReorderResult:
    output_path: Path


def reorder_pdf(
    input_path: Path,
    options: ReorderOptions,
    *,
    output_path: Path,
) -> ReorderResult:
    """Reorder pages of a PDF. `order` is a list of 1-based page numbers."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    with fitz.open(input_path) as doc:
        total = doc.page_count
        expected = set(range(1, total + 1))
        provided = options.order

        if set(provided) != expected or len(provided) != total:
            raise ValueError(
                f"Order must include every page exactly once (1-{total}). "
                f"Got: {provided}"
            )

        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        out_doc = fitz.open()
        for page_num in provided:
            out_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
        out_doc.save(output_path)
        out_doc.close()

    return ReorderResult(output_path=output_path)
