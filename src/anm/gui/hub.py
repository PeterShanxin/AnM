"""PDFToolkitApp — main application window.

Navigation strategy
-------------------
* **Home** (Variant B): ``HubHomePanel`` — launcher grid of all tools by category.
* **In-tool** (Variant A): ``ToolChromeFrame`` — persistent icon rail + grouped
  sidebar wrapping the active tool panel.

Backward-compatibility proxy
-----------------------------
Tests and CLI callers access attributes/methods on the app directly (e.g.
``app.model``, ``app.add_paths()``, ``app.custom_output_dir``).  These live
on the active tool panel, so ``__getattr__`` / ``__setattr__`` proxy them
transparently.

The ``AnnotateMergePanel`` is always instantiated eagerly (it is the default
"active" panel even when the home screen is visible) so that proxy access
works from the very first line after ``PDFToolkitApp()``.
"""

from __future__ import annotations

import queue
import threading
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

# Maps catalog tool-id → internal panel key used by _create_tool_panel.
_TOOL_PANEL_KEYS: dict[str, str] = {
    "merge":   "annotate_merge",
    "split":   "split",
    "reorder": "reorder",
    "delete":  "delete_pages",
    "rotate":  "rotate",
    "extract": "extract",
}


class PDFToolkitApp(BaseTk):
    """Main application window that hosts tool panels."""

    def __init__(self) -> None:
        # DPI awareness MUST be set before super().__init__() — Tk caches
        # the screen dimensions at construction time, so calling it after
        # leaves winfo_screen{width,height}() returning pre-scaling values.
        self._set_dpi_awareness()
        super().__init__()
        self.title("AnM — PDF Toolkit")
        self._apply_default_geometry()

        # Apply design-system ttk styling (anm-btn, anm-btn-primary).
        from .styles import configure_ttk
        configure_ttk(self)

        self.status_var = tk.StringVar(value="Select a tool from the menu.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        # Shared lock prevents two Phase 1 tool panels from running concurrently.
        self.run_lock = threading.Lock()

        # Panel cache: panel_key → ttk.Frame
        self._panels: dict[str, ttk.Frame] = {}
        # The active *tool* panel (inside ToolChromeFrame); used by the proxy.
        self._active_panel: ttk.Frame | None = None
        # Which top-level frame is currently visible in _panel_container.
        self._visible_frame: ttk.Frame | None = None
        self._hub_ready = False

        self._build_layout()
        self._build_top_level_frames()

        # Eagerly create AnnotateMergePanel so proxy works from __init__ onward.
        _am = self._get_tool_panel("annotate_merge")
        self._active_panel = _am

        # Start on the home screen.
        self._show_home()

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

    def _physical_screen_size(self) -> tuple[int, int]:
        """Return primary-monitor pixel dimensions, DPI-correct on Windows.

        Falls back to winfo_screen* on non-Windows or if ctypes fails.
        """
        try:
            from ctypes import windll
            user32 = windll.user32
            # SM_CXSCREEN=0, SM_CYSCREEN=1 — primary monitor in physical
            # pixels once SetProcessDpiAwareness has been called.
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            return self.winfo_screenwidth(), self.winfo_screenheight()

    def _apply_default_geometry(self) -> None:
        """Size and centre the window as a fraction of the screen.

        Breakpoints (screen width):
          < 1366  → 95 % of screen  (compact laptop)
          < 1920  → 92 % of screen  (typical 1080p / 1440p)
          ≥ 1920  → 85 % of screen, capped at 2200×1400 (large / 4K)
        """
        sw, sh = self._physical_screen_size()

        if sw < 1366:
            frac = 0.95
        elif sw < 1920:
            frac = 0.92
        else:
            frac = 0.85

        w = max(1100, min(int(sw * frac), 2200))
        h = max(720,  min(int(sh * frac), 1400))

        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        min_w = max(960, min(int(sw * 0.55), 1280))
        min_h = max(640, min(int(sh * 0.55), 860))
        self.minsize(min_w, min_h)

    # ------------------------------------------------------------------
    # DnD delegation
    # ------------------------------------------------------------------

    def _handle_drop(self, event: object) -> None:
        if self._active_panel is not None and hasattr(self._active_panel, "_handle_drop"):
            self._active_panel._handle_drop(event)

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

    def _build_top_level_frames(self) -> None:
        from .hub_home import HubHomePanel
        from .tool_chrome import ToolChromeFrame

        self._hub_home = HubHomePanel(
            self._panel_container,
            on_tool_select=self._on_home_tool_select,
        )

        self._tool_chrome = ToolChromeFrame(
            self._panel_container,
            on_home=self._show_home,
            on_tool_navigate=self._on_home_tool_select,
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_home(self) -> None:
        """Display the hub home (Variant B launcher)."""
        if self._visible_frame is not None:
            self._visible_frame.grid_forget()
        self._hub_home.grid(row=0, column=0, sticky="nsew")
        self._visible_frame = self._hub_home
        self.title("AnM — PDF Toolkit")
        # Keep _active_panel pointing to last tool for proxy compat.

    def _on_home_tool_select(self, tool_id: str) -> None:
        """Called when a tool card or sidebar item is clicked."""
        panel_key = _TOOL_PANEL_KEYS.get(tool_id)
        if panel_key is None:
            # Tool not yet implemented — show placeholder
            panel_key = "__placeholder__"
            panel = self._get_placeholder_panel(tool_id)
        else:
            panel = self._get_tool_panel(panel_key)

        from .catalog import get_tool
        tool_def = get_tool(tool_id)
        cat_id = tool_def.cat if tool_def else "organize"

        if self._visible_frame is not None:
            self._visible_frame.grid_forget()

        self._tool_chrome.show_tool_panel(panel, tool_id=tool_id, cat_id=cat_id)
        self._tool_chrome.grid(row=0, column=0, sticky="nsew")
        self._visible_frame = self._tool_chrome
        self._active_panel = panel

        tool_label = tool_def.label if tool_def else tool_id
        self.title(f"AnM — {tool_label}")

    # ------------------------------------------------------------------
    # Panel management
    # ------------------------------------------------------------------

    def _get_tool_panel(self, key: str) -> ttk.Frame:
        if key not in self._panels:
            self._panels[key] = self._create_tool_panel(key)
        return self._panels[key]

    def _create_tool_panel(self, key: str) -> ttk.Frame:
        parent = self._tool_chrome.content_area
        common = {
            "status_var":   self.status_var,
            "progress_var": self.progress_var,
            "event_queue":  self.event_queue,
        }
        if key == "annotate_merge":
            from .annotate_merge import AnnotateMergePanel
            return AnnotateMergePanel(parent, **common, run_lock=self.run_lock)
        # All panels share run_lock to prevent concurrent PyMuPDF operations.
        phase1 = {**common, "run_lock": self.run_lock}
        if key == "split":
            from .panels.split import SplitPanel
            return SplitPanel(parent, **phase1)
        if key == "rotate":
            from .panels.rotate import RotatePanel
            return RotatePanel(parent, **phase1)
        if key == "reorder":
            from .panels.reorder import ReorderPanel
            return ReorderPanel(parent, **phase1)
        if key == "delete_pages":
            from .panels.delete_pages import DeletePagesPanel
            return DeletePagesPanel(parent, **phase1)
        if key == "extract":
            from .panels.extract import ExtractPanel
            return ExtractPanel(parent, **phase1)
        raise ValueError(f"Unknown panel key: {key!r}")

    def _get_placeholder_panel(self, tool_id: str) -> ttk.Frame:
        """Lazy placeholder for tools not yet implemented."""
        key = f"__ph_{tool_id}__"
        if key not in self._panels:
            self._panels[key] = self._make_placeholder(tool_id)
        return self._panels[key]

    def _make_placeholder(self, tool_id: str) -> ttk.Frame:
        from .catalog import get_tool
        from .styles import BG, TEXT, TEXT_MUTED, body, heading

        tool = get_tool(tool_id)
        label = tool.label if tool else tool_id.replace("_", " ").title()
        desc = tool.desc if tool else "This tool is coming soon."

        frame = ttk.Frame(self._tool_chrome.content_area)
        inner = tk.Frame(frame, bg=BG)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=label, bg=BG, fg=TEXT, font=heading(20)).pack(
            anchor="center", pady=(120, 8)
        )
        tk.Label(inner, text=desc, bg=BG, fg=TEXT_MUTED, font=body(13)).pack(anchor="center")
        tk.Label(
            inner,
            text="Coming soon",
            bg=BG,
            fg="#8a8a8a",
            font=body(11),
        ).pack(anchor="center", pady=(4, 0))
        return frame

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
        import gc

        self._active_panel = None
        self._panels.clear()
        # Drop references to top-level frames so their StringVars can be
        # collected (and their __del__ can unset the Tcl vars) before the
        # interpreter is torn down in super().destroy().
        self._hub_home = None  # type: ignore[assignment]
        self._tool_chrome = None  # type: ignore[assignment]
        gc.collect()  # run reference-cycle collector to trigger __del__ while interp alive
        super().destroy()

    # ------------------------------------------------------------------
    # Event drain loop
    # ------------------------------------------------------------------

    def _drain_events(self) -> None:
        while True:
            try:
                item = self.event_queue.get_nowait()
            except queue.Empty:
                break
            # Phase 1 panels include the panel ref as a 3rd element so events
            # are routed to the launching panel even after navigation.
            # Legacy panels (e.g. AnnotateMergePanel) post 2-tuples; fall back
            # to _active_panel for those.
            if len(item) == 3:
                event_type, payload, panel = item
            else:
                event_type, payload = item  # type: ignore[misc]
                panel = self._active_panel
            if panel is not None and hasattr(panel, "_handle_event"):
                panel._handle_event(event_type, payload)
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
