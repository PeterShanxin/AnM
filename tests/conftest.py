from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _preserve_tcl_env() -> None:
    """Preserve Tcl/Tk environment variables across tests.

    On Windows, destroying a Tk instance can corrupt TCL_LIBRARY / TK_LIBRARY,
    which prevents a second Tk instance from initialising in the same process.
    Saving and restoring those vars after every test restores isolation.
    """
    keys = ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH")
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
