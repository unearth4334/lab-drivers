"""Shared base for lab-drivers instrument nodes."""

from __future__ import annotations

import inspect
from typing import Any

from automation_nodes.base import NodeContext, NodeExecutionError
from automation_nodes.labdrivers import InstrumentNode

from lab_drivers_nodes._logging import driver_logs_to


class LabDriverNode(InstrumentNode):
    """An :class:`InstrumentNode` whose driver logs into the run's log.

    Also pins the drivers into non-interactive mode: a node runs while the DM-TP
    program is paused at a checkpoint, so a driver that stopped to ask the
    operator a question would hold the instrument *and* the paused test program
    until the run timed out.

    Overrides connection handling because the wrapped drivers disagree on the
    port-selection kwarg: most VISA drivers accept ``address``, the serial
    ones accept ``com_port``, and a few auto-detect with no port kwarg at all.
    ``InstrumentNode.execute()`` assumes ``connect(address=...)`` universally,
    which breaks (``TypeError``) for any driver that doesn't use that name.
    """

    #: Passed to drivers that accept it; False = never prompt, raise instead.
    interactive = False

    def build_driver(self, driver_cls: type) -> Any:
        """Construct ``driver_cls`` unconnected, passing ``interactive`` only
        if its constructor accepts it -- not every driver still does."""
        kwargs: dict[str, Any] = {"auto_connect": False}
        try:
            params = inspect.signature(driver_cls.__init__).parameters
        except (TypeError, ValueError):
            params = {}
        if "interactive" in params:
            kwargs["interactive"] = self.interactive
        return driver_cls(**kwargs)

    def execute(self, context: NodeContext) -> None:
        try:
            driver = self.make_driver()
        except Exception as ex:  # noqa: BLE001 - normalize driver construction errors
            raise NodeExecutionError(f"Could not create instrument driver: {ex}") from ex

        try:
            self._connect(driver, context)
            self.perform(driver, context)
        finally:
            disconnect = getattr(driver, "disconnect", None)
            if callable(disconnect):
                try:
                    disconnect()
                except Exception:  # noqa: BLE001 - never mask the primary error
                    context.log("instrument disconnect failed", level="warn")

    def _connect(self, driver: Any, context: NodeContext) -> None:
        connect = getattr(driver, "connect", None)
        if not callable(connect):
            return
        address = str(self.config.get("address") or "") or None
        if address is None:
            connect()
            return

        try:
            params = inspect.signature(connect).parameters
        except (TypeError, ValueError):
            params = {}
        if "address" in params:
            connect(address=address)
        elif "com_port" in params:
            connect(com_port=address)
        else:
            context.log(
                f"this driver auto-detects its port; the configured address "
                f"'{address}' was ignored",
                level="warn",
            )
            connect()

    def perform(self, driver: Any, context: NodeContext) -> None:
        """Interact with the instrument. Subclasses implement :meth:`work`."""
        with driver_logs_to(context):
            self.work(driver, context)

    def work(self, driver: Any, context: NodeContext) -> None:
        raise NotImplementedError
