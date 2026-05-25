from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range

VALID_ANGLES = {90, 180, 270}


@dataclass(slots=True)
class RotateOptions:
    angle: int = 90
    page_spec: str = "all"


@dataclass(slots=True)
class RotateResult:
    output_path: Path
    pages_rotated: int = 0


def rotate_pdf(
    input_path: Path,
    options: RotateOptions,
    *,
    output_path: Path,
) -> RotateResult:
    """Rotate selected pages of a PDF by 90, 180, or 270 degrees."""
    if options.angle not in VALID_ANGLES:
        raise ValueError(f"Invalid angle: {options.angle}. Must be one of {sorted(VALID_ANGLES)}.")

    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)
        for idx in indices:
            page = doc[idx]
            page.set_rotation(page.rotation + options.angle)
        doc.save(output_path)

    return RotateResult(output_path=output_path, pages_rotated=len(indices))
