from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

POSITION_CONFIG: dict[str, tuple[str, str]] = {
    "top-left": ("left", "top"),
    "top-center": ("center", "top"),
    "top-right": ("right", "top"),
    "bottom-left": ("left", "bottom"),
    "bottom-center": ("center", "bottom"),
    "bottom-right": ("right", "bottom"),
}


@dataclass(slots=True)
class AnnotationOptions:
    text_template: str = "{filename}"
    position: str = "top-center"
    font_size: int = 12
    margin: int = 24
    box_opacity: float = 0.5


@dataclass(slots=True)
class RunOptions:
    output_dir: Path | None = None
    output_filename: str = "annotated-merged.pdf"
    save_intermediate: bool = False
    open_folder: bool = True
    overwrite: bool = False


@dataclass(slots=True)
class FileItem:
    path: Path
    included: bool = True


@dataclass(slots=True)
class RunResult:
    merged_pdf_path: Path
    intermediate_paths: list[Path] = field(default_factory=list)
    output_dir: Path | None = None
