"""Serial-backed instrument drivers.

Each name below resolves to the *driver class*, so both of these work::

    from lab_drivers.drivers.serial import KA3010P          # the class
    from lab_drivers.drivers.serial.KA3010P import KA3010P  # still supported

Resolution is lazy: importing this package does not import pyserial.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["FLUKE45", "KA3010P", "RigolDP711", "U1233A"]


def __getattr__(name: str) -> Any:
    """Import the submodule named ``name`` and return its like-named class."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f"{__name__}.{name}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
