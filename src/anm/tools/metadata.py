from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz

_EDITABLE_KEYS = ("title", "author", "subject", "keywords", "creator", "producer")


@dataclass(slots=True)
class MetadataOptions:
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class MetadataResult:
    output_path: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def read_metadata(input_path: Path) -> dict[str, str]:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")
    with fitz.open(input_path) as doc:
        raw = doc.metadata or {}
        return {k: str(v) for k, v in raw.items() if v not in (None, "")}


def write_metadata(
    input_path: Path,
    options: MetadataOptions,
    *,
    output_path: Path,
) -> MetadataResult:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    invalid = [k for k in options.fields if k not in _EDITABLE_KEYS]
    if invalid:
        raise ValueError(f"Invalid metadata key(s): {', '.join(invalid)}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        current = doc.metadata or {}
        updated = {**current, **options.fields}
        doc.set_metadata(updated)
        doc.save(output_path)
        final = {k: str(v) for k, v in (doc.metadata or {}).items() if v not in (None, "")}

    return MetadataResult(output_path=output_path, metadata=final)
