# Annotate and Merge PDFs

AnM is a Windows-first desktop app for annotating and merging PDFs with a Tkinter GUI. It is now packaged as a small Python project with a testable PDF pipeline, drag-and-drop workflow, safer output handling, and a reproducible local/CI build.

## What it does

- Drag and drop PDF files or folders into the app.
- Keep a visible merge queue with include or exclude controls.
- Reorder files before merging.
- Add a filename-based annotation to every page.
- Adjust annotation template, position, font size, margin, and box opacity.
- Leave annotation text empty to merge without adding text or a box.
- Preview the current overlay on the first selected PDF.
- Write merged output to `output/annotated-merged.pdf` by default.
- Optionally keep intermediate annotated PDFs under `output/annotated/`.
- Open the output folder automatically after a successful run.

## Safety defaults

- App-generated PDFs are excluded from future discovery so reruns do not re-merge old output.
- Temporary working files are created under `output/.tmp/` and removed automatically when intermediate files are not being kept.
- If the merged output already exists, the app asks before overwriting it.

## Requirements

- Python 3.11+
- Windows is the primary supported desktop target
- Tkinter (typically included with Python)

Runtime dependencies:

- `PyMuPDF`
- `tkinterdnd2`

## Install for development

```powershell
python -m pip install -e ".[dev]"
```

## Run the desktop app

Either entry point works:

```powershell
python annotate_and_merge.py
```

or

```powershell
anm
```

## CLI for power users and agents

`anm` with no arguments opens the GUI. Add a command to run the CLI:

```powershell
anm --help
anm help merge
anm --version
```

Merge explicit PDFs in the order provided:

```powershell
anm merge .\a.pdf .\b.pdf --output .\output\merged.pdf
```

Merge all source PDFs in a folder using the same generated-output filtering and natural
sort order as the GUI:

```powershell
anm merge-dir .\pdfs --output .\output\merged.pdf --overwrite
```

Merge without adding an annotation:

```powershell
anm merge .\a.pdf .\b.pdf --template "" --output .\output\merged.pdf
```

Preview the annotation on the first page:

```powershell
anm preview .\a.pdf --output .\preview.png
```

Inspect PDFs or verify the local runtime:

```powershell
anm info .\a.pdf --json
anm doctor
```

Useful merge options:

- `--template`, `--position`, `--font-size`, `--margin`, `--opacity`
- `--overwrite`, `--keep-intermediate`, `--open-folder`
- `--dry-run` to show inputs, output path, and overwrite status without writing files
- `--json` for stable machine-readable output

## Local checks

```powershell
python -m ruff check .
python -m pytest
```

## Build a Windows executable

```powershell
pwsh ./scripts/build_windows.ps1
```

This creates a PyInstaller build under `dist/AnM/`.

## Project layout

- `src/anm/pipeline.py`: PDF discovery, annotation, merge, preview, cleanup.
- `src/anm/gui.py`: Tkinter desktop workbench, drag and drop, progress UI.
- `src/anm/cli.py`: argparse CLI for power users, scripts, and AI agents.
- `src/anm/app_state.py`: queue ordering and generated-file filtering helpers.
- `tests/`: unit, integration, and GUI smoke coverage.

## Screenshots

- Add fresh screenshots or a short GIF here once the upgraded UI is visually finalized.

## Maintenance note

If workflow, build, release, or developer setup behavior changes, update `AGENTS.md`, this README, and the corresponding config or CI files together.
