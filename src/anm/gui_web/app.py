"""pywebview entrypoint + JS-callable Api bridge.

The bridge runs PDF operations on a worker thread so the UI stays
responsive.  Each method returns a JSON-serialisable dict:

    {"ok": True,  "data": ...}
    {"ok": False, "error": "..."}

Tools are dispatched by ``tool_id`` so the JS side stays decoupled from
Python's dataclass layout.
"""

from __future__ import annotations

import base64
import io
import threading
import traceback
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import webview

from ..models import AnnotationOptions, RunOptions
from ..pipeline import process_pdfs
from ..tools.delete_pages import DeletePagesOptions, delete_pages
from ..tools.extract import ExtractOptions, extract_pages
from ..tools.reorder import ReorderOptions, reorder_pdf
from ..tools.rotate import RotateOptions, rotate_pdf
from ..tools.split import SplitMode, SplitOptions, split_pdf

# Assets shipped alongside this module.
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_INDEX_HTML = _ASSETS_DIR / "index.html"

# Thumbnail rendering settings.
_THUMB_WIDTH_PX = 160     # render width in CSS pixels
_THUMB_ZOOM = 1.5         # PyMuPDF zoom multiplier — higher = sharper, slower


def _ok(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _err(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


class Api:
    """Exposed to JavaScript via ``window.pywebview.api.<method>``.

    All methods are callable from JS and return promises that resolve to
    plain dicts.  Errors are caught and returned as ``{ok: False, ...}``
    rather than raised — pywebview's default error handling drops the
    traceback, which makes debugging painful.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_pdf: Path | None = None
        self._output_dir: Path = Path.cwd() / "output"

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def open_pdf_dialog(self) -> dict[str, Any]:
        window = webview.active_window()
        if window is None:
            return _err("No active window")
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("PDF files (*.pdf)", "All files (*.*)"),
                allow_multiple=False,
            )
        except Exception as exc:  # noqa: BLE001
            return _err(f"Dialog failed: {exc}")
        if not result:
            return _ok(None)
        path = Path(result[0])
        return self.load_pdf(str(path))

    def open_pdfs_dialog(self) -> dict[str, Any]:
        """Multi-file picker for tools that take several PDFs (Merge)."""
        window = webview.active_window()
        if window is None:
            return _err("No active window")
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("PDF files (*.pdf)", "All files (*.*)"),
                allow_multiple=True,
            )
        except Exception as exc:  # noqa: BLE001
            return _err(f"Dialog failed: {exc}")
        if not result:
            return _ok([])
        files: list[dict[str, Any]] = []
        for raw in result:
            path = Path(raw).expanduser().resolve()
            if not path.is_file() or path.suffix.lower() != ".pdf":
                continue
            try:
                with fitz.open(path) as doc:
                    page_count = doc.page_count
            except Exception:  # noqa: BLE001 - skip unreadable file but keep going
                page_count = 0
            files.append({
                "path": str(path),
                "name": path.name,
                "page_count": page_count,
                "size_bytes": path.stat().st_size,
            })
        # Default output dir to the first file's parent if none chosen yet.
        if files:
            with self._lock:
                if self._output_dir == Path.cwd() / "output":
                    self._output_dir = Path(files[0]["path"]).parent
        return _ok({
            "files": files,
            "output_dir": str(self._output_dir),
        })

    def load_pdf(self, path_str: str) -> dict[str, Any]:
        path = Path(path_str).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            return _err(f"Not a PDF: {path}")
        try:
            with fitz.open(path) as doc:
                page_count = doc.page_count
        except Exception as exc:  # noqa: BLE001
            return _err(f"Failed to open: {exc}")
        with self._lock:
            self._current_pdf = path
            if self._output_dir == Path.cwd() / "output":
                # Default to the source folder until the user picks one.
                self._output_dir = path.parent
        size_bytes = path.stat().st_size
        return _ok({
            "path": str(path),
            "name": path.name,
            "page_count": page_count,
            "size_bytes": size_bytes,
            "output_dir": str(self._output_dir),
        })

    def choose_output_dir(self) -> dict[str, Any]:
        window = webview.active_window()
        if window is None:
            return _err("No active window")
        try:
            result = window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as exc:  # noqa: BLE001
            return _err(f"Dialog failed: {exc}")
        if not result:
            return _ok(None)
        chosen = Path(result[0])
        with self._lock:
            self._output_dir = chosen
        return _ok({"output_dir": str(chosen)})

    # ------------------------------------------------------------------
    # Page thumbnails (lazy)
    # ------------------------------------------------------------------

    def get_page_thumbs(self, page_indices: Iterable[int]) -> dict[str, Any]:
        """Render a batch of thumbnails as base64-encoded PNGs.

        *page_indices* are 0-based.  Returns ``{index: dataUri}``.
        """
        with self._lock:
            pdf = self._current_pdf
        if pdf is None:
            return _err("No PDF loaded")
        try:
            indices = sorted({int(i) for i in page_indices})
        except (TypeError, ValueError) as exc:
            return _err(f"Bad page indices: {exc}")
        out: dict[str, str] = {}
        try:
            with fitz.open(pdf) as doc:
                matrix = fitz.Matrix(_THUMB_ZOOM, _THUMB_ZOOM)
                for i in indices:
                    if i < 0 or i >= doc.page_count:
                        continue
                    pix = doc[i].get_pixmap(matrix=matrix, alpha=False)
                    buf = io.BytesIO(pix.tobytes("png"))
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                    out[str(i)] = f"data:image/png;base64,{encoded}"
        except Exception as exc:  # noqa: BLE001
            return _err(f"Thumb render failed: {exc}")
        return _ok(out)

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def run_tool(self, tool_id: str, options: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            pdf = self._current_pdf
            out_dir = self._output_dir
        if pdf is None:
            return _err("Open a PDF first.")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return _err(f"Cannot create output folder: {exc}")
        try:
            return _ok(_dispatch_tool(tool_id, pdf, out_dir, options or {}))
        except Exception as exc:  # noqa: BLE001
            return _err(f"{exc}\n\n{traceback.format_exc(limit=3)}")

    def run_merge(
        self,
        files: list[str],
        annotation: dict[str, Any] | None = None,
        run: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Annotate + merge a list of PDFs via pipeline.process_pdfs."""
        if not files:
            return _err("Pick at least one PDF.")
        paths = [Path(f).expanduser() for f in files]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            return _err(f"File(s) not found: {', '.join(p.name for p in missing)}")

        with self._lock:
            out_dir = self._output_dir
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return _err(f"Cannot create output folder: {exc}")

        annotation = annotation or {}
        run = run or {}
        try:
            anno_opts = AnnotationOptions(
                text_template=str(annotation.get("text_template", "{filename}")),
                position=str(annotation.get("position", "top-center")),
                font_size=int(annotation.get("font_size", 12)),
                margin=int(annotation.get("margin", 24)),
                box_opacity=float(annotation.get("box_opacity", 0.5)),
            )
            run_opts = RunOptions(
                output_dir=out_dir,
                output_filename=str(run.get("output_filename", "annotated-merged.pdf")),
                save_intermediate=bool(run.get("save_intermediate", False)),
                open_folder=bool(run.get("open_folder", False)),
                overwrite=bool(run.get("overwrite", True)),
            )
            result = process_pdfs(paths, anno_opts, run_opts)
        except Exception as exc:  # noqa: BLE001
            return _err(f"{exc}\n\n{traceback.format_exc(limit=3)}")

        return _ok({
            "outputs": [str(result.merged_pdf_path)],
            "summary": f"Merged {len(paths)} file(s) → {result.merged_pdf_path.name}",
        })

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def reveal_path(self, path_str: str) -> dict[str, Any]:
        """Open *path_str* in the OS file explorer (best-effort)."""
        import os
        import subprocess
        import sys

        target = Path(path_str)
        if not target.exists():
            return _err("Path not found")
        try:
            if sys.platform.startswith("win"):
                # ``os.startfile`` opens folders in Explorer.
                os.startfile(str(target))  # type: ignore[attr-defined] # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)], check=False)  # noqa: S603,S607
            else:
                subprocess.run(["xdg-open", str(target)], check=False)  # noqa: S603,S607
        except Exception as exc:  # noqa: BLE001
            return _err(str(exc))
        return _ok(None)


def _dispatch_tool(
    tool_id: str,
    pdf: Path,
    out_dir: Path,
    opts: dict[str, Any],
) -> dict[str, Any]:
    """Map a JS-side tool_id + options dict to the matching tools.* function."""

    if tool_id == "split":
        mode_str = str(opts.get("mode", "each_page"))
        try:
            mode = SplitMode(mode_str)
        except ValueError as exc:
            raise ValueError(f"Unknown split mode: {mode_str}") from exc
        options = SplitOptions(
            mode=mode,
            page_spec=str(opts.get("page_spec", "")),
            every_n=int(opts.get("every_n", 1)),
        )
        result = split_pdf(pdf, options, output_dir=out_dir)
        return {
            "outputs": [str(p) for p in result.output_paths],
            "summary": f"Wrote {len(result.output_paths)} file(s) to {out_dir}",
        }

    if tool_id == "rotate":
        options = RotateOptions(
            angle=int(opts.get("angle", 90)),
            page_spec=str(opts.get("page_spec", "all")),
        )
        out_path = out_dir / f"{pdf.stem}_rotated.pdf"
        result = rotate_pdf(pdf, options, output_path=out_path)
        return {
            "outputs": [str(result.output_path)],
            "summary": f"Rotated {result.pages_rotated} page(s) → {result.output_path.name}",
        }

    if tool_id == "extract":
        options = ExtractOptions(page_spec=str(opts.get("page_spec", "")))
        out_path = out_dir / f"{pdf.stem}_extracted.pdf"
        result = extract_pages(pdf, options, output_path=out_path)
        return {
            "outputs": [str(result.output_path)],
            "summary": f"Extracted {result.pages_extracted} page(s) → {result.output_path.name}",
        }

    if tool_id == "delete":
        options = DeletePagesOptions(page_spec=str(opts.get("page_spec", "")))
        out_path = out_dir / f"{pdf.stem}_trimmed.pdf"
        result = delete_pages(pdf, options, output_path=out_path)
        return {
            "outputs": [str(result.output_path)],
            "summary": f"Removed {result.pages_removed} page(s) → {result.output_path.name}",
        }

    if tool_id == "reorder":
        order = opts.get("order") or []
        if not isinstance(order, list):
            raise ValueError("'order' must be a list of 1-based page numbers")
        options = ReorderOptions(order=[int(n) for n in order])
        out_path = out_dir / f"{pdf.stem}_reordered.pdf"
        result = reorder_pdf(pdf, options, output_path=out_path)
        return {
            "outputs": [str(result.output_path)],
            "summary": f"Reordered → {result.output_path.name}",
        }

    raise ValueError(f"Tool not yet wired: {tool_id}")


# --------------------------------------------------------------------------- #
# Window plumbing
# --------------------------------------------------------------------------- #


class WebApp:
    """Wraps the pywebview window so callers see a tk-app-like API."""

    def __init__(self, *, debug: bool = False) -> None:
        self._api = Api()
        self._debug = debug
        if not _INDEX_HTML.exists():
            raise FileNotFoundError(f"Missing UI bundle: {_INDEX_HTML}")
        self._window = webview.create_window(
            title="AnM — PDF Toolkit",
            url=_INDEX_HTML.as_uri(),
            js_api=self._api,
            width=1280,
            height=820,
            min_size=(960, 640),
            background_color="#f3f3f3",
            text_select=False,
        )

    def mainloop(self) -> None:
        webview.start(debug=self._debug)


def launch(debug: bool = False) -> int:
    WebApp(debug=debug).mainloop()
    return 0
