"""VISA-backed instrument drivers.

Each name below resolves to the *driver class*, so both of these work::

    from lab_drivers.drivers.visa import DMM6500          # the class
    from lab_drivers.drivers.visa.DMM6500 import DMM6500  # still supported

Resolution is lazy: importing this package does not import pyvisa. Only
touching a driver pulls in its transport dependency, which is what keeps
``pyvisa`` an optional extra.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "DL3021",
    "DMM6500",
    "DP832",
    "KS33500B",
    "Keysight34460A",
    "KeysightMSOX4154A",
    "RSA3030",
    "RigolDP832",
    "RigolDS7034",
    "StanfordPS310",
]


def __getattr__(name: str) -> Any:
    """Import the submodule named ``name`` and return its like-named class."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f"{__name__}.{name}")
    value = getattr(module, name)
    # Replace the submodule the import machinery bound here with the class, so
    # later lookups skip this function entirely.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
