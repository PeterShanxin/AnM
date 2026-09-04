from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .page_range import parse_page_range


class ImageFormat(enum.Enum):
    PNG = "png"
    JPEG = "jpeg"


_DPI_SCALE = {72: 1.0, 150: 150 / 72, 300: 300 / 72}


@dataclass(slots=True)
class ToImagesOptions:
    fmt: ImageFormat = ImageFormat.PNG
    dpi: int = 150
    page_spec: str = "all"


@dataclass(slots=True)
class ToImagesResult:
    output_paths: list[Path] = field(default_factory=list)


def pdf_to_images(
    input_path: Path,
    options: ToImagesOptions,
    *,
    output_dir: Path,
) -> ToImagesResult:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scale = _DPI_SCALE.get(options.dpi, options.dpi / 72)
    matrix = fitz.Matrix(scale, scale)
    ext = "jpg" if options.fmt == ImageFormat.JPEG else "png"

    output_paths: list[Path] = []
    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)
        for idx in indices:
            pix = doc[idx].get_pixmap(matrix=matrix, alpha=False)
            out_path = output_dir / f"{input_path.stem}_page_{idx + 1}.{ext}"
            if options.fmt == ImageFormat.JPEG:
                out_path.write_bytes(pix.tobytes("jpeg", jpg_quality=95))
            else:
                pix.save(out_path)
            output_paths.append(out_path)

    return ToImagesResult(output_paths=output_paths)
