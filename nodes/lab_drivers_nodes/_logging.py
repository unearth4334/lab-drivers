"""Bridge lab-drivers log records into a running node's execution log.

Where drivers report through :mod:`logging`, their records should appear in
the DM-TP run log the operator is watching -- not on the server's stdout.

The handler is scoped to the thread that installed it. Custom nodes run on a
per-checkpoint worker thread, so without that filter two overlapping checkpoints
would each collect the other's instrument output and both run logs would be
wrong in a way that is very hard to read back afterwards.

!!! note "Currently a no-op against the drivers in this repo"
    None of the driver modules under ``src/lab_drivers`` call :mod:`logging`
    today -- they print (via ``colorama``) directly to the console instead.
    This bridge has nothing to intercept until that changes, or until a
    console-output-capture mechanism replaces it. It is kept import-safe
    (rather than removed) so a driver that starts using ``logging`` again
    picks this up for free.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

try:
    from lab_drivers.core.log import LOGGER_NAME
except ImportError:
    # lab_drivers.core.log no longer exists on main (see module docstring).
    LOGGER_NAME = "lab_drivers"

#: logging level -> the level names NodeContext.log understands.
_LEVELS = {
    logging.CRITICAL: "error",
    logging.ERROR: "error",
    logging.WARNING: "warn",
    logging.INFO: "info",
    logging.DEBUG: "debug",
}


class _ContextHandler(logging.Handler):
    """Forward this thread's driver records to a node context."""

    def __init__(self, context, thread_id: int) -> None:
        super().__init__()
        self._context = context
        self._thread_id = thread_id

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self._thread_id:
            return
        try:
            self._context.log(record.getMessage(), _LEVELS.get(record.levelno, "info"))
        except Exception:  # noqa: BLE001 - logging must never break the run
            pass


@contextmanager
def driver_logs_to(context, level: int = logging.INFO):
    """Route lab-drivers output into ``context`` for the duration of the block."""
    logger = logging.getLogger(LOGGER_NAME)
    handler = _ContextHandler(context, threading.get_ident())
    handler.setLevel(level)

    previous = logger.level
    # Only lower the threshold; never raise it above what the app configured.
    if previous == logging.NOTSET or previous > level:
        logger.setLevel(level)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
