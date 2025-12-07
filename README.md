# Annotate and Merge PDFs

A lightweight Python app to annotate and merge PDF files via a Tkinter GUI.

## Features

- Annotates each page with its filename.
- Natural sorting of PDF files to ensure correct order.
- Semi-transparent rectangle behind the filename for readability.
- Option to save intermediate annotated files or discard them.
- Merges annotated files into a single PDF.
- High DPI awareness for clear display on high-resolution screens.
- Cleans up intermediate files when not required.
- Simple interface with buttons to select a directory, begin merge, and toggle options.

## Requirements

- Python 3.x
- PyMuPDF (fitz)
- Tkinter (usually included with Python on Windows)
- Windows (supports `explorer` command to open output folder)

## Usage

1. Clone this repository or download the script.
2. Install dependencies:
    pip install PyMuPDF
3. Run the script:
    python annotate_and_merge.py
4. Select the directory containing your PDF files.
5. Choose whether to save intermediate annotated files and whether to open the folder after merging.
6. Click **Begin Merge** to annotate and merge PDFs. The output file will be saved as `annotatedMerged.pdf` in the selected directory.

## Roadmap

- [ ] Add drag-and-drop file selection.
- [ ] Support for non-Windows platforms.
- [ ] Customize annotation position and style.
- [ ] More configuration via settings panel.
