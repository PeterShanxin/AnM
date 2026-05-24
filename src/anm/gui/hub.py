from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - exercised manually when dependency missing
    DND_FILES = None
    TkinterDnD = None

BaseTk = TkinterDnD.Tk if TkinterDnD is not None else tk.Tk

# Attributes that live on the active panel and should be proxied
# through __setattr__ when set on the hub after initialisation.
_PANEL_ATTRS = frozenset({"custom_output_dir"})


class PDFToolkitApp(BaseTk):
    """Main application window that hosts tool panels."""

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
        self._hub_ready = False

        self._build_menu()
        self._build_layout()
        self._show_panel("annotate_merge")
        self.after(100, self._drain_events)

        # Register DnD on root window, delegate to active panel
        if DND_FILES is not None:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._handle_drop)

        self._hub_ready = True

    # ------------------------------------------------------------------
    # Platform helpers
    # ------------------------------------------------------------------

    def _set_dpi_awareness(self) -> None:
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            return

    # ------------------------------------------------------------------
    # DnD delegation
    # ------------------------------------------------------------------

    def _handle_drop(self, event: object) -> None:
        if self._active_panel is not None and hasattr(self._active_panel, "_handle_drop"):
            self._active_panel._handle_drop(event)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Annotate && Merge",
            command=lambda: self._show_panel("annotate_merge"),
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=menubar)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Panel management
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """Destroy the hub, cleaning up panels before tearing down the Tk interpreter.

        StringVars and other Tk variables held by panels must be released while the
        Tcl interpreter is still alive.  Without this, garbage-collecting the panel
        after interpreter teardown corrupts Tcl state and prevents a second Tk
        instance from being created (breaks test isolation).
        """
        self._active_panel = None
        self._panels.clear()
        super().destroy()

    # ------------------------------------------------------------------
    # Event drain loop
    # ------------------------------------------------------------------

    def _drain_events(self) -> None:
        while True:
            try:
                event_type, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break
            if self._active_panel is not None and hasattr(
                self._active_panel, "_handle_event"
            ):
                self._active_panel._handle_event(event_type, payload)
        self.after(100, self._drain_events)

    # ------------------------------------------------------------------
    # Backward-compatibility proxy
    # ------------------------------------------------------------------
    # Tests and CLI code access attributes like app.model,
    # app.add_paths(), app.output_dir_var, etc.  These live on the
    # active panel, so we proxy attribute access transparently.

    def __getattr__(self, name: str) -> object:
        # Only called when normal attribute lookup fails.
        panel = self.__dict__.get("_active_panel")
        if panel is not None:
            try:
                return getattr(panel, name)
            except AttributeError:
                pass
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: object) -> None:
        # Proxy known panel-owned attributes after hub initialisation.
        if name in _PANEL_ATTRS and self.__dict__.get("_hub_ready", False):
            panel = self.__dict__.get("_active_panel")
            if panel is not None:
                setattr(panel, name, value)
                return
        super().__setattr__(name, value)
