from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

import fitz

_SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

_PAGE_SIZES = {
    "a4": fitz.paper_rect("a4"),
    "letter": fitz.paper_rect("letter"),
}


class PageSize(enum.Enum):
    A4 = "a4"
    LETTER = "letter"
    FIT = "fit"


class Orientation(enum.Enum):
    AUTO = "auto"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass(slots=True)
class FromImagesOptions:
    page_size: PageSize = PageSize.A4
    orientation: Orientation = Orientation.AUTO


@dataclass(slots=True)
class FromImagesResult:
    output_path: Path
    page_count: int = 0


def images_to_pdf(
    image_paths: list[Path],
    options: FromImagesOptions,
    *,
    output_path: Path,
) -> FromImagesResult:
    if not image_paths:
        raise ValueError("No image files provided.")

    resolved = []
    for p in image_paths:
        p = p.resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Image not found: {p}")
        if p.suffix.lower() not in _SUPPORTED_EXTS:
            raise ValueError(f"Unsupported image format: {p.suffix}")
        resolved.append(p)

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    for img_path in resolved:
        pix = fitz.Pixmap(str(img_path))
        img_rect = fitz.Rect(pix.irect)
        pix = None  # release immediately
        page_rect = _compute_page_rect(img_rect, options)
        page = doc.new_page(width=page_rect.width, height=page_rect.height)
        fit_rect = _fit_rect(img_rect, page_rect)
        page.insert_image(fit_rect, filename=str(img_path))

    doc.save(output_path)
    page_count = doc.page_count
    doc.close()

    return FromImagesResult(output_path=output_path, page_count=page_count)


def _compute_page_rect(
    img_rect: fitz.Rect,
    options: FromImagesOptions,
) -> fitz.Rect:
    if options.page_size == PageSize.FIT:
        return fitz.Rect(0, 0, img_rect.width, img_rect.height)

    base = _PAGE_SIZES[options.page_size.value]
    if options.orientation == Orientation.LANDSCAPE:
        return fitz.Rect(0, 0, base.height, base.width)
    if options.orientation == Orientation.PORTRAIT:
        return base
    # auto: match image aspect
    img_landscape = img_rect.width > img_rect.height
    if img_landscape:
        return fitz.Rect(0, 0, base.height, base.width)
    return base


def _fit_rect(img_rect: fitz.Rect, page_rect: fitz.Rect) -> fitz.Rect:
    iw, ih = img_rect.width, img_rect.height
    pw, ph = page_rect.width, page_rect.height
    scale = min(pw / iw, ph / ih)
    w, h = iw * scale, ih * scale
    x0 = (pw - w) / 2
    y0 = (ph - h) / 2
    return fitz.Rect(x0, y0, x0 + w, y0 + h)
