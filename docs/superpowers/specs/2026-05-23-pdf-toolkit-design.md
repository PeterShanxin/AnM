# AnM PDF Toolkit — Design Spec

## Overview

Evolve AnM from a single-purpose annotate-and-merge tool into a full PDF Swiss Army
knife. All tools share one desktop window (tkinter), accessed via a menu bar. Each tool
also exposes a CLI subcommand. Inspired by Stirling-PDF's feature set, adapted for a
lightweight Python/PyMuPDF desktop app.

**Audience:** Office workers, students, personal use — anyone with day-to-day PDF friction.

**Stack:** Python 3.11+, PyMuPDF (fitz), tkinter/tkinterdnd2, Tesseract (optional, Phase 3).

---

## Architecture

### App structure

```
AnM (main window)
├── Menu bar: [Annotate & Merge | Split | Rotate | ...]
├── Tool panel (swaps per menu selection)
└── Shared status bar + progress
```

### Code layout

```
src/anm/
├── main.py                # Entry point (unchanged)
├── cli.py                 # CLI router — subcommand per tool
├── models.py              # Shared dataclasses
├── app_state.py           # Shared file selection model
├── pipeline.py            # Existing annotate+merge logic (stays intact)
├── gui/
│   ├── __init__.py
│   ├── hub.py             # Main window, menu bar, panel container
│   ├── annotate_merge.py  # Current GUI refactored into a panel
│   ├── split.py
│   ├── rotate.py
│   ├── reorder.py
│   ├── delete_pages.py
│   ├── extract.py
│   ├── compress.py
│   ├── to_images.py
│   ├── from_images.py
│   ├── watermark.py
│   ├── page_numbers.py
│   ├── metadata.py
│   ├── protect.py
│   ├── unlock.py
│   ├── flatten.py
│   ├── compare.py
│   └── ocr.py
├── tools/
│   ├── __init__.py
│   ├── split.py
│   ├── rotate.py
│   ├── reorder.py
│   ├── delete_pages.py
│   ├── extract.py
│   ├── compress.py
│   ├── to_images.py
│   ├── from_images.py
│   ├── watermark.py
│   ├── page_numbers.py
│   ├── metadata.py
│   ├── protect.py
│   ├── unlock.py
│   ├── flatten.py
│   ├── compare.py
│   └── ocr.py
```

### Key principles

- **`tools/`** = pure functions, zero GUI dependency. CLI and GUI both call these.
- **`gui/`** = tkinter panels. Each tool panel is a `ttk.Frame` subclass.
- **Hub** manages panel switching — one active panel at a time.
- **Existing `pipeline.py`** stays intact — becomes one tool among many.
- **`FileSelectionModel`** gets reused where tools need file input.
- All new dataclasses use `@dataclass(slots=True)` for consistency.

### Shared patterns

Each tool module in `tools/` follows this contract:

```python
@dataclass(slots=True)
class SplitOptions:
    """Tool-specific options dataclass."""
    ...

@dataclass(slots=True)
class SplitResult:
    """Tool-specific result dataclass."""
    ...

def split_pdf(
    input_path: Path,
    options: SplitOptions,
    progress_callback: ProgressCallback | None = None,
    cancel_event: object | None = None,
) -> SplitResult:
    """Pure function. No GUI. No CLI. Just logic."""
    ...
```

Each GUI panel in `gui/` follows:

```python
class SplitPanel(ttk.Frame):
    """Self-contained panel with file input, options, action button, status."""

    def __init__(self, parent: tk.Widget) -> None: ...
    def reset(self) -> None: ...  # Called when panel is shown
```

Each CLI subcommand in `cli.py` follows existing patterns: argparse handler,
`--json` flag, `--dry-run` where applicable.

---

## Tool Specifications

### Phase 1 — Core page operations

All Phase 1 tools use PyMuPDF only. No new dependencies.

#### 1. Split

- **Input:** Single PDF
- **Modes:**
  - By page range: `1-3,5,8-10` → one PDF per range segment
  - Every N pages: split into chunks of N
  - Each page: one PDF per page
- **Output:** Multiple PDFs to chosen folder
- **Naming:** `{stem}_pages_{range}.pdf` or `{stem}_page_{n}.pdf`
- **CLI:** `anm split input.pdf --pages 1-3,5 --output ./out/`
- **CLI:** `anm split input.pdf --every 5 --output ./out/`
- **PyMuPDF:** `insert_pdf(src, from_page, to_page)` on new doc per segment

#### 2. Rotate

- **Input:** Single PDF
- **Page selection:** All, range, or pick from list
- **Rotation:** 90, 180, 270 degrees clockwise
- **Output:** New rotated PDF (or overwrite with confirmation)
- **CLI:** `anm rotate input.pdf --pages 1,3-5 --angle 90 --output rotated.pdf`
- **PyMuPDF:** `page.set_rotation(angle)`

#### 3. Reorder

- **Input:** Single PDF
- **GUI:** Thumbnail grid with drag-and-drop reordering
- **CLI:** `anm reorder input.pdf --order 3,1,2,5,4 --output reordered.pdf`
- **PyMuPDF:** Build new doc with `insert_pdf` per page in desired order

#### 4. Delete Pages

- **Input:** Single PDF
- **Select:** Pages to remove (range syntax or pick)
- **Preview:** Show page count before/after
- **CLI:** `anm delete-pages input.pdf --pages 2,4-6 --output trimmed.pdf`
- **PyMuPDF:** `document.delete_pages(page_list)`

#### 5. Extract Pages

- **Input:** Single PDF
- **Select:** Pages to extract into new PDF
- **Inverse of delete** — same selection UI, different operation
- **CLI:** `anm extract input.pdf --pages 1,3,7-9 --output extracted.pdf`
- **PyMuPDF:** `insert_pdf(src, from_page, to_page)` for selected pages

### Phase 2 — Transform & convert

#### 6. Compress

- **Input:** Single or batch PDFs
- **Quality presets:**
  - High (best quality, mild compression)
  - Medium (balanced)
  - Low (smallest file, visible quality loss on images)
- **Shows:** Before/after file size comparison
- **CLI:** `anm compress input.pdf --quality medium --output compressed.pdf`
- **PyMuPDF:** `save(deflate=True, garbage=4, clean=True)` + image
  downsampling via `page.get_images()` + re-insert at lower resolution

#### 7. PDF to Images

- **Input:** Single PDF
- **Output:** PNG or JPG, one image per page
- **Options:** DPI (72, 150, 300), page range, image format
- **CLI:** `anm to-images input.pdf --format png --dpi 300 --output ./images/`
- **PyMuPDF:** `page.get_pixmap(matrix=fitz.Matrix(scale, scale))`

#### 8. Images to PDF

- **Input:** Multiple images (PNG, JPG, BMP, TIFF)
- **Options:** Page size (A4, Letter, fit-to-image), orientation (auto/portrait/landscape)
- **GUI:** Drag-and-drop ordering (reuse `FileSelectionModel`)
- **CLI:** `anm from-images img1.jpg img2.png --page-size A4 --output album.pdf`
- **PyMuPDF:** `page.insert_image(rect, filename=path)`

#### 9. Watermark

- **Input:** Single PDF
- **Text watermark:** Custom text, font size, color, opacity, rotation angle
- **Position modes:** Diagonal (centered), tiled (repeat grid), header/footer
- **Extends:** Existing annotation engine pattern from `pipeline.py`
- **CLI:** `anm watermark input.pdf --text "CONFIDENTIAL" --opacity 0.3 --rotation 45 --output wm.pdf`
- **PyMuPDF:** `page.insert_text()` with transformation matrix for rotation

#### 10. Page Numbers

- **Input:** Single PDF
- **Format:** `{page}`, `Page {page} of {total}`, custom template
- **Position:** Same 6 positions as existing annotation system
- **Options:** Start number, skip first N pages, font size, opacity
- **CLI:** `anm page-numbers input.pdf --format "Page {page} of {total}" --position bottom-center --output numbered.pdf`
- **Extends:** Existing annotation engine — reuse `build_annotation_rect`

#### 11. Metadata Editor

- **Input:** Single PDF
- **Fields:** Title, author, subject, keywords, creator, producer
- **GUI:** Form with current values pre-filled, edit and save
- **CLI (read):** `anm metadata input.pdf --show`
- **CLI (write):** `anm metadata input.pdf --set title="My Doc" --set author="Name" --output updated.pdf`
- **PyMuPDF:** `document.metadata` (read), `document.set_metadata(dict)` (write)

### Phase 3 — Security & advanced

#### 12. Protect (Encrypt)

- **User password:** Required to open
- **Owner password:** Required to change permissions
- **Permission flags:** Print, copy, modify
- **CLI:** `anm protect input.pdf --user-password "abc" --no-print --output protected.pdf`
- **PyMuPDF:** `save(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=..., owner_pw=..., permissions=...)`

#### 13. Unlock

- **User provides password**, outputs unprotected copy
- **CLI:** `anm unlock input.pdf --password "abc" --output unlocked.pdf`
- **PyMuPDF:** `fitz.open(path, password=pw)` then `save()` without encryption

#### 14. Flatten

- **Flatten annotations and form fields** into static page content
- **CLI:** `anm flatten input.pdf --output flat.pdf`
- **PyMuPDF:** Iterate pages, use `page.annots()` to bake annotations, then
  remove annotation objects

#### 15. Compare

- **Input:** Two PDFs
- **GUI:** Side-by-side preview panes, pixel differences highlighted in red
- **Output:** Optional diff PDF with highlighted changes
- **CLI:** `anm compare a.pdf b.pdf --output diff.pdf`
- **PyMuPDF:** Render both pages as pixmaps, compute pixel difference,
  overlay red on changed regions

#### 16. OCR

- **Requires:** Tesseract (external dependency, checked by `anm doctor`)
- **Language selection** from installed Tesseract language packs
- **Adds invisible text layer** to scanned pages (searchable PDF)
- **CLI:** `anm ocr scanned.pdf --lang eng --output searchable.pdf`
- **Dependency:** `pytesseract` or direct subprocess call to `tesseract`

---

## Dependencies

| Dependency | Phase | Required? | Purpose |
|---|---|---|---|
| PyMuPDF (fitz) | All | Yes | PDF manipulation engine |
| tkinterdnd2 | All | Yes | Drag-and-drop in GUI |
| Pillow | Phase 2 | Optional | Extended image format support (TIFF, BMP). PyMuPDF handles PNG/JPG natively. |
| Tesseract | Phase 3 | Optional | OCR engine (external binary) |

---

## CLI Summary

All subcommands follow existing patterns: `--json`, `--output/-o`, consistent
error handling via `emit_error`.

```
anm gui                    # Open desktop app (default)
anm merge ...              # Existing annotate+merge
anm merge-dir ...          # Existing folder merge
anm split ...              # Phase 1
anm rotate ...             # Phase 1
anm reorder ...            # Phase 1
anm delete-pages ...       # Phase 1
anm extract ...            # Phase 1
anm compress ...           # Phase 2
anm to-images ...          # Phase 2
anm from-images ...        # Phase 2
anm watermark ...          # Phase 2
anm page-numbers ...       # Phase 2
anm metadata ...           # Phase 2
anm protect ...            # Phase 3
anm unlock ...             # Phase 3
anm flatten ...            # Phase 3
anm compare ...            # Phase 3
anm ocr ...                # Phase 3
anm preview ...            # Existing
anm info ...               # Existing
anm doctor ...             # Existing (extended to check Tesseract)
```

---

## Design Agent Prompt

Use this when ready to design the UI:

> AnM is a Python/tkinter PDF toolkit desktop app. Currently single-purpose
> (annotate + merge PDFs). Evolving into a multi-tool hub with a menu to
> switch between tools: Split, Rotate, Reorder, Delete Pages, Extract,
> Compress, PDF↔Images, Watermark, Page Numbers, Metadata, Protect, Unlock,
> Flatten, Compare, OCR. Each tool is a panel that swaps in the main window.
> Explore a few UI layout options — sidebar nav vs top menu vs something
> else. Consider the tool count (~16 tools) and how to keep navigation
> clean. Windows-first, supports high DPI. Current window is 1180x760.

---

## Migration Notes

- Current `gui.py` (584 lines) refactors into `gui/hub.py` + `gui/annotate_merge.py`
- Current `pipeline.py` stays unchanged — it becomes the backend for annotate+merge panel
- Current CLI subcommands (`merge`, `merge-dir`, `preview`, `info`, `doctor`, `gui`)
  remain intact, new subcommands added alongside
- No breaking changes to existing functionality
