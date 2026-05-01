from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from .app_state import collect_pdf_files
from .models import AnnotationOptions, RunOptions


class CliError(RuntimeError):
    """Raised for user-facing CLI failures."""


class AnmArgumentParser(argparse.ArgumentParser):
    def __init__(
        self,
        *args: object,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def _print_message(self, message: str, file: TextIO | None = None) -> None:
        if message:
            if file is None or file is sys.stdout:
                target = self.stdout
            elif file is sys.stderr:
                target = self.stderr
            else:
                target = file
            target.write(message)


def get_version() -> str:
    try:
        return importlib.metadata.version("anm")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def build_parser(stdout: TextIO | None = None, stderr: TextIO | None = None) -> AnmArgumentParser:
    parser = AnmArgumentParser(
        prog="anm",
        description="Annotate and merge PDFs from the desktop app pipeline.",
        epilog=(
            "Examples:\n"
            "  anm merge .\\a.pdf .\\b.pdf --output .\\output\\merged.pdf\n"
            "  anm merge-dir .\\pdfs --dry-run\n"
            "  anm preview .\\a.pdf --output .\\preview.png\n"
            "  anm info .\\a.pdf --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        stdout=stdout,
        stderr=stderr,
    )
    parser.add_argument("--version", action="version", version=f"anm {get_version()}")

    def subparser_factory(*args: object, **kwargs: object) -> AnmArgumentParser:
        return AnmArgumentParser(*args, stdout=stdout, stderr=stderr, **kwargs)

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="command",
        parser_class=subparser_factory,
    )
    command_parsers: dict[str, argparse.ArgumentParser] = {}

    def add_command(name: str, **kwargs: object) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            name,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            **kwargs,
        )
        command_parsers[name] = subparser
        return subparser

    gui = add_command(
        "gui",
        help="open the desktop app",
        description="Open the AnM desktop app.",
        epilog="Examples:\n  anm gui\n  anm",
    )
    gui.set_defaults(handler=handle_gui)

    merge = add_command(
        "merge",
        help="annotate and merge explicit PDFs",
        description="Annotate and merge explicit PDF files in the order provided.",
        epilog=(
            "Examples:\n"
            "  anm merge .\\a.pdf .\\b.pdf --output .\\output\\merged.pdf\n"
            "  anm merge .\\a.pdf --template \"{stem} p{page_number}\" --overwrite"
        ),
    )
    merge.add_argument("pdfs", nargs="+", type=Path, help="PDF files in merge order")
    add_merge_options(merge)
    merge.set_defaults(handler=handle_merge)

    merge_dir = add_command(
        "merge-dir",
        help="collect, annotate, and merge PDFs from a folder",
        description=(
            "Collect PDFs from a folder with natural sorting and generated-output filtering."
        ),
        epilog=(
            "Examples:\n"
            "  anm merge-dir .\\pdfs --output .\\output\\merged.pdf\n"
            "  anm merge-dir .\\pdfs --dry-run --json"
        ),
    )
    merge_dir.add_argument("folder", type=Path, help="Folder containing source PDFs")
    add_merge_options(merge_dir)
    merge_dir.set_defaults(handler=handle_merge_dir)

    preview = add_command(
        "preview",
        help="render first-page annotation preview",
        description="Render a PNG preview of the first page with the selected annotation settings.",
        epilog=(
            "Examples:\n"
            "  anm preview .\\a.pdf --output .\\preview.png\n"
            "  anm preview .\\a.pdf --position bottom-right --opacity 0.8"
        ),
    )
    preview.add_argument("pdf", type=Path, help="PDF to preview")
    preview.add_argument("--output", "-o", required=True, type=Path, help="PNG output path")
    add_annotation_options(preview)
    preview.add_argument("--json", action="store_true", help="print machine-readable JSON")
    preview.set_defaults(handler=handle_preview)

    info = add_command(
        "info",
        help="inspect PDFs",
        description="Show page count, first-page size, file size, and basic metadata.",
        epilog="Examples:\n  anm info .\\a.pdf .\\b.pdf\n  anm info .\\a.pdf --json",
    )
    info.add_argument("pdfs", nargs="+", type=Path, help="PDF files to inspect")
    info.add_argument("--json", action="store_true", help="print machine-readable JSON")
    info.set_defaults(handler=handle_info)

    doctor = add_command(
        "doctor",
        help="check runtime dependencies",
        description="Check Python, PyMuPDF, tkinterdnd2, GUI imports, and install paths.",
        epilog="Examples:\n  anm doctor\n  anm doctor --json",
    )
    doctor.add_argument("--json", action="store_true", help="print machine-readable JSON")
    doctor.set_defaults(handler=handle_doctor)

    parser.command_parsers = command_parsers  # type: ignore[attr-defined]
    return parser


def add_annotation_options(parser: argparse.ArgumentParser) -> None:
    from .pipeline import POSITION_CONFIG

    parser.add_argument("--template", default="{filename}", help="annotation template")
    parser.add_argument("--position", choices=sorted(POSITION_CONFIG), default="top-center")
    parser.add_argument("--font-size", type=int, default=12)
    parser.add_argument("--margin", type=int, default=24)
    parser.add_argument("--opacity", type=float, default=0.5, help="annotation box opacity")


def add_merge_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path, help="merged PDF output path")
    add_annotation_options(parser)
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing output")
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="keep annotated PDFs under output/annotated",
    )
    parser.add_argument("--open-folder", action="store_true", help="open output folder on success")
    parser.add_argument("--dry-run", action="store_true", help="show plan without writing output")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def main(
    argv: list[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    gui_runner: Any | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser(stdout=stdout, stderr=stderr)

    if not args:
        parser.print_help(stdout)
        return 0

    if args[0] == "help":
        return print_help(parser, args[1:], stdout)

    try:
        namespace = parser.parse_args(args)
    except SystemExit as exc:
        return int(exc.code or 0)

    handler = getattr(namespace, "handler", None)
    if handler is None:
        parser.print_help(stdout)
        return 0

    try:
        return int(handler(namespace, stdout, stderr, gui_runner))
    except KeyboardInterrupt:
        return emit_error(namespace, stdout, stderr, KeyboardInterrupt("Interrupted."), code=130)
    except Exception as exc:
        return emit_error(namespace, stdout, stderr, exc, code=1)


def print_help(parser: AnmArgumentParser, args: list[str], stdout: TextIO) -> int:
    if not args:
        parser.print_help(stdout)
        return 0
    command = args[0]
    command_parsers = getattr(parser, "command_parsers", {})
    subparser = command_parsers.get(command)
    if subparser is None:
        stdout.write(f"Unknown command: {command}\n\n")
        parser.print_help(stdout)
        return 2
    subparser.print_help(stdout)
    return 0


def handle_gui(_args: argparse.Namespace, _stdout: TextIO, _stderr: TextIO, gui_runner: Any) -> int:
    if gui_runner is None:
        from .gui import PDFAnnotatorApp

        app = PDFAnnotatorApp()
        app.mainloop()
        return 0
    return int(gui_runner())


def handle_merge(args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any) -> int:
    pdf_paths = validate_pdf_paths(args.pdfs)
    return run_merge_command("merge", pdf_paths, args, stdout, stderr)


def handle_merge_dir(
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
    _gui_runner: Any,
) -> int:
    folder = args.folder.resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")
    pdf_paths = collect_pdf_files(folder)
    if not pdf_paths:
        raise FileNotFoundError(f"No source PDFs found in: {folder}")
    return run_merge_command("merge-dir", pdf_paths, args, stdout, stderr)


def run_merge_command(
    command: str,
    pdf_paths: list[Path],
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    annotation_options = build_annotation_options(args)
    run_options = build_run_options(args, pdf_paths)
    output_path = resolve_cli_output_path(pdf_paths, args.output)
    warnings: list[str] = []

    if args.dry_run:
        exists = output_path.exists()
        payload = {
            "ok": True,
            "command": command,
            "dry_run": True,
            "inputs": stringify_paths(pdf_paths),
            "output": str(output_path),
            "would_overwrite": exists and args.overwrite,
            "output_exists": exists,
            "warnings": warnings,
        }
        if args.json:
            write_json(stdout, payload)
        else:
            stdout.write("Dry run: no files were written.\n")
            stdout.write(f"Output: {output_path}\n")
            stdout.write("Inputs:\n")
            for index, path in enumerate(pdf_paths, start=1):
                stdout.write(f"  {index}. {path}\n")
            if exists:
                stdout.write(
                    "Output exists and will be overwritten.\n"
                    if args.overwrite
                    else (
                        "Output exists; run without --dry-run would fail "
                        "unless --overwrite is set.\n"
                    )
                )
        return 0

    progress_callback = None if args.json else lambda payload: emit_progress(stderr, payload)
    from .pipeline import open_output_folder, process_pdfs

    result = process_pdfs(
        pdf_paths,
        annotation_options,
        run_options,
        progress_callback=progress_callback,
    )
    if args.open_folder:
        open_output_folder(result.output_dir or result.merged_pdf_path.parent)

    payload = {
        "ok": True,
        "command": command,
        "inputs": stringify_paths(pdf_paths),
        "output": str(result.merged_pdf_path),
        "output_dir": str(result.output_dir) if result.output_dir else None,
        "intermediate": stringify_paths(result.intermediate_paths),
        "warnings": warnings,
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Created {result.merged_pdf_path}\n")
    return 0


def handle_preview(
    args: argparse.Namespace,
    stdout: TextIO,
    _stderr: TextIO,
    _gui_runner: Any,
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    from .pipeline import render_preview_png

    png_bytes = render_preview_png(source, build_annotation_options(args), scale=1.0)
    output.write_bytes(png_bytes)

    payload = {
        "ok": True,
        "command": "preview",
        "inputs": [str(source)],
        "output": str(output),
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Created {output}\n")
    return 0


def handle_info(args: argparse.Namespace, stdout: TextIO, _stderr: TextIO, _gui_runner: Any) -> int:
    pdf_paths = validate_pdf_paths(args.pdfs)
    items = [inspect_pdf(path) for path in pdf_paths]
    payload = {
        "ok": True,
        "command": "info",
        "inputs": stringify_paths(pdf_paths),
        "output": None,
        "items": items,
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        for item in items:
            stdout.write(f"{item['path']}\n")
            stdout.write(f"  pages: {item['page_count']}\n")
            stdout.write(f"  first_page: {item['first_page_size']}\n")
            stdout.write(f"  size_bytes: {item['size_bytes']}\n")
            title = item["metadata"].get("title")
            if title:
                stdout.write(f"  title: {title}\n")
    return 0


def handle_doctor(
    args: argparse.Namespace,
    stdout: TextIO,
    _stderr: TextIO,
    _gui_runner: Any,
) -> int:
    checks = doctor_checks()
    ok = all(check["ok"] for check in checks.values())
    payload = {
        "ok": ok,
        "command": "doctor",
        "inputs": [],
        "output": None,
        "checks": checks,
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write("AnM doctor\n")
        for name, check in checks.items():
            status = "ok" if check["ok"] else "missing"
            detail = check.get("detail") or check.get("version") or check.get("path") or ""
            stdout.write(f"  {name}: {status} {detail}\n")
    return 0 if ok else 1


def build_annotation_options(args: argparse.Namespace) -> AnnotationOptions:
    if args.font_size <= 0:
        raise CliError("--font-size must be greater than 0")
    if args.margin < 0:
        raise CliError("--margin must be 0 or greater")
    if not 0 <= args.opacity <= 1:
        raise CliError("--opacity must be between 0 and 1")
    return AnnotationOptions(
        text_template=args.template.strip() or "{filename}",
        position=args.position,
        font_size=args.font_size,
        margin=args.margin,
        box_opacity=args.opacity,
    )


def build_run_options(args: argparse.Namespace, pdf_paths: list[Path]) -> RunOptions:
    output_path = resolve_cli_output_path(pdf_paths, args.output)
    return RunOptions(
        output_dir=output_path.parent,
        output_filename=output_path.name,
        save_intermediate=args.keep_intermediate,
        open_folder=args.open_folder,
        overwrite=args.overwrite,
    )


def resolve_cli_output_path(pdf_paths: list[Path], output: Path | None) -> Path:
    if output is not None:
        return output.resolve()
    if not pdf_paths:
        return (Path.cwd() / "output" / "annotated-merged.pdf").resolve()
    return (pdf_paths[0].resolve().parent / "output" / "annotated-merged.pdf").resolve()


def validate_pdf_paths(paths: list[Path]) -> list[Path]:
    resolved_paths = [path.resolve() for path in paths]
    for path in resolved_paths:
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise CliError(f"Not a PDF file: {path}")
    return resolved_paths


def inspect_pdf(path: Path) -> dict[str, Any]:
    import fitz

    with fitz.open(path) as document:
        first_page_size = None
        if document.page_count:
            rect = document[0].rect
            first_page_size = {"width": round(rect.width, 2), "height": round(rect.height, 2)}
        return {
            "path": str(path.resolve()),
            "page_count": document.page_count,
            "first_page_size": first_page_size,
            "size_bytes": path.stat().st_size,
            "metadata": clean_metadata(document.metadata or {}),
        }


def clean_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in metadata.items() if value not in (None, "")}


def doctor_checks() -> dict[str, dict[str, object]]:
    checks: dict[str, dict[str, object]] = {
        "python": {
            "ok": True,
            "version": sys.version.split()[0],
            "path": sys.executable,
        },
    }
    try:
        import fitz

        checks["pymupdf"] = {
            "ok": True,
            "version": getattr(fitz, "VersionBind", "unknown"),
            "path": str(Path(fitz.__file__).resolve()) if getattr(fitz, "__file__", None) else None,
        }
    except ImportError as exc:
        checks["pymupdf"] = {"ok": False, "detail": str(exc)}
    checks["tkinterdnd2"] = dependency_check("tkinterdnd2")
    try:
        from .gui import PDFAnnotatorApp  # noqa: F401

        checks["gui_import"] = {"ok": True, "detail": "PDFAnnotatorApp import succeeded"}
    except Exception as exc:  # pragma: no cover - depends on local GUI stack
        checks["gui_import"] = {"ok": False, "detail": str(exc)}
    return checks


def dependency_check(module_name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {"ok": False, "detail": f"{module_name} is not installed"}
    version = None
    try:
        version = importlib.metadata.version(module_name)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return {"ok": True, "version": version, "path": spec.origin}


def emit_progress(stderr: TextIO, payload: dict[str, object]) -> None:
    message = payload.get("message")
    if message:
        stderr.write(f"{message}\n")


def emit_error(
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
    exc: BaseException,
    code: int,
) -> int:
    if getattr(args, "json", False):
        write_json(
            stdout,
            {
                "ok": False,
                "error": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        stderr.write(f"Error: {exc}\n")
    return code


def write_json(stdout: TextIO, payload: dict[str, Any]) -> None:
    stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    stdout.write("\n")


def stringify_paths(paths: list[Path]) -> list[str]:
    return [str(path.resolve()) for path in paths]
