# Phase 1: Core Page Operations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add shared page-range parsing, extract `gui.py` into `gui/hub.py` + `gui/annotate_merge.py`, then build five page-operation tools (split, rotate, reorder, delete-pages, extract) — each as a `tools/` pure-function module with CLI subcommand. GUI panels deferred to a separate plan after design agent runs.

**Architecture:** Each tool lives in `src/anm/tools/<name>.py` with an Options dataclass, a Result dataclass, and a single entry-point function. CLI subcommands in `cli.py` delegate to those functions. The existing `gui.py` is refactored into a `gui/` package with a hub that swaps panels; the current annotate-merge GUI becomes one panel. All existing tests must keep passing throughout.

**Tech Stack:** Python 3.11+, PyMuPDF (fitz), pytest, ruff

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/anm/tools/__init__.py` | Package init |
| Create | `src/anm/tools/page_range.py` | Parse `1-3,5,8-10` into page indices |
| Create | `src/anm/tools/split.py` | Split PDF by range / every-N / each-page |
| Create | `src/anm/tools/rotate.py` | Rotate selected pages |
| Create | `src/anm/tools/reorder.py` | Reorder pages by index list |
| Create | `src/anm/tools/delete_pages.py` | Delete selected pages |
| Create | `src/anm/tools/extract.py` | Extract selected pages to new PDF |
| Create | `src/anm/gui/__init__.py` | Package init, re-export for backward compat |
| Create | `src/anm/gui/hub.py` | Main window with menu bar + panel switching |
| Create | `src/anm/gui/widgets.py` | Shared Tooltip class extracted from gui.py |
| Create | `src/anm/gui/annotate_merge.py` | Current GUI refactored into ttk.Frame panel |
| Modify | `src/anm/main.py` | Update import from `gui` → `gui.hub` |
| Modify | `src/anm/cli.py` | Add split/rotate/reorder/delete-pages/extract subcommands |
| Create | `tests/test_page_range.py` | Tests for page range parser |
| Create | `tests/test_split.py` | Tests for split tool |
| Create | `tests/test_rotate.py` | Tests for rotate tool |
| Create | `tests/test_reorder.py` | Tests for reorder tool |
| Create | `tests/test_delete_pages.py` | Tests for delete-pages tool |
| Create | `tests/test_extract.py` | Tests for extract tool |
| Modify | `tests/test_cli.py` | Add CLI tests for new subcommands |

---

## Task 1: Page Range Parser

Shared utility used by split, rotate, delete, extract. Parses human page specs like `1-3,5,8-10` into zero-based indices.

**Files:**
- Create: `src/anm/tools/__init__.py`
- Create: `src/anm/tools/page_range.py`
- Test: `tests/test_page_range.py`

- [ ] **Step 1: Write failing tests for page range parser**

```python
# tests/test_page_range.py
from __future__ import annotations

import pytest

from anm.tools.page_range import parse_page_range


def test_single_page() -> None:
    assert parse_page_range("3", total_pages=10) == [2]


def test_page_range() -> None:
    assert parse_page_range("2-4", total_pages=10) == [1, 2, 3]


def test_comma_separated() -> None:
    assert parse_page_range("1,3,5", total_pages=10) == [0, 2, 4]


def test_mixed_ranges_and_singles() -> None:
    assert parse_page_range("1-3,5,8-10", total_pages=10) == [0, 1, 2, 4, 7, 8, 9]


def test_deduplicates_and_sorts() -> None:
    assert parse_page_range("3,1-3", total_pages=10) == [0, 1, 2]


def test_whitespace_is_stripped() -> None:
    assert parse_page_range(" 1 - 3 , 5 ", total_pages=10) == [0, 1, 2, 4]


def test_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="out of range"):
        parse_page_range("11", total_pages=10)


def test_zero_page_raises() -> None:
    with pytest.raises(ValueError, match="out of range"):
        parse_page_range("0", total_pages=10)


def test_negative_page_raises() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_page_range("-1", total_pages=10)


def test_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_page_range("", total_pages=10)


def test_reversed_range_raises() -> None:
    with pytest.raises(ValueError, match="Invalid range"):
        parse_page_range("5-3", total_pages=10)


def test_all_keyword() -> None:
    assert parse_page_range("all", total_pages=3) == [0, 1, 2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_page_range.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anm.tools'`

- [ ] **Step 3: Create tools package and implement page range parser**

```python
# src/anm/tools/__init__.py
```

```python
# src/anm/tools/page_range.py
from __future__ import annotations

import re


def parse_page_range(spec: str, *, total_pages: int) -> list[int]:
    """Parse a human page specification into sorted, deduplicated zero-based indices.

    Accepts: "1-3,5,8-10", "all", single pages "5", ranges "2-4".
    Pages are 1-based in the spec, returned as 0-based indices.
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("Page specification is empty.")

    if spec.casefold() == "all":
        return list(range(total_pages))

    indices: set[int] = set()
    for segment in spec.split(","):
        segment = segment.strip()
        if not segment:
            continue
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", segment)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start > end:
                raise ValueError(f"Invalid range: {start}-{end} (start > end).")
            _validate_page(start, total_pages)
            _validate_page(end, total_pages)
            indices.update(range(start - 1, end))
        elif re.fullmatch(r"\d+", segment):
            page = int(segment)
            _validate_page(page, total_pages)
            indices.add(page - 1)
        else:
            raise ValueError(f"Invalid page specification segment: '{segment}'.")

    return sorted(indices)


def _validate_page(page: int, total_pages: int) -> None:
    if page < 1 or page > total_pages:
        raise ValueError(f"Page {page} is out of range (1-{total_pages}).")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_page_range.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Run ruff and existing tests**

Run: `ruff check src/anm/tools/ tests/test_page_range.py && pytest -v`
Expected: No lint errors, all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/__init__.py src/anm/tools/page_range.py tests/test_page_range.py
git commit -m "feat: add page range parser for PDF page selection"
```

---

## Task 2: Split Tool

**Files:**
- Create: `src/anm/tools/split.py`
- Test: `tests/test_split.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_split.py
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.split import SplitMode, SplitOptions, SplitResult, split_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_split_by_ranges(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 5)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.RANGES, page_spec="1-2,4"),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 2
    doc1 = fitz.open(result.output_paths[0])
    assert doc1.page_count == 2
    doc1.close()
    doc2 = fitz.open(result.output_paths[1])
    assert doc2.page_count == 1
    doc2.close()


def test_split_every_n(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 7)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.EVERY_N, every_n=3),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 3
    counts = [fitz.open(p).page_count for p in result.output_paths]
    assert counts == [3, 3, 1]


def test_split_each_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 4)

    result = split_pdf(
        source,
        SplitOptions(mode=SplitMode.EACH_PAGE),
        output_dir=tmp_path / "out",
    )

    assert len(result.output_paths) == 4
    for p in result.output_paths:
        doc = fitz.open(p)
        assert doc.page_count == 1
        doc.close()


def test_split_empty_pdf_raises(tmp_path: Path) -> None:
    source = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.save(source)
    doc.close()

    with pytest.raises(ValueError, match="no pages"):
        split_pdf(source, SplitOptions(mode=SplitMode.EACH_PAGE), output_dir=tmp_path / "out")


def test_split_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        split_pdf(
            tmp_path / "missing.pdf",
            SplitOptions(mode=SplitMode.EACH_PAGE),
            output_dir=tmp_path / "out",
        )


def test_split_creates_output_dir(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 2)
    out = tmp_path / "nested" / "deep" / "out"

    result = split_pdf(source, SplitOptions(mode=SplitMode.EACH_PAGE), output_dir=out)

    assert out.is_dir()
    assert len(result.output_paths) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_split.py -v`
Expected: FAIL — `ImportError: cannot import name 'split_pdf' from 'anm.tools.split'`

- [ ] **Step 3: Implement split tool**

```python
# src/anm/tools/split.py
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from .page_range import parse_page_range


class SplitMode(enum.Enum):
    RANGES = "ranges"
    EVERY_N = "every_n"
    EACH_PAGE = "each_page"


@dataclass(slots=True)
class SplitOptions:
    mode: SplitMode = SplitMode.EACH_PAGE
    page_spec: str = ""
    every_n: int = 1


@dataclass(slots=True)
class SplitResult:
    output_paths: list[Path] = field(default_factory=list)


def split_pdf(
    input_path: Path,
    options: SplitOptions,
    *,
    output_dir: Path,
) -> SplitResult:
    """Split a PDF into multiple files based on the given mode."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    with fitz.open(input_path) as doc:
        total = doc.page_count
        if total == 0:
            raise ValueError(f"{input_path.name} has no pages.")

        chunks = _compute_chunks(options, total)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.stem
        output_paths: list[Path] = []

        for chunk_index, page_indices in enumerate(chunks, start=1):
            out_doc = fitz.open()
            for page_index in page_indices:
                out_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)

            name = _chunk_filename(stem, page_indices, chunk_index, options.mode)
            out_path = output_dir / name
            out_doc.save(out_path)
            out_doc.close()
            output_paths.append(out_path)

    return SplitResult(output_paths=output_paths)


def _compute_chunks(options: SplitOptions, total: int) -> list[list[int]]:
    if options.mode == SplitMode.EACH_PAGE:
        return [[i] for i in range(total)]

    if options.mode == SplitMode.EVERY_N:
        n = max(1, options.every_n)
        return [list(range(i, min(i + n, total))) for i in range(0, total, n)]

    if options.mode == SplitMode.RANGES:
        indices = parse_page_range(options.page_spec, total_pages=total)
        chunks: list[list[int]] = []
        current: list[int] = []
        for i, idx in enumerate(indices):
            if current and idx != indices[i - 1] + 1:
                chunks.append(current)
                current = []
            current.append(idx)
        if current:
            chunks.append(current)
        return chunks

    raise ValueError(f"Unknown split mode: {options.mode}")


def _chunk_filename(stem: str, indices: list[int], chunk_index: int, mode: SplitMode) -> str:
    if mode == SplitMode.EACH_PAGE:
        return f"{stem}_page_{indices[0] + 1}.pdf"
    if len(indices) == 1:
        return f"{stem}_page_{indices[0] + 1}.pdf"
    return f"{stem}_pages_{indices[0] + 1}-{indices[-1] + 1}.pdf"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_split.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Lint and full test suite**

Run: `ruff check src/anm/tools/split.py tests/test_split.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/split.py tests/test_split.py
git commit -m "feat: add split tool — ranges, every-N, each-page modes"
```

---

## Task 3: Rotate Tool

**Files:**
- Create: `src/anm/tools/rotate.py`
- Test: `tests/test_rotate.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rotate.py
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.rotate import RotateOptions, RotateResult, rotate_pdf


def make_pdf(path: Path, num_pages: int) -> None:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_rotate_all_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 3)
    output = tmp_path / "rotated.pdf"

    result = rotate_pdf(source, RotateOptions(angle=90, page_spec="all"), output_path=output)

    assert result.output_path == output
    doc = fitz.open(output)
    for page in doc:
        assert page.rotation == 90
    doc.close()


def test_rotate_specific_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 4)
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, RotateOptions(angle=180, page_spec="1,3"), output_path=output)

    doc = fitz.open(output)
    assert doc[0].rotation == 180
    assert doc[1].rotation == 0
    assert doc[2].rotation == 180
    assert doc[3].rotation == 0
    doc.close()


def test_rotate_270(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, RotateOptions(angle=270, page_spec="all"), output_path=output)

    doc = fitz.open(output)
    assert doc[0].rotation == 270
    doc.close()


def test_rotate_invalid_angle_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)

    with pytest.raises(ValueError, match="angle"):
        rotate_pdf(
            source,
            RotateOptions(angle=45, page_spec="all"),
            output_path=tmp_path / "out.pdf",
        )


def test_rotate_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rotate_pdf(
            tmp_path / "missing.pdf",
            RotateOptions(angle=90, page_spec="all"),
            output_path=tmp_path / "out.pdf",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rotate.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement rotate tool**

```python
# src/anm/tools/rotate.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range

VALID_ANGLES = {90, 180, 270}


@dataclass(slots=True)
class RotateOptions:
    angle: int = 90
    page_spec: str = "all"


@dataclass(slots=True)
class RotateResult:
    output_path: Path
    pages_rotated: int = 0


def rotate_pdf(
    input_path: Path,
    options: RotateOptions,
    *,
    output_path: Path,
) -> RotateResult:
    """Rotate selected pages of a PDF by 90, 180, or 270 degrees."""
    if options.angle not in VALID_ANGLES:
        raise ValueError(f"Invalid angle: {options.angle}. Must be one of {sorted(VALID_ANGLES)}.")

    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)
        for idx in indices:
            page = doc[idx]
            page.set_rotation(page.rotation + options.angle)
        doc.save(output_path)

    return RotateResult(output_path=output_path, pages_rotated=len(indices))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rotate.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Lint and full suite**

Run: `ruff check src/anm/tools/rotate.py tests/test_rotate.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/rotate.py tests/test_rotate.py
git commit -m "feat: add rotate tool — 90/180/270 on selected pages"
```

---

## Task 4: Reorder Tool

**Files:**
- Create: `src/anm/tools/reorder.py`
- Test: `tests/test_reorder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_reorder.py
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.reorder import ReorderOptions, reorder_pdf


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_reorder_reverses(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])
    output = tmp_path / "reordered.pdf"

    reorder_pdf(source, ReorderOptions(order=[3, 2, 1]), output_path=output)

    doc = fitz.open(output)
    assert doc.page_count == 3
    assert "C" in doc[0].get_text()
    assert "B" in doc[1].get_text()
    assert "A" in doc[2].get_text()
    doc.close()


def test_reorder_subset_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])

    with pytest.raises(ValueError, match="must include every page exactly once"):
        reorder_pdf(source, ReorderOptions(order=[1, 2]), output_path=tmp_path / "out.pdf")


def test_reorder_duplicates_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])

    with pytest.raises(ValueError, match="must include every page exactly once"):
        reorder_pdf(source, ReorderOptions(order=[1, 1]), output_path=tmp_path / "out.pdf")


def test_reorder_identity(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["X", "Y"])
    output = tmp_path / "out.pdf"

    reorder_pdf(source, ReorderOptions(order=[1, 2]), output_path=output)

    doc = fitz.open(output)
    assert "X" in doc[0].get_text()
    assert "Y" in doc[1].get_text()
    doc.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reorder.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement reorder tool**

```python
# src/anm/tools/reorder.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz


@dataclass(slots=True)
class ReorderOptions:
    order: list[int] = field(default_factory=list)


@dataclass(slots=True)
class ReorderResult:
    output_path: Path


def reorder_pdf(
    input_path: Path,
    options: ReorderOptions,
    *,
    output_path: Path,
) -> ReorderResult:
    """Reorder pages of a PDF. `order` is a list of 1-based page numbers."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    with fitz.open(input_path) as doc:
        total = doc.page_count
        expected = set(range(1, total + 1))
        provided = options.order

        if set(provided) != expected or len(provided) != total:
            raise ValueError(
                f"Order must include every page exactly once (1-{total}). "
                f"Got: {provided}"
            )

        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        out_doc = fitz.open()
        for page_num in provided:
            out_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
        out_doc.save(output_path)
        out_doc.close()

    return ReorderResult(output_path=output_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reorder.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and full suite**

Run: `ruff check src/anm/tools/reorder.py tests/test_reorder.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/reorder.py tests/test_reorder.py
git commit -m "feat: add reorder tool — rearrange pages by index"
```

---

## Task 5: Delete Pages Tool

**Files:**
- Create: `src/anm/tools/delete_pages.py`
- Test: `tests/test_delete_pages.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_delete_pages.py
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.delete_pages import DeletePagesOptions, delete_pages


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_delete_middle_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C"])
    output = tmp_path / "out.pdf"

    result = delete_pages(source, DeletePagesOptions(page_spec="2"), output_path=output)

    assert result.pages_removed == 1
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "A" in doc[0].get_text()
    assert "C" in doc[1].get_text()
    doc.close()


def test_delete_range(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D", "E"])
    output = tmp_path / "out.pdf"

    result = delete_pages(source, DeletePagesOptions(page_spec="2-4"), output_path=output)

    assert result.pages_removed == 3
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "A" in doc[0].get_text()
    assert "E" in doc[1].get_text()
    doc.close()


def test_delete_all_pages_raises(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])

    with pytest.raises(ValueError, match="Cannot delete all"):
        delete_pages(source, DeletePagesOptions(page_spec="all"), output_path=tmp_path / "out.pdf")


def test_delete_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        delete_pages(
            tmp_path / "missing.pdf",
            DeletePagesOptions(page_spec="1"),
            output_path=tmp_path / "out.pdf",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_delete_pages.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement delete pages tool**

```python
# src/anm/tools/delete_pages.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range


@dataclass(slots=True)
class DeletePagesOptions:
    page_spec: str = ""


@dataclass(slots=True)
class DeletePagesResult:
    output_path: Path
    pages_removed: int = 0


def delete_pages(
    input_path: Path,
    options: DeletePagesOptions,
    *,
    output_path: Path,
) -> DeletePagesResult:
    """Remove selected pages from a PDF."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        total = doc.page_count
        to_delete = parse_page_range(options.page_spec, total_pages=total)

        if len(to_delete) >= total:
            raise ValueError("Cannot delete all pages from a PDF.")

        keep = [i for i in range(total) if i not in set(to_delete)]
        out_doc = fitz.open()
        for idx in keep:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        out_doc.save(output_path)
        out_doc.close()

    return DeletePagesResult(output_path=output_path, pages_removed=len(to_delete))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_delete_pages.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and full suite**

Run: `ruff check src/anm/tools/delete_pages.py tests/test_delete_pages.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/delete_pages.py tests/test_delete_pages.py
git commit -m "feat: add delete-pages tool — remove pages by range"
```

---

## Task 6: Extract Pages Tool

**Files:**
- Create: `src/anm/tools/extract.py`
- Test: `tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extract.py
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from anm.tools.extract import ExtractOptions, extract_pages


def make_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_specific_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D", "E"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="2,4"), output_path=output)

    assert result.pages_extracted == 2
    doc = fitz.open(output)
    assert doc.page_count == 2
    assert "B" in doc[0].get_text()
    assert "D" in doc[1].get_text()
    doc.close()


def test_extract_range(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B", "C", "D"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="2-4"), output_path=output)

    assert result.pages_extracted == 3
    doc = fitz.open(output)
    assert doc.page_count == 3
    doc.close()


def test_extract_all(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, ["A", "B"])
    output = tmp_path / "extracted.pdf"

    result = extract_pages(source, ExtractOptions(page_spec="all"), output_path=output)

    assert result.pages_extracted == 2


def test_extract_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_pages(
            tmp_path / "missing.pdf",
            ExtractOptions(page_spec="1"),
            output_path=tmp_path / "out.pdf",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extract.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement extract tool**

```python
# src/anm/tools/extract.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from .page_range import parse_page_range


@dataclass(slots=True)
class ExtractOptions:
    page_spec: str = ""


@dataclass(slots=True)
class ExtractResult:
    output_path: Path
    pages_extracted: int = 0


def extract_pages(
    input_path: Path,
    options: ExtractOptions,
    *,
    output_path: Path,
) -> ExtractResult:
    """Extract selected pages from a PDF into a new file."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        indices = parse_page_range(options.page_spec, total_pages=doc.page_count)

        out_doc = fitz.open()
        for idx in indices:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        out_doc.save(output_path)
        out_doc.close()

    return ExtractResult(output_path=output_path, pages_extracted=len(indices))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extract.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and full suite**

Run: `ruff check src/anm/tools/extract.py tests/test_extract.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/tools/extract.py tests/test_extract.py
git commit -m "feat: add extract tool — pull pages into new PDF"
```

---

## Task 7: CLI Subcommands for Phase 1 Tools

Add `split`, `rotate`, `reorder`, `delete-pages`, `extract` subcommands to existing CLI. Follow existing patterns in `cli.py`.

**Files:**
- Modify: `src/anm/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Add to `tests/test_cli.py`:

```python
# Append to existing tests/test_cli.py


def test_split_each_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, "hello")
    # Add a second page
    doc = fitz.open(source)
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
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_cli.py::test_split_each_page -v`
Expected: FAIL — `SystemExit` or unknown command

- [ ] **Step 3: Add CLI subcommands to `cli.py`**

Add these subcommands in `build_parser()` after the `doctor` command (around line 165), and add corresponding handler functions after `handle_doctor()`:

In `build_parser()`, add after the doctor block:

```python
    split = add_command(
        "split",
        help="split a PDF into multiple files",
        description="Split a PDF by page ranges, every N pages, or each page.",
        epilog="Examples:\n  anm split .\\a.pdf --output .\\out\\\n  anm split .\\a.pdf --pages 1-3,5 --output .\\out\\",
    )
    split.add_argument("pdf", type=Path, help="PDF to split")
    split.add_argument("--pages", default=None, help="page ranges (e.g. 1-3,5)")
    split.add_argument("--every", type=int, default=None, help="split every N pages")
    split.add_argument("--output", "-o", required=True, type=Path, help="output directory")
    split.add_argument("--json", action="store_true", help="print machine-readable JSON")
    split.set_defaults(handler=handle_split)

    rotate = add_command(
        "rotate",
        help="rotate pages in a PDF",
        description="Rotate selected pages by 90, 180, or 270 degrees.",
        epilog="Examples:\n  anm rotate .\\a.pdf --angle 90 --output .\\rotated.pdf",
    )
    rotate.add_argument("pdf", type=Path, help="PDF to rotate")
    rotate.add_argument("--angle", type=int, required=True, choices=[90, 180, 270])
    rotate.add_argument("--pages", default="all", help="page selection (default: all)")
    rotate.add_argument("--output", "-o", required=True, type=Path, help="output PDF path")
    rotate.add_argument("--json", action="store_true", help="print machine-readable JSON")
    rotate.set_defaults(handler=handle_rotate)

    reorder = add_command(
        "reorder",
        help="reorder pages in a PDF",
        description="Rearrange pages by specifying new order.",
        epilog="Examples:\n  anm reorder .\\a.pdf --order 3,1,2 --output .\\reordered.pdf",
    )
    reorder.add_argument("pdf", type=Path, help="PDF to reorder")
    reorder.add_argument("--order", required=True, help="comma-separated 1-based page order")
    reorder.add_argument("--output", "-o", required=True, type=Path, help="output PDF path")
    reorder.add_argument("--json", action="store_true", help="print machine-readable JSON")
    reorder.set_defaults(handler=handle_reorder)

    del_pages = add_command(
        "delete-pages",
        help="delete pages from a PDF",
        description="Remove selected pages from a PDF.",
        epilog="Examples:\n  anm delete-pages .\\a.pdf --pages 2,4-6 --output .\\trimmed.pdf",
    )
    del_pages.add_argument("pdf", type=Path, help="PDF to modify")
    del_pages.add_argument("--pages", required=True, help="pages to delete (e.g. 2,4-6)")
    del_pages.add_argument("--output", "-o", required=True, type=Path, help="output PDF path")
    del_pages.add_argument("--json", action="store_true", help="print machine-readable JSON")
    del_pages.set_defaults(handler=handle_delete_pages)

    extract = add_command(
        "extract",
        help="extract pages from a PDF",
        description="Extract selected pages into a new PDF.",
        epilog="Examples:\n  anm extract .\\a.pdf --pages 1,3,7-9 --output .\\extracted.pdf",
    )
    extract.add_argument("pdf", type=Path, help="PDF to extract from")
    extract.add_argument("--pages", required=True, help="pages to extract (e.g. 1,3,7-9)")
    extract.add_argument("--output", "-o", required=True, type=Path, help="output PDF path")
    extract.add_argument("--json", action="store_true", help="print machine-readable JSON")
    extract.set_defaults(handler=handle_extract)
```

Add handler functions after `handle_doctor()`:

```python
def handle_split(
    args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    from .tools.split import SplitMode, SplitOptions, split_pdf

    if args.pages:
        options = SplitOptions(mode=SplitMode.RANGES, page_spec=args.pages)
    elif args.every:
        options = SplitOptions(mode=SplitMode.EVERY_N, every_n=args.every)
    else:
        options = SplitOptions(mode=SplitMode.EACH_PAGE)

    result = split_pdf(source, options, output_dir=args.output)

    payload = {
        "ok": True,
        "command": "split",
        "inputs": [str(source)],
        "outputs": stringify_paths(result.output_paths),
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Split into {len(result.output_paths)} file(s) in {args.output}\n")
    return 0


def handle_rotate(
    args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    from .tools.rotate import RotateOptions, rotate_pdf

    result = rotate_pdf(source, RotateOptions(angle=args.angle, page_spec=args.pages), output_path=args.output)

    payload = {
        "ok": True,
        "command": "rotate",
        "inputs": [str(source)],
        "output": str(result.output_path),
        "pages_rotated": result.pages_rotated,
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Rotated {result.pages_rotated} page(s) → {result.output_path}\n")
    return 0


def handle_reorder(
    args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    from .tools.reorder import ReorderOptions, reorder_pdf

    order = [int(x.strip()) for x in args.order.split(",")]
    result = reorder_pdf(source, ReorderOptions(order=order), output_path=args.output)

    payload = {
        "ok": True,
        "command": "reorder",
        "inputs": [str(source)],
        "output": str(result.output_path),
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Reordered → {result.output_path}\n")
    return 0


def handle_delete_pages(
    args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    from .tools.delete_pages import DeletePagesOptions, delete_pages

    result = delete_pages(source, DeletePagesOptions(page_spec=args.pages), output_path=args.output)

    payload = {
        "ok": True,
        "command": "delete-pages",
        "inputs": [str(source)],
        "output": str(result.output_path),
        "pages_removed": result.pages_removed,
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Removed {result.pages_removed} page(s) → {result.output_path}\n")
    return 0


def handle_extract(
    args: argparse.Namespace, stdout: TextIO, stderr: TextIO, _gui_runner: Any
) -> int:
    source = validate_pdf_paths([args.pdf])[0]
    from .tools.extract import ExtractOptions, extract_pages

    result = extract_pages(source, ExtractOptions(page_spec=args.pages), output_path=args.output)

    payload = {
        "ok": True,
        "command": "extract",
        "inputs": [str(source)],
        "output": str(result.output_path),
        "pages_extracted": result.pages_extracted,
        "warnings": [],
    }
    if args.json:
        write_json(stdout, payload)
    else:
        stdout.write(f"Extracted {result.pages_extracted} page(s) → {result.output_path}\n")
    return 0
```

- [ ] **Step 4: Run all CLI tests**

Run: `pytest tests/test_cli.py -v`
Expected: All tests PASS (old + new)

- [ ] **Step 5: Lint and full suite**

Run: `ruff check src/anm/cli.py tests/test_cli.py && pytest -v`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add src/anm/cli.py tests/test_cli.py
git commit -m "feat: add CLI subcommands for split, rotate, reorder, delete-pages, extract"
```

---

## Task 8: GUI Hub Refactor

Extract current `gui.py` into `gui/` package. Hub manages menu + panel switching. Current GUI becomes `annotate_merge.py` panel. Old `gui.py` import path preserved via `gui/__init__.py`.

**Files:**
- Create: `src/anm/gui/__init__.py`
- Create: `src/anm/gui/widgets.py`
- Create: `src/anm/gui/annotate_merge.py`
- Create: `src/anm/gui/hub.py`
- Delete: `src/anm/gui.py` (replaced by package)
- Modify: `src/anm/main.py`
- Modify: `src/anm/cli.py` (line 244 and 511 — `from .gui import PDFAnnotatorApp`)

- [ ] **Step 1: Create `gui/widgets.py` — extract Tooltip**

```python
# src/anm/gui/widgets.py
from __future__ import annotations

import tkinter as tk


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide)

    def show(self, _event: object | None = None) -> None:
        if self.window is not None:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 8
        y = self.widget.winfo_rooty()
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=5,
            wraplength=340,
        )
        label.pack()

    def hide(self, _event: object | None = None) -> None:
        if self.window is None:
            return
        self.window.destroy()
        self.window = None
```

- [ ] **Step 2: Create `gui/annotate_merge.py` — move PDFAnnotatorApp body into a Frame**

Take the entire body of `PDFAnnotatorApp._build_ui` and all its instance methods, adapt to be a `ttk.Frame` subclass instead of `BaseTk`. The hub will own the window, status bar, and progress bar. The panel manages its own internal layout.

This is a large mechanical refactor — copy `gui.py` lines 67–584 into `annotate_merge.py`, change the class to extend `ttk.Frame`, and remove window-level calls (`self.title`, `self.geometry`, `self.minsize`, `self._set_dpi_awareness`). The hub provides `status_var`, `progress_var`, and `event_queue` to the panel via constructor args.

```python
# src/anm/gui/annotate_merge.py
# Full content: the entire current PDFAnnotatorApp class, refactored to extend ttk.Frame.
# Constructor signature: __init__(self, parent, *, status_var, progress_var, event_queue)
# Remove: self.title(), self.geometry(), self.minsize(), _set_dpi_awareness()
# Keep: all other methods unchanged
# Import Tooltip from .widgets instead of defining it inline
```

The exact refactor is mechanical — the implementing agent should:
1. Copy `gui.py` content
2. Change `class PDFAnnotatorApp(BaseTk)` → `class AnnotateMergePanel(ttk.Frame)`
3. Change `super().__init__()` → `super().__init__(parent)`
4. Accept `status_var`, `progress_var`, `event_queue` as constructor args instead of creating them
5. Remove window-level setup (title, geometry, minsize, dpi)
6. Import `Tooltip` from `.widgets`
7. Keep drag-and-drop registration (the hub registers on the root window instead)

- [ ] **Step 3: Create `gui/hub.py` — main window with menu and panel container**

```python
# src/anm/gui/hub.py
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

BaseTk = TkinterDnD.Tk if TkinterDnD is not None else tk.Tk


class PDFToolkitApp(BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AnM — PDF Toolkit")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self._set_dpi_awareness()

        self.status_var = tk.StringVar(value="Select a tool from the menu.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._panels: dict[str, ttk.Frame] = {}
        self._active_panel: ttk.Frame | None = None

        self._build_menu()
        self._build_layout()
        self._show_panel("annotate_merge")
        self.after(100, self._drain_events)

    def _set_dpi_awareness(self) -> None:
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            return

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Annotate && Merge",
            command=lambda: self._show_panel("annotate_merge"),
        )
        # Phase 1 tools — GUI panels added in a future plan after design agent
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=menubar)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self._panel_container = ttk.Frame(self)
        self._panel_container.grid(row=0, column=0, sticky="nsew")
        self._panel_container.columnconfigure(0, weight=1)
        self._panel_container.rowconfigure(0, weight=1)

        status = ttk.Label(
            self, textvariable=self.status_var, padding=(12, 0, 12, 12), anchor="w"
        )
        status.grid(row=1, column=0, sticky="ew")

    def _get_panel(self, name: str) -> ttk.Frame:
        if name not in self._panels:
            self._panels[name] = self._create_panel(name)
        return self._panels[name]

    def _create_panel(self, name: str) -> ttk.Frame:
        if name == "annotate_merge":
            from .annotate_merge import AnnotateMergePanel
            return AnnotateMergePanel(
                self._panel_container,
                status_var=self.status_var,
                progress_var=self.progress_var,
                event_queue=self.event_queue,
            )
        raise ValueError(f"Unknown panel: {name}")

    def _show_panel(self, name: str) -> None:
        panel = self._get_panel(name)
        if self._active_panel is not None:
            self._active_panel.grid_forget()
        panel.grid(row=0, column=0, sticky="nsew")
        self._active_panel = panel
        if hasattr(panel, "reset"):
            panel.reset()

    def _drain_events(self) -> None:
        while True:
            try:
                event_type, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break
            if self._active_panel and hasattr(self._active_panel, "handle_event"):
                self._active_panel.handle_event(event_type, payload)
        self.after(100, self._drain_events)
```

- [ ] **Step 4: Create `gui/__init__.py` for backward compatibility**

```python
# src/anm/gui/__init__.py
from .hub import PDFToolkitApp

# Backward compat: cli.py and main.py import PDFAnnotatorApp from .gui
PDFAnnotatorApp = PDFToolkitApp
```

- [ ] **Step 5: Delete old `gui.py` and update imports**

Delete `src/anm/gui.py`.

In `src/anm/main.py`, the import `from .gui import PDFAnnotatorApp` will now resolve to `gui/__init__.py` → works with no changes.

In `src/anm/cli.py` line 244 and 511, same — `from .gui import PDFAnnotatorApp` resolves to `gui/__init__.py`.

- [ ] **Step 6: Run all existing tests**

Run: `pytest -v`
Expected: All existing tests still pass. The GUI smoke test imports `PDFAnnotatorApp` which now resolves through `gui/__init__.py`.

- [ ] **Step 7: Lint**

Run: `ruff check src/anm/gui/ && pytest -v`
Expected: Clean

- [ ] **Step 8: Commit**

```bash
git add src/anm/gui/ && git rm src/anm/gui.py
git add src/anm/main.py src/anm/cli.py
git commit -m "refactor: extract gui.py into gui/ package with hub + panel architecture"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Page range parser, split, rotate, reorder, delete, extract all have tasks. Hub refactor covered. CLI subcommands covered. GUI panels deferred (spec says design agent runs first).
- [x] **Placeholder scan:** No TBD/TODO. All code blocks complete. Task 8 step 2 is intentionally high-level for the mechanical refactor — the implementing agent copies and adapts existing code.
- [x] **Type consistency:** `SplitOptions`, `SplitResult`, `split_pdf` — names consistent across tests, tool, and CLI. Same for all tools. `parse_page_range` signature consistent everywhere.
- [x] **Existing tests preserved:** No modifications to existing test files except appending new CLI tests to `test_cli.py`.
