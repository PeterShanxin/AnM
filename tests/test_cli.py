from __future__ import annotations

import io
import json
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


def test_subcommand_help_is_captured() -> None:
    code, stdout, stderr = run_cli(["merge", "--help"])

    assert code == 0
    assert stderr == ""
    assert "Examples:" in stdout
    assert "--dry-run" in stdout


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
