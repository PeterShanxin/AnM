from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Protocol


class GuiApp(Protocol):
    def mainloop(self) -> None: ...


def run_gui(gui_factory: Callable[[], GuiApp] | None = None) -> int:
    if gui_factory is None:
        from .gui import PDFAnnotatorApp

        gui_factory = PDFAnnotatorApp
    app = gui_factory()
    app.mainloop()
    return 0


def main(
    argv: list[str] | None = None,
    gui_factory: Callable[[], GuiApp] | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return run_gui(gui_factory)

    from .cli import main as cli_main

    return cli_main(args, gui_runner=lambda: run_gui(gui_factory))
