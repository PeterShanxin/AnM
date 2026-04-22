from __future__ import annotations

import re
from pathlib import Path

from .models import FileItem

LEGACY_GENERATED_NAMES = {"annotatedmerged.pdf"}
LEGACY_GENERATED_PREFIX = "annotated_"
OUTPUT_DIR_NAME = "output"


def natural_sort_key(value: str) -> list[object]:
    parts = re.split(r"(\d+)", value.casefold())
    return [int(part) if part.isdigit() else part for part in parts]


def is_generated_pdf(path: Path, selected_directory: Path | None = None) -> bool:
    path_lower = path.name.casefold()
    if path_lower in LEGACY_GENERATED_NAMES or path_lower.startswith(LEGACY_GENERATED_PREFIX):
        return True
    if selected_directory is not None:
        try:
            relative = path.resolve().relative_to(selected_directory.resolve())
        except ValueError:
            return False
        return OUTPUT_DIR_NAME in relative.parts
    return OUTPUT_DIR_NAME in {part.casefold() for part in path.parts}


def collect_pdf_files(directory: Path) -> list[Path]:
    directory = directory.resolve()
    pdfs = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.casefold() == ".pdf"
        and not is_generated_pdf(path, directory)
    ]
    return sorted(pdfs, key=lambda item: natural_sort_key(item.name))


class FileSelectionModel:
    def __init__(self) -> None:
        self._items: list[FileItem] = []

    @property
    def items(self) -> list[FileItem]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()

    def add_files(self, paths: list[Path]) -> int:
        added = 0
        existing = {item.path.resolve() for item in self._items}
        for path in paths:
            resolved = path.resolve()
            if (
                resolved in existing
                or not path.is_file()
                or path.suffix.casefold() != ".pdf"
                or is_generated_pdf(path)
            ):
                continue
            self._items.append(FileItem(path=resolved))
            existing.add(resolved)
            added += 1
        return added

    def add_directory(self, directory: Path) -> int:
        return self.add_files(collect_pdf_files(directory))

    def remove_indices(self, indices: list[int]) -> None:
        for index in sorted(set(indices), reverse=True):
            if 0 <= index < len(self._items):
                del self._items[index]

    def set_included(self, indices: list[int], included: bool) -> None:
        for index in indices:
            if 0 <= index < len(self._items):
                self._items[index].included = included

    def move(self, indices: list[int], direction: int) -> list[int]:
        if not indices:
            return []
        indices = sorted(set(index for index in indices if 0 <= index < len(self._items)))
        if direction < 0:
            for index in indices:
                if index == 0 or index - 1 in indices:
                    continue
                self._items[index - 1], self._items[index] = (
                    self._items[index],
                    self._items[index - 1],
                )
            return [max(index - 1, 0) for index in indices]
        for index in reversed(indices):
            if index >= len(self._items) - 1 or index + 1 in indices:
                continue
            self._items[index + 1], self._items[index] = self._items[index], self._items[index + 1]
        return [min(index + 1, len(self._items) - 1) for index in indices]

    def get_included_paths(self) -> list[Path]:
        return [item.path for item in self._items if item.included]

    def get_display_rows(self) -> list[tuple[str, str, str]]:
        rows = []
        for item in self._items:
            rows.append(("Yes" if item.included else "No", item.path.name, str(item.path.parent)))
        return rows
