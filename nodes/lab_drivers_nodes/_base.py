"""Shared base for lab-drivers instrument nodes."""

from __future__ import annotations

from typing import Any

from automation_nodes.base import NodeContext
from automation_nodes.labdrivers import InstrumentNode

from lab_drivers_nodes._logging import driver_logs_to


class LabDriverNode(InstrumentNode):
    """An :class:`InstrumentNode` whose driver logs into the run's log.

    Also pins the drivers into non-interactive mode: a node runs while the DM-TP
    program is paused at a checkpoint, so a driver that stopped to ask the
    operator a question would hold the instrument *and* the paused test program
    until the run timed out.
    """

    #: Passed to drivers that accept it; False = never prompt, raise instead.
    interactive = False

    def perform(self, driver: Any, context: NodeContext) -> None:
        """Interact with the instrument. Subclasses implement :meth:`work`."""
        with driver_logs_to(context):
            self.work(driver, context)

    def work(self, driver: Any, context: NodeContext) -> None:
        raise NotImplementedError
