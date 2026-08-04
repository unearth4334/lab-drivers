"""DM-TP automation nodes backed by lab-drivers instruments.

This package is the *only* part of the repository that knows DM-TP exists. The
driver layer under ``src/lab_drivers`` stays free of orchestration concerns, as
the project scope requires; everything workflow-facing lives here.

It is imported by the DM-TP automation server after this repository is installed
through **Settings -> Custom Nodes**. The server provides ``automation_nodes``,
so this package is not importable standalone -- which is why the driver layer
never imports it.

Adding a node
-------------
Subclass :class:`~automation_nodes.labdrivers.InstrumentNode`, declare the
inputs, and implement ``make_driver`` / ``perform``. The ``@register`` decorator
publishes it; the WebUI picker picks it up with no further changes.
"""

from __future__ import annotations

from lab_drivers_nodes.dmm6500 import DMM6500MeasureNode
from lab_drivers_nodes.ka3010p import KA3010POutputNode
from lab_drivers_nodes.rigoldp711 import RigolDP711OutputNode

__all__ = [
    "DMM6500MeasureNode",
    "KA3010POutputNode",
    "RigolDP711OutputNode",
]
