"""pytest configuration and shared fixtures.

Tcl/Tk re-initialisation fix (Windows)
----------------------------------------
After a Tk root window is destroyed, the loaded tcl86.dll/tk86.dll has
partially-cleared internal state.  A second Tk.__init__() in the same
process cannot re-discover the library directories without explicit env-var
hints (TCL_LIBRARY / TK_LIBRARY).

We solve this in two steps:
1. At module-load time, inspect sys.base_exec_prefix to locate the Tcl/Tk
   library directories and pre-set the env vars so both the first AND any
   subsequent Tk instance can initialise successfully.
2. An autouse fixture saves the vars before each test and restores them
   afterward, preventing test-to-test leakage from other env changes.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest


def _set_tcl_env() -> None:
    """Set TCL_LIBRARY / TK_LIBRARY from the running Python if not already set."""
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return  # already configured

    base = pathlib.Path(sys.base_exec_prefix)

    # uv-managed CPython on Windows: tcl lives under <base>/tcl/
    candidates = [
        (base / "tcl" / "tcl8.6",  base / "tcl" / "tk8.6"),
        (base / "lib" / "tcl8.6",  base / "lib" / "tk8.6"),
        # conda layout
        (base / "Library" / "lib" / "tcl8.6", base / "Library" / "lib" / "tk8.6"),
    ]

    for tcl_dir, tk_dir in candidates:
        if tcl_dir.exists() and tk_dir.exists():
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
            os.environ.setdefault("TK_LIBRARY",  str(tk_dir))
            return


# Run at import time so both first and subsequent Tk instances get the paths.
_set_tcl_env()


# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _preserve_tcl_env() -> None:
    """Preserve Tcl/Tk environment variables across tests.

    Even with the module-level pre-set above, a test could unset or
    mangle these vars.  This fixture ensures every test starts and ends
    with a consistent environment.
    """
    keys = ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH")
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
