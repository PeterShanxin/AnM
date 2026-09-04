from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import fitz

from anm import cli
from anm.main import main


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = cli.main(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_main_without_args_launches_gui_dispatch() -> None:
    launched = False

    class FakeApp:
        def mainloop(self) -> None:
            nonlocal launched
            launched = True

    assert main([], gui_factory=FakeApp) == 0
    assert launched


def test_help_command_includes_examples() -> None:
    code, stdout, stderr = run_cli(["help", "merge"])

    assert code == 0
    assert stderr == ""
    assert "Examples:" in stdout
    assert "anm merge" in stdout


def test_blank_template_disables_annotation() -> None:
    args = cli.build_parser().parse_args(["merge", "sample.pdf", "--template", " "])

    options = cli.build_annotation_options(args)

    assert options.text_template == ""


def test_subcommand_help_is_captured() -> None:
    code, stdout, stderr = run_cli(["merge", "--help"])

    assert code == 0
    assert stderr == ""
    assert "Examples:" in stdout
    assert "--dry-run" in stdout


def test_top_level_help_does_not_import_pipeline() -> None:
    original_pipeline = sys.modules.pop("anm.pipeline", None)

    try:
        code, stdout, stderr = run_cli(["--help"])

        assert code == 0
        assert stderr == ""
        assert "anm merge" in stdout
        assert "anm.pipeline" not in sys.modules
    finally:
        if original_pipeline is not None:
            sys.modules["anm.pipeline"] = original_pipeline


def test_merge_writes_output_in_explicit_order(tmp_path: Path) -> None:
    first = tmp_path / "page2.pdf"
    second = tmp_path / "page10.pdf"
    make_pdf(first, "Second")
    make_pdf(second, "Tenth")
    output = tmp_path / "merged.pdf"

    code, stdout, stderr = run_cli(["merge", str(second), str(first), "--output", str(output)])

    assert code == 0
    assert str(output) in stdout
    assert "Annotated" in stderr
    merged = fitz.open(output)
    assert merged.page_count == 2
    merged.close()


def test_merge_dir_filters_generated_outputs_and_supports_json(tmp_path: Path) -> None:
    make_pdf(tmp_path / "page2.pdf", "Second")
    make_pdf(tmp_path / "page10.pdf", "Tenth")
    make_pdf(tmp_path / "annotated_old.pdf", "Generated")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    make_pdf(output_dir / "page1.pdf", "Generated nested")

    code, stdout, stderr = run_cli(
        ["merge-dir", str(tmp_path), "--json", "--output", str(tmp_path / "merged.pdf")]
    )

    assert code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert [Path(path).name for path in payload["inputs"]] == ["page2.pdf", "page10.pdf"]
    assert Path(payload["output"]).exists()


def test_preview_writes_png(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    preview = tmp_path / "preview.png"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli(["preview", str(source), "--output", str(preview)])

    assert code == 0
    assert str(preview) in stdout
    assert stderr == ""
    assert preview.read_bytes().startswith(b"\x89PNG")


def test_info_supports_json(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli(["info", str(source), "--json"])

    assert code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert payload["items"][0]["page_count"] == 1
    assert payload["items"][0]["path"] == str(source.resolve())


def test_doctor_reports_dependencies() -> None:
    code, stdout, stderr = run_cli(["doctor", "--json"])

    assert code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert payload["checks"]["pymupdf"]["ok"] is True
    assert payload["checks"]["python"]["ok"] is True


def test_dry_run_does_not_create_output(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "merged.pdf"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli(["merge", str(source), "--output", str(output), "--dry-run"])

    assert code == 0
    assert stderr == ""
    assert "Dry run" in stdout
    assert not output.exists()


def test_merge_json_failure_is_stable_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "merged.pdf"
    make_pdf(source, "hello")
    output.write_bytes(b"already here")

    code, stdout, stderr = run_cli(["merge", str(source), "--output", str(output), "--json"])

    assert code == 1
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["ok"] is False
    assert payload["type"] == "FileExistsError"
    assert "already exists" in payload["error"]


def test_split_each_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "hello")
    doc.new_page()
    doc.save(source)
    doc.close()
    out_dir = tmp_path / "split_out"

    code, stdout, stderr = run_cli(["split", str(source), "--output", str(out_dir)])

    assert code == 0
    assert out_dir.is_dir()


def test_split_by_range_json(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    for _ in range(5):
        doc.new_page()
    doc.save(source)
    doc.close()
    out_dir = tmp_path / "split_out"

    code, stdout, stderr = run_cli(
        ["split", str(source), "--pages", "1-2,4", "--output", str(out_dir), "--json"]
    )

    assert code == 0
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert len(payload["outputs"]) == 2


def test_rotate_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "rotated.pdf"

    code, stdout, stderr = run_cli(
        ["rotate", str(source), "--angle", "90", "--output", str(output)]
    )

    assert code == 0
    doc = fitz.open(output)
    assert doc[0].rotation == 90
    doc.close()


def test_reorder_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    for text in ["A", "B", "C"]:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(source)
    doc.close()
    output = tmp_path / "reordered.pdf"

    code, stdout, stderr = run_cli(
        ["reorder", str(source), "--order", "3,2,1", "--output", str(output)]
    )

    assert code == 0
    doc = fitz.open(output)
    assert "C" in doc[0].get_text()
    doc.close()


def test_delete_pages_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    for text in ["A", "B", "C"]:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(source)
    doc.close()
    output = tmp_path / "trimmed.pdf"

    code, stdout, stderr = run_cli(
        ["delete-pages", str(source), "--pages", "2", "--output", str(output)]
    )

    assert code == 0
    doc = fitz.open(output)
    assert doc.page_count == 2
    doc.close()


def test_extract_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    for text in ["A", "B", "C"]:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(source)
    doc.close()
    output = tmp_path / "extracted.pdf"

    code, stdout, stderr = run_cli(
        ["extract", str(source), "--pages", "1,3", "--output", str(output)]
    )

    assert code == 0
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "A" in doc[0].get_text()
    assert "C" in doc[1].get_text()
    doc.close()


def test_compress_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "compressed.pdf"

    code, stdout, stderr = run_cli(
        ["compress", str(source), "--quality", "medium", "--output", str(output)]
    )

    assert code == 0
    assert output.is_file()


def test_compress_cli_json(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "compressed.pdf"

    code, stdout, stderr = run_cli(
        ["compress", str(source), "--output", str(output), "--json"]
    )

    assert code == 0
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert payload["original_size"] > 0


def test_to_images_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    out_dir = tmp_path / "images"

    code, stdout, stderr = run_cli(
        ["to-images", str(source), "--format", "png", "--dpi", "72", "--output", str(out_dir)]
    )

    assert code == 0
    assert out_dir.is_dir()


def test_to_images_cli_json(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    out_dir = tmp_path / "images"

    code, stdout, stderr = run_cli(
        ["to-images", str(source), "--output", str(out_dir), "--json"]
    )

    assert code == 0
    payload = json.loads(stdout)
    assert payload["ok"] is True
    assert len(payload["outputs"]) == 1


def test_from_images_cli(tmp_path: Path) -> None:
    img = tmp_path / "img.png"
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100), 0)
    pix.set_rect(pix.irect, (255, 0, 0))
    pix.save(str(img))
    output = tmp_path / "album.pdf"

    code, stdout, stderr = run_cli(
        ["from-images", str(img), "--page-size", "a4", "--output", str(output)]
    )

    assert code == 0
    assert output.is_file()


def test_watermark_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "wm.pdf"

    code, stdout, stderr = run_cli(
        ["watermark", str(source), "--text", "DRAFT", "--output", str(output)]
    )

    assert code == 0
    assert output.is_file()


def test_page_numbers_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "numbered.pdf"

    code, stdout, stderr = run_cli(
        ["page-numbers", str(source), "--output", str(output)]
    )

    assert code == 0
    assert output.is_file()


def test_metadata_show_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli(["metadata", str(source), "--show"])

    assert code == 0
    assert str(source) in stdout


def test_metadata_set_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "updated.pdf"

    code, stdout, stderr = run_cli(
        ["metadata", str(source), "--set", "title=My Title", "--output", str(output)]
    )

    assert code == 0
    assert output.is_file()
    meta = fitz.open(output).metadata
    assert meta["title"] == "My Title"


def test_watermark_cli_color(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    output = tmp_path / "wm.pdf"

    code, stdout, stderr = run_cli([
        "watermark", str(source),
        "--text", "CONFIDENTIAL",
        "--color", "red",
        "--output", str(output),
    ])

    assert code == 0
    assert output.is_file()


def test_metadata_clear_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    with_title = tmp_path / "with_title.pdf"
    run_cli(["metadata", str(source), "--set", "title=Old Title", "--output", str(with_title)])

    cleared = tmp_path / "cleared.pdf"
    code, stdout, stderr = run_cli(
        ["metadata", str(with_title), "--set", "title=", "--output", str(cleared)]
    )
    assert code == 0
    meta = fitz.open(cleared).metadata
    assert not meta.get("title")


def test_metadata_show_and_set_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli([
        "metadata", str(source),
        "--show", "--set", "title=Test",
        "--output", str(tmp_path / "out.pdf"),
    ])
    assert code == 1
    assert "Cannot use both --show and --set" in stderr


def test_metadata_set_requires_output(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")

    code, stdout, stderr = run_cli(
        ["metadata", str(source), "--set", "title=Test"]
    )

    assert code == 1
