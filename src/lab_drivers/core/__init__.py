"""Core shared primitives for lab_drivers.

Small, transport-agnostic building blocks the drivers share: the logging setup
(:mod:`lab_drivers.core.log`) and serial-port resolution
(:mod:`lab_drivers.core.ports`).
"""

from lab_drivers.core.log import (
    LOGGER_NAME,
    enable_console_logging,
    get_logger,
    remove_console_logging,
)

__all__ = [
    "LOGGER_NAME",
    "can_prompt",
    "enable_console_logging",
    "get_logger",
    "remove_console_logging",
    "resolve_address",
    "select_port",
]


def __getattr__(name: str):
    """Expose the port helpers lazily so ``core`` never needs pyserial."""
    if name in ("can_prompt", "resolve_address", "select_port"):
        from lab_drivers.core import ports

        return getattr(ports, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
