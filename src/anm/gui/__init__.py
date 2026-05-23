from .hub import PDFToolkitApp

# Backward compat: cli.py, main.py, and tests import PDFAnnotatorApp.
PDFAnnotatorApp = PDFToolkitApp

__all__ = ["PDFAnnotatorApp", "PDFToolkitApp"]
