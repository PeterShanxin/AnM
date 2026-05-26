# AnM PDF Toolkit — Design Spec

## Overview

Evolve AnM from a single-purpose annotate-and-merge tool into a full PDF Swiss Army
knife. All tools share one desktop window (pywebview hosting an HTML/CSS/JS SPA),
swapped via in-app navigation. Each tool also exposes a CLI subcommand. Inspired by
Stirling-PDF's feature set, adapted for a lightweight Python/PyMuPDF desktop app.

**Audience:** Office workers, students, personal use — anyone with day-to-day PDF friction.

**Stack:** Python 3.11+, PyMuPDF (fitz), pywebview (Edge WebView2 on Windows),
vanilla JS/HTML/CSS for the UI, Tesseract (optional, Phase 3). Legacy tkinter GUI
remains reachable via ``anm --tk`` as a fallback.

---

## Architecture

### App structure

```
AnM (pywebview window)
├── HTML/CSS/JS SPA (Variant B home + Variant A in-tool chrome)
│   ├── Home grid: 16 tools by category
│   └── In-tool view: rail + sidebar + tool main (header + page grid + inspector)
└── Python `Api` bridge (file dialogs, thumbnail render, tool dispatch)
```

The SPA is a single page; navigation between home and per-tool views is
client-side state. The Python ``Api`` object is exposed via
``window.pywebview.api`` and returns ``{ok: bool, data?: any, error?: string}``
dicts for every method.

### Code layout

```
src/anm/
├── __main__.py            # `python -m anm` entry
├── main.py                # Entry point — defaults to web GUI, `--tk` flag falls back to legacy
├── cli.py                 # CLI router — subcommand per tool
├── models.py              # Shared dataclasses
├── app_state.py           # Shared file selection model
├── pipeline.py            # Existing annotate+merge logic (stays intact)
├── gui_web/               # Primary GUI — pywebview + HTML/CSS/JS SPA
│   ├── __init__.py
│   ├── app.py             # WebApp window + `Api` bridge + `_dispatch_tool`
│   └── assets/
│       ├── index.html     # SPA shell
│       ├── app.css        # Design tokens + components (copied from design pkg)
│       ├── app.js         # State, renderers, per-tool inspector functions
│       ├── icons.js       # SVG icon catalog
│       └── catalog.js     # TOOLS + CATEGORIES (mirrors gui/catalog.py)
├── gui/                   # LEGACY tkinter hub (kept for `anm --tk` fallback only)
│   ├── __init__.py
│   ├── hub.py
│   ├── annotate_merge.py
│   └── panels/            # tk panels — do NOT extend for new tools
└── tools/                 # Pure functions, zero GUI dependency
    ├── __init__.py
    ├── split.py
    ├── rotate.py
    ├── reorder.py
    ├── delete_pages.py
    ├── extract.py
    ├── compress.py
    ├── to_images.py
    ├── from_images.py
    ├── watermark.py
    ├── page_numbers.py
    ├── metadata.py
    ├── protect.py
    ├── unlock.py
    ├── flatten.py
    ├── compare.py
    └── ocr.py
```

**For Phase 2 and Phase 3, new tools land as:**
1. A pure-function module in ``tools/<tool>.py``
2. A JS inspector function in ``gui_web/assets/app.js`` (e.g. ``compressInspector()``)
3. A ``_dispatch_tool`` case in ``gui_web/app.py``
4. A ``wired: true`` flag in ``gui_web/assets/catalog.js``
5. A CLI subcommand in ``cli.py``

No new ``gui/<tool>.py`` tkinter panel is required.

### Key principles

- **`tools/`** = pure functions, zero GUI dependency. CLI and GUI both call these.
- **`gui_web/`** = SPA inspectors keyed by ``tool_id``. The Python ``Api`` bridge
  exposes ``run_tool(tool_id, options)``; ``_dispatch_tool`` routes to the matching
  ``tools/*`` function.
- **`gui/`** = LEGACY tkinter hub. Reachable via ``anm --tk`` for fallback only.
  Do not extend for new tools.
- **Hub (SPA)** is a single page; the JS ``state`` object holds ``view``, ``toolId``,
  ``pdf``, ``options``, ``selectedPages``. Re-render on change.
- **Existing `pipeline.py`** stays intact — becomes one tool among many.
- **`FileSelectionModel`** stays server-side as a data model for multi-file tools
  (Merge, From-Images). The JS side sends file paths; Python builds the model.
- All new dataclasses use `@dataclass(slots=True)` for consistency.
- All ``Api`` methods return ``{ok: bool, data?, error?}`` — never raise across the
  JS bridge (pywebview drops the traceback).

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

Each GUI inspector in `gui_web/assets/app.js` follows:

```javascript
// 1. Inspector renderer (returns HTML string, called from renderInspector())
function splitInspector() {
  const o = getOpts('split');           // per-tool option state, defaults provided
  return `
    <div class="cap">Split mode</div>
    <div data-radio="mode" ...>${radioCard('Each page', ..., o.mode === 'each_page', 'each_page')}</div>
    ${o.mode === 'ranges' ? `<input class="anm-input" data-bind="page_spec" ...>` : ''}
    ${outputBlock()}
  `;
}

// 2. Defaults registered inside getOpts()
function getOpts(id) {
  if (!state.options[id]) {
    const defaults = { split: { mode: 'each_page', page_spec: '', every_n: 2 }, ... };
    state.options[id] = defaults[id] || {};
  }
  return state.options[id];
}
```

Binding to ``data-radio`` and ``data-bind`` is handled generically by
``bindTool()``; per-tool code is just the renderer + defaults.

Each Python dispatch case in ``gui_web/app.py`` follows:

```python
def _dispatch_tool(tool_id, pdf, out_dir, opts):
    if tool_id == "split":
        options = SplitOptions(
            mode=SplitMode(opts.get("mode", "each_page")),
            page_spec=str(opts.get("page_spec", "")),
            every_n=int(opts.get("every_n", 1)),
        )
        result = split_pdf(pdf, options, output_dir=out_dir)
        return {
            "outputs": [str(p) for p in result.output_paths],
            "summary": f"Wrote {len(result.output_paths)} file(s) to {out_dir}",
        }
```

Each CLI subcommand in `cli.py` follows existing patterns: argparse handler,
`--json` flag, `--dry-run` where applicable.

---

## Tool Specifications

### Phase 0 — Pre-existing

#### 0. Annotate & Merge

The original AnM tool — concatenate multiple PDFs into one merged file while
optionally stamping a per-source-file annotation (header/footer text) on every
page. Backed by ``src/anm/pipeline.py`` (``process_pdfs``), not a module in
``tools/``.

- **Input:** Multiple PDFs (ordered list)
- **Annotation:**
  - ``text_template`` — placeholders ``{filename}``, ``{stem}``, ``{index}``,
    ``{page_number}``, ``{total_pages}``
  - ``position`` — one of 6 anchors (top/bottom × left/center/right)
  - ``font_size``, ``margin``, ``box_opacity``
- **Output:** Single merged PDF in chosen folder + optional ``annotated/``
  intermediates
- **CLI:** ``anm merge a.pdf b.pdf --output merged.pdf [--text "{filename}"] [--position bottom-right]``
- **CLI (folder):** ``anm merge-dir ./pdfs/ --output merged.pdf``
- **Backend:** ``pipeline.process_pdfs(pdf_paths, AnnotationOptions, RunOptions, ...)``

**Web GUI wire (gui_web):** Special-cased in ``app.js`` because Merge is the
only multi-file tool. The tool body renders a file list (instead of the
single-PDF page grid), with HTML5 drag-reorder. The inspector exposes the
annotation + run options. ``Api.open_pdfs_dialog()`` returns the picked paths;
``Api.run_merge(files, annotation, run)`` dispatches to ``process_pdfs``.

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
- **GUI:** Thumbnail grid with drag-and-drop reordering. Use HTML5 native
  ``draggable``/``dragover``/``drop`` events on the ``.thumb-wrap`` cells, or a
  small library like SortableJS shipped under ``gui_web/assets/vendor/``.
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
- **GUI:** HTML5 file drop into the page-grid host. JS keeps an ordered list of
  file paths in ``state.options.from_images.files``; server-side ``FileSelectionModel``
  is built from that list when ``run_tool`` is called.
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
- **GUI:** Two ``<img>`` columns rendered side-by-side; diff overlay served as a
  third base64 PNG per page from a new ``Api.get_compare_thumbs(left_idx, right_idx)``
  method. Page-grid host swaps to a custom Compare layout for this tool.
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
| pywebview | All | Yes | Native window hosting the HTML/CSS/JS SPA (Edge WebView2 on Windows) |
| tkinterdnd2 | All | Yes (legacy) | Drag-and-drop in legacy ``--tk`` GUI. Web UI uses HTML5 drag-and-drop natively. |
| Pillow | Phase 2 | Optional | Extended image format support (TIFF, BMP). PyMuPDF handles PNG/JPG natively. |
| Tesseract | Phase 3 | Optional | OCR engine (external binary) |

---

## CLI Summary

All subcommands follow existing patterns: `--json`, `--output/-o`, consistent
error handling via `emit_error`.

```
anm                        # Open desktop app (pywebview, default)
anm --tk                   # Open legacy tkinter hub (fallback)
anm gui                    # Same as `anm` — explicit GUI subcommand
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

> AnM is a Windows-first PDF toolkit desktop app. Python backend, but the UI is
> an HTML/CSS/JS SPA rendered by pywebview (Edge WebView2). Currently uses
> design tokens from ``src/anm/gui_web/assets/app.css``: ``--anm-bg #f3f3f3``,
> ``--anm-accent #0067c0``, ``--anm-radius 6/10``, full dark-theme palette
> via ``.anm-dark``. Layout is Variant B for the home launcher (4×N tool
> grid by category, top bar with search + open + theme toggle) and Variant A
> in-tool (56-px icon rail + 232-px sidebar + main content area with 56-px
> tool header, page-thumb grid, and 280-px inspector). Tool count is 16
> across 4 categories. Default window 1280×820. Use real ``border-radius``,
> ``box-shadow``, SVG icons — no faking required. When proposing new
> chrome, keep tokens consistent with ``app.css`` and ship updated
> variants under ``.tmp/design-pkg/`` for diffing.

---

## Migration Notes

- Current `gui.py` (584 lines) refactors into `gui/hub.py` + `gui/annotate_merge.py`
- Current `pipeline.py` stays unchanged — it becomes the backend for annotate+merge panel
- Current CLI subcommands (`merge`, `merge-dir`, `preview`, `info`, `doctor`, `gui`)
  remain intact, new subcommands added alongside
- No breaking changes to existing functionality

### Phase 1.5 — pywebview pivot

After Phase 1 landed, the GUI was rewritten on top of pywebview because tkinter
could not match the design's elegance (real ``border-radius``, ``box-shadow``,
SVG icons, dark theme).

- New package ``src/anm/gui_web/`` with a Python ``Api`` bridge + an HTML/CSS/JS SPA
- Legacy ``src/anm/gui/`` kept reachable via ``anm --tk`` for fallback / debugging
- ``main.py`` defaults to the web GUI; ``--tk`` flag opts back to the tk hub
- ``src/anm/__main__.py`` added so ``python -m anm`` works
- ``pyproject.toml`` gained ``pywebview>=5,<6`` (installed 6.2.1) and
  ``[tool.setuptools.package-data]`` for shipping the SPA assets
- All ``tools/*`` modules unchanged — the pure-function contract held up
- All 76 tests still pass (tk tests run against the legacy ``PDFAnnotatorApp``)

### Phase 2/3 implications

- Do **not** create new ``gui/<tool>.py`` tkinter panels — instead add a JS inspector
  function in ``gui_web/assets/app.js`` and a ``_dispatch_tool`` case in ``gui_web/app.py``
- ``tkinterdnd2`` reference in tool specs no longer applies to the primary GUI;
  use HTML5 drag-and-drop or SortableJS for thumbnail reordering
- Side-by-side previews (Compare) become two ``<img>`` columns instead of two
  ``tk.Canvas`` widgets
