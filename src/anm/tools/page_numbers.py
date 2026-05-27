from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

POSITION_CONFIG: dict[str, tuple[str, str]] = {
    "top-left": ("left", "top"),
    "top-center": ("center", "top"),
    "top-right": ("right", "top"),
    "bottom-left": ("left", "bottom"),
    "bottom-center": ("center", "bottom"),
    "bottom-right": ("right", "bottom"),
}


@dataclass(slots=True)
class PageNumbersOptions:
    fmt: str = "Page {page} of {total}"
    position: str = "bottom-center"
    start_number: int = 1
    skip_first_n: int = 0
    font_size: int = 10
    opacity: float = 0.7
    margin: int = 24


@dataclass(slots=True)
class PageNumbersResult:
    output_path: Path
    pages_numbered: int = 0


def add_page_numbers(
    input_path: Path,
    options: PageNumbersOptions,
    *,
    output_path: Path,
) -> PageNumbersResult:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")
    if options.position not in POSITION_CONFIG:
        raise ValueError(f"Invalid position: {options.position}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        total = doc.page_count
        numbered = 0
        for page_idx in range(total):
            if page_idx < options.skip_first_n:
                continue
            page_num = options.start_number + page_idx - options.skip_first_n
            text = options.fmt.format(page=page_num, total=total)
            _insert_number(doc[page_idx], text, options)
            numbered += 1
        doc.save(output_path)

    return PageNumbersResult(output_path=output_path, pages_numbered=numbered)


def _insert_number(
    page: fitz.Page,
    text: str,
    options: PageNumbersOptions,
) -> None:
    rect = page.rect
    horizontal, vertical = POSITION_CONFIG[options.position]
    tw = fitz.get_text_length(text, fontsize=options.font_size)
    margin = options.margin

    if horizontal == "left":
        x = margin
    elif horizontal == "center":
        x = (rect.width - tw) / 2
    else:
        x = rect.width - margin - tw

    if vertical == "top":
        y = margin + options.font_size
    else:
        y = rect.height - margin

    page.insert_text(
        fitz.Point(x, y),
        text,
        fontsize=options.font_size,
        color=(0, 0, 0),
        overlay=True,
        stroke_opacity=options.opacity,
        fill_opacity=options.opacity,
    )
