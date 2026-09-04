from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

import fitz


class CompressQuality(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_JPEG_QUALITY = {
    CompressQuality.HIGH: 90,
    CompressQuality.MEDIUM: 65,
    CompressQuality.LOW: 35,
}


@dataclass(slots=True)
class CompressOptions:
    quality: CompressQuality = CompressQuality.MEDIUM


@dataclass(slots=True)
class CompressResult:
    output_path: Path
    original_size: int = 0
    compressed_size: int = 0


def compress_pdf(
    input_path: Path,
    options: CompressOptions,
    *,
    output_path: Path,
) -> CompressResult:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")
    original_size = input_path.stat().st_size

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        if options.quality != CompressQuality.HIGH:
            _recompress_images(doc, _JPEG_QUALITY[options.quality])
        doc.save(output_path, garbage=4, deflate=True, clean=True)

    compressed_size = output_path.stat().st_size
    return CompressResult(
        output_path=output_path,
        original_size=original_size,
        compressed_size=compressed_size,
    )


def _recompress_images(doc: fitz.Document, jpeg_quality: int) -> None:
    processed: set[int] = set()
    for page_num in range(doc.page_count):
        for img_info in doc.get_page_images(page_num, full=True):
            xref = img_info[0]
            if xref in processed:
                continue
            processed.add(xref)
            smask = img_info[1] if len(img_info) > 1 else 0
            if smask:
                continue
            if doc.xref_get_key(xref, "SMask")[0] != "null":
                continue
            if doc.xref_get_key(xref, "Mask")[0] != "null":
                continue
            if doc.xref_get_key(xref, "ImageMask")[1] == "true":
                continue
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue
            if pix.width < 8 or pix.height < 8:
                continue
            if pix.alpha:
                continue
            if pix.colorspace and (pix.colorspace.n == 1 or "gray" in pix.colorspace.name.lower()):
                cs_name = "/DeviceGray"
            else:
                if pix.colorspace is None or pix.colorspace.n != 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                cs_name = "/DeviceRGB"
            try:
                img_bytes = pix.tobytes("jpeg", jpg_quality=jpeg_quality)
            except Exception:
                continue
            doc.update_stream(xref, img_bytes, compress=False)
            doc.xref_set_key(xref, "Filter", "/DCTDecode")
            doc.xref_set_key(xref, "DecodeParms", "null")
            doc.xref_set_key(xref, "Decode", "null")
            doc.xref_set_key(xref, "Width", str(pix.width))
            doc.xref_set_key(xref, "Height", str(pix.height))
            doc.xref_set_key(xref, "ColorSpace", cs_name)
            doc.xref_set_key(xref, "BitsPerComponent", "8")
            doc.xref_set_key(xref, "SMaskInData", "null")
            doc.xref_set_key(xref, "Alternates", "null")
