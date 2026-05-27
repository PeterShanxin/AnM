from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range


class WatermarkMode(enum.Enum):
    DIAGONAL = "diagonal"
    TILED = "tiled"
    HEADER = "header"
    FOOTER = "footer"


@dataclass(slots=True)
class WatermarkOptions:
    text: str = "CONFIDENTIAL"
    font_size: int = 48
    opacity: float = 0.3
    rotation: int = 45
    mode: WatermarkMode = WatermarkMode.DIAGONAL
    color: tuple[float, float, float] = (0.5, 0.5, 0.5)
    page_spec: str = "all"


@dataclass(slots=True)
class WatermarkResult:
    output_path: Path
    pages_stamped: int = 0


def watermark_pdf(
    input_path: Path,
    options: WatermarkOptions,
    *,
    output_path: Path,
) -> WatermarkResult:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")
    if not options.text.strip():
        raise ValueError("Watermark text must not be empty.")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)
        for idx in indices:
            page = doc[idx]
            if options.mode == WatermarkMode.TILED:
                _stamp_tiled(page, options)
            elif options.mode in (WatermarkMode.HEADER, WatermarkMode.FOOTER):
                _stamp_header_footer(page, options)
            else:
                _stamp_diagonal(page, options)
        doc.save(output_path)

    return WatermarkResult(output_path=output_path, pages_stamped=len(indices))


def _stamp_diagonal(page: fitz.Page, opts: WatermarkOptions) -> None:
    rect = page.rect
    cx, cy = rect.width / 2, rect.height / 2
    tw = fitz.get_text_length(opts.text, fontsize=opts.font_size)
    morph = (fitz.Point(cx, cy), fitz.Matrix(1, 0, 0, 1, 0, 0).prerotate(-opts.rotation))
    page.insert_text(
        fitz.Point(cx - tw / 2, cy + opts.font_size / 3),
        opts.text,
        fontsize=opts.font_size,
        color=opts.color,
        overlay=True,
        morph=morph,
        stroke_opacity=opts.opacity,
        fill_opacity=opts.opacity,
    )


def _stamp_tiled(page: fitz.Page, opts: WatermarkOptions) -> None:
    rect = page.rect
    tw = fitz.get_text_length(opts.text, fontsize=opts.font_size)
    spacing_x = tw + 80
    spacing_y = opts.font_size * 3 + 60
    rad = math.radians(opts.rotation)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    y = -rect.height * 0.5
    while y < rect.height * 1.5:
        x = -rect.width * 0.5
        while x < rect.width * 1.5:
            px = x * cos_a + y * sin_a
            py = -x * sin_a + y * cos_a
            if 0 <= px <= rect.width and 0 <= py <= rect.height:
                morph = (
                    fitz.Point(px, py),
                    fitz.Matrix(1, 0, 0, 1, 0, 0).prerotate(-opts.rotation),
                )
                page.insert_text(
                    fitz.Point(px - tw / 2, py + opts.font_size / 3),
                    opts.text,
                    fontsize=opts.font_size,
                    color=opts.color,
                    overlay=True,
                    morph=morph,
                    stroke_opacity=opts.opacity,
                    fill_opacity=opts.opacity,
                )
            x += spacing_x
        y += spacing_y


def _stamp_header_footer(page: fitz.Page, opts: WatermarkOptions) -> None:
    rect = page.rect
    tw = fitz.get_text_length(opts.text, fontsize=opts.font_size)
    x = (rect.width - tw) / 2
    margin = 24
    if opts.mode == WatermarkMode.HEADER:
        y = margin + opts.font_size
    else:
        y = rect.height - margin
    page.insert_text(
        fitz.Point(x, y),
        opts.text,
        fontsize=opts.font_size,
        color=opts.color,
        overlay=True,
        stroke_opacity=opts.opacity,
        fill_opacity=opts.opacity,
    )
