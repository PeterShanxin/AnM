from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Protocol


class GuiApp(Protocol):
    def mainloop(self) -> None: ...


def _default_web_factory() -> GuiApp:
    from .gui_web import WebApp

    return WebApp()


def _legacy_tk_factory() -> GuiApp:
    from .gui import PDFAnnotatorApp

    return PDFAnnotatorApp()


def run_gui(gui_factory: Callable[[], GuiApp] | None = None) -> int:
    if gui_factory is None:
        gui_factory = _default_web_factory
    app = gui_factory()
    app.mainloop()
    return 0


def main(
    argv: list[str] | None = None,
    gui_factory: Callable[[], GuiApp] | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    # Optional escape hatch back to the legacy tk GUI: ``anm --tk``.
    if args and args[0] == "--tk":
        return run_gui(gui_factory or _legacy_tk_factory)

    if not args:
        return run_gui(gui_factory)

    from .cli import main as cli_main

    return cli_main(args, gui_runner=lambda: run_gui(gui_factory))
