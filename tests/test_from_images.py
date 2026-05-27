from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.from_images import (
    FromImagesOptions,
    Orientation,
    PageSize,
    images_to_pdf,
)


def make_image(path: Path, width: int = 200, height: int = 300) -> None:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 0)
    pix.set_rect(pix.irect, (100, 150, 200))
    pix.save(str(path))


def test_images_to_pdf_a4(tmp_path: Path) -> None:
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    make_image(img1)
    make_image(img2)
    out = tmp_path / "album.pdf"

    result = images_to_pdf([img1, img2], FromImagesOptions(), output_path=out)

    assert result.output_path == out
    assert result.page_count == 2
    assert out.is_file()


def test_images_to_pdf_fit(tmp_path: Path) -> None:
    img = tmp_path / "wide.png"
    make_image(img, width=800, height=200)
    out = tmp_path / "fit.pdf"

    result = images_to_pdf(
        [img], FromImagesOptions(page_size=PageSize.FIT), output_path=out
    )

    assert result.page_count == 1
    with fitz.open(out) as doc:
        rect = doc[0].rect
        assert rect.width == 800
        assert rect.height == 200


def test_images_to_pdf_landscape(tmp_path: Path) -> None:
    img = tmp_path / "img.png"
    make_image(img, width=400, height=200)
    out = tmp_path / "landscape.pdf"

    result = images_to_pdf(
        [img],
        FromImagesOptions(orientation=Orientation.LANDSCAPE),
        output_path=out,
    )

    assert result.page_count == 1
    with fitz.open(out) as doc:
        rect = doc[0].rect
        assert rect.width > rect.height


def test_images_to_pdf_empty_raises() -> None:
    with pytest.raises(ValueError, match="No image"):
        images_to_pdf([], FromImagesOptions(), output_path=Path("out.pdf"))


def test_images_to_pdf_missing_image(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        images_to_pdf(
            [tmp_path / "missing.png"],
            FromImagesOptions(),
            output_path=tmp_path / "out.pdf",
        )


def test_images_to_pdf_unsupported_format(tmp_path: Path) -> None:
    bad = tmp_path / "file.txt"
    bad.write_text("not an image")
    with pytest.raises(ValueError, match="Unsupported"):
        images_to_pdf([bad], FromImagesOptions(), output_path=tmp_path / "out.pdf")
