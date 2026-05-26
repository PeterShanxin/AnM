"""Web-based GUI: pywebview window hosting an HTML/CSS/JS SPA.

The SPA renders the design (Variant B home + Variant A in-tool) verbatim
in a native Edge WebView2 window.  Python exposes a small ``Api`` object
via the pywebview bridge to handle file dialogs, PDF inspection, and
tool execution.
"""

from .app import WebApp, launch

__all__ = ["WebApp", "launch"]
