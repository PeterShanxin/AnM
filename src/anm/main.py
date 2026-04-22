from __future__ import annotations

from .gui import PDFAnnotatorApp


def main() -> int:
    app = PDFAnnotatorApp()
    app.mainloop()
    return 0
