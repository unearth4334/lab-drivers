"""Logging for the driver layer.

Drivers report progress through the standard :mod:`logging` module rather than
``print``, so an embedding application can route that output wherever it needs
it -- a run log, a file, a GUI pane -- without the drivers knowing anything
about the consumer.

Following the usual library convention, this package attaches only a
:class:`logging.NullHandler`: nothing is emitted until the application asks for
it. Scripts that want the old console behaviour call
:func:`enable_console_logging` once at start-up::

    import lab_drivers

    lab_drivers.enable_console_logging()

Library code should never configure the root logger, which is why this is an
explicit call rather than something that happens on import.
"""

from __future__ import annotations

import logging
import sys

#: Root logger name for every driver in this package.
LOGGER_NAME = "lab_drivers"

_root = logging.getLogger(LOGGER_NAME)
_root.addHandler(logging.NullHandler())


def get_logger(name: str) -> logging.Logger:
    """Return the logger a driver module should use.

    Pass ``__name__``; the result sits under :data:`LOGGER_NAME`, so an
    application can configure the whole driver layer with one handler, or a
    single instrument by its module name.
    """
    if name.startswith(f"{LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


class _ColorFormatter(logging.Formatter):
    """Format records with the severity colours the drivers used to print."""

    def __init__(self) -> None:
        super().__init__("%(message)s")
        try:
            from colorama import Fore, Style, init

            init(autoreset=True)
            self._styles = {
                logging.ERROR: Fore.RED + Style.BRIGHT,
                logging.CRITICAL: Fore.RED + Style.BRIGHT,
                logging.WARNING: Fore.YELLOW + Style.BRIGHT,
            }
            self._reset = Style.RESET_ALL
        except ImportError:  # colorama is optional; plain text still reads fine
            self._styles = {}
            self._reset = ""

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        style = self._styles.get(record.levelno)
        return f"{style}{text}{self._reset}" if style else text


def enable_console_logging(level: int = logging.INFO, *, stream=None) -> logging.Handler:
    """Send driver output to the console, as the drivers used to print it.

    Calling this more than once replaces the previous console handler rather
    than stacking a second one (which would double every line).
    """
    remove_console_logging()
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(_ColorFormatter())
    handler.set_name("lab_drivers.console")
    _root.addHandler(handler)
    _root.setLevel(level)
    return handler


def remove_console_logging() -> None:
    """Detach the handler installed by :func:`enable_console_logging`."""
    for handler in list(_root.handlers):
        if handler.get_name() == "lab_drivers.console":
            _root.removeHandler(handler)
            handler.close()
