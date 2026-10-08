"""Make the driver layer and the node layer importable without installation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for relative in ("src", "nodes"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest


@pytest.fixture(autouse=True)
def _reset_connection_pool():
    """Isolate the process-wide instrument connection pool between tests.

    Instrument nodes now reuse one pooled session per (instrument, address), so
    a live entry left by one test would be handed to the next and make-driver
    would never run. Clear it on both sides of every test.
    """
    from automation_nodes.labdrivers import close_all_connections

    close_all_connections()
    yield
    close_all_connections()
