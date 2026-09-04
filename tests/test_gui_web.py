"""Tests for the gui_web Api bridge + ``_dispatch_tool``.

These cover the JS↔Python contract that the SPA depends on:

- ``_dispatch_tool`` correctly maps tool_id + options dicts to ``tools/*``
  callable invocations and returns the expected payload shape.
- ``Api`` envelope methods always return ``{"ok": True, "data": ...}`` or
  ``{"ok": False, "error": "..."}`` — they never raise across the bridge.
- ``Api.open_pdfs_dialog`` is not exercised here (needs a live webview
  window), but its return-shape contract is asserted via ``Api.run_merge``
  on a pre-built file list.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.gui_web.app import Api, _dispatch_tool


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


# ───────────────────────── _dispatch_tool ──────────────────────────────


def test_dispatch_split_ranges(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 6)
    out_dir = tmp_path / "out"

    result = _dispatch_tool("split", src, out_dir, {
        "mode": "ranges",
        "page_spec": "1-3, 4-6",
    })

    assert "outputs" in result and "summary" in result
    assert len(result["outputs"]) == 2
    assert all(Path(p).exists() for p in result["outputs"])


def test_dispatch_split_every_n(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 5)
    out_dir = tmp_path / "out"

    result = _dispatch_tool("split", src, out_dir, {
        "mode": "every_n",
        "every_n": 2,
    })

    # 5 pages / 2 = 3 chunks (2+2+1)
    assert len(result["outputs"]) == 3


def test_dispatch_split_each_page(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)
    out_dir = tmp_path / "out"

    result = _dispatch_tool("split", src, out_dir, {"mode": "each_page"})

    assert len(result["outputs"]) == 3


def test_dispatch_split_unknown_mode(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)

    with pytest.raises(ValueError, match="Unknown split mode"):
        _dispatch_tool("split", src, tmp_path / "out", {"mode": "bogus"})


def test_dispatch_rotate(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)

    result = _dispatch_tool("rotate", src, tmp_path / "out", {
        "angle": 90,
        "page_spec": "all",
    })

    assert len(result["outputs"]) == 1
    assert Path(result["outputs"][0]).exists()
    assert "Rotated 3 page" in result["summary"]


def test_dispatch_extract(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 5)

    result = _dispatch_tool("extract", src, tmp_path / "out", {
        "page_spec": "1,3",
    })

    out = Path(result["outputs"][0])
    with fitz.open(out) as doc:
        assert doc.page_count == 2


def test_dispatch_delete(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 5)

    result = _dispatch_tool("delete", src, tmp_path / "out", {
        "page_spec": "2,4",
    })

    out = Path(result["outputs"][0])
    with fitz.open(out) as doc:
        assert doc.page_count == 3


def test_dispatch_reorder(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)

    result = _dispatch_tool("reorder", src, tmp_path / "out", {
        "order": [3, 1, 2],
    })

    out = Path(result["outputs"][0])
    with fitz.open(out) as doc:
        assert doc.page_count == 3


def test_dispatch_reorder_rejects_non_list(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)

    with pytest.raises(ValueError, match="'order' must be a list"):
        _dispatch_tool("reorder", src, tmp_path / "out", {"order": "3,1,2"})


def test_dispatch_compress(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 2)

    result = _dispatch_tool("compress", src, tmp_path / "out", {"quality": "medium"})

    assert len(result["outputs"]) == 1
    assert "smaller" in result["summary"]


def test_dispatch_to_images(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 2)

    result = _dispatch_tool("to_images", src, tmp_path / "out", {
        "fmt": "png", "dpi": 72, "page_spec": "all",
    })

    assert len(result["outputs"]) == 2


def test_dispatch_watermark(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 2)

    result = _dispatch_tool("watermark", src, tmp_path / "out", {
        "text": "DRAFT", "mode": "diagonal",
    })

    assert "Watermarked 2 page" in result["summary"]


def test_dispatch_numbers(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)

    result = _dispatch_tool("numbers", src, tmp_path / "out", {})

    assert "Numbered 3 page" in result["summary"]


def test_dispatch_metadata_read(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 1)

    result = _dispatch_tool("metadata", src, tmp_path / "out", {})

    assert "metadata" in result


def test_dispatch_metadata_write(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 1)

    result = _dispatch_tool("metadata", src, tmp_path / "out", {
        "fields": {"title": "Test Doc"},
    })

    assert len(result["outputs"]) == 1
    assert result["metadata"]["title"] == "Test Doc"


def test_dispatch_metadata_clear(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 1)
    _dispatch_tool("metadata", src, tmp_path, {"fields": {"title": "To Clear", "author": "Keep"}})

    result = _dispatch_tool("metadata", tmp_path / "in_metadata.pdf", tmp_path / "out", {
        "fields": {"title": ""},
    })
    assert len(result["outputs"]) == 1
    assert "title" not in result["metadata"]
    assert result["metadata"].get("author") == "Keep"


def test_dispatch_unknown_tool(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 1)

    with pytest.raises(ValueError, match="Tool not yet wired"):
        _dispatch_tool("nonexistent_tool", src, tmp_path / "out", {})


# ───────────────────────── Api envelope shape ──────────────────────────


def test_api_load_pdf_ok(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 4)
    api = Api()

    result = api.load_pdf(str(src))

    assert result["ok"] is True
    assert result["data"]["name"] == "in.pdf"
    assert result["data"]["page_count"] == 4
    assert "size_bytes" in result["data"]


def test_api_load_pdf_missing_returns_error_envelope(tmp_path: Path) -> None:
    api = Api()
    result = api.load_pdf(str(tmp_path / "nope.pdf"))

    assert result["ok"] is False
    assert "error" in result
    assert "Not a PDF" in result["error"]


def test_api_load_pdf_non_pdf_extension(tmp_path: Path) -> None:
    bogus = tmp_path / "in.txt"
    bogus.write_text("hello")
    api = Api()

    result = api.load_pdf(str(bogus))
    assert result["ok"] is False


def test_api_run_tool_without_pdf(tmp_path: Path) -> None:
    api = Api()
    result = api.run_tool("split", {"mode": "each_page"})

    assert result["ok"] is False
    assert "Open a PDF first" in result["error"]


def test_api_run_tool_split_ok(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)
    api = Api()
    api.load_pdf(str(src))
    api._output_dir = tmp_path / "out"

    result = api.run_tool("split", {"mode": "each_page"})

    assert result["ok"] is True
    assert "outputs" in result["data"]
    assert len(result["data"]["outputs"]) == 3
    assert "summary" in result["data"]


def test_api_run_tool_bad_options_returns_error(tmp_path: Path) -> None:
    """Invalid options must surface as ``{ok: False, error}`` — never raise."""
    src = tmp_path / "in.pdf"
    make_pdf(src, 3)
    api = Api()
    api.load_pdf(str(src))
    api._output_dir = tmp_path / "out"

    # Empty page_spec for ranges mode → ValueError under the hood.
    result = api.run_tool("split", {"mode": "ranges", "page_spec": ""})

    assert result["ok"] is False
    assert "error" in result


def test_api_run_merge_empty_files() -> None:
    api = Api()
    result = api.run_merge([], {}, {})

    assert result["ok"] is False
    assert "at least one" in result["error"].lower()


def test_api_run_merge_missing_file(tmp_path: Path) -> None:
    api = Api()
    api._output_dir = tmp_path / "out"

    result = api.run_merge(
        [str(tmp_path / "nope.pdf")],
        {},
        {},
    )
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_api_run_merge_ok(tmp_path: Path) -> None:
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    make_pdf(a, 2)
    make_pdf(b, 3)
    api = Api()
    api._output_dir = tmp_path / "out"

    result = api.run_merge(
        [str(a), str(b)],
        {"text_template": "{filename}", "position": "bottom-center"},
        {"output_filename": "merged.pdf", "overwrite": True},
    )

    assert result["ok"] is True, result.get("error")
    assert len(result["data"]["outputs"]) == 1
    merged = Path(result["data"]["outputs"][0])
    assert merged.exists()
    with fitz.open(merged) as doc:
        assert doc.page_count == 5


def test_api_run_from_images_ok(tmp_path: Path) -> None:
    img = tmp_path / "test.png"
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 0)
    pix.clear_with(200)
    pix.save(str(img))

    api = Api()
    api._output_dir = tmp_path / "out"

    result = api.run_from_images([str(img)], {"page_size": "a4", "orientation": "portrait"})
    assert result["ok"] is True
    assert len(result["data"]["outputs"]) == 1
    out_file = Path(result["data"]["outputs"][0])
    assert out_file.is_file()
    with fitz.open(out_file) as doc:
        assert doc.page_count == 1
