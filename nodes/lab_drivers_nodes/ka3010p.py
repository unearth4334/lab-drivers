"""Korad KA3010P power-supply output node."""

from __future__ import annotations

from typing import Any

from automation_nodes import NodeInput, register
from automation_nodes.base import NodeContext

from lab_drivers_nodes._base import LabDriverNode


@register
class KA3010POutputNode(LabDriverNode):
    """Set a KA3010P's output and optionally read it back."""

    type_key = "ka3010p-output"
    label = "KA3010P Output"
    summary = "Set voltage/current on a Korad KA3010P and switch its output."
    instrument_key = "ka3010p"
    instrument_label = "Korad KA3010P Power Supply"
    inputs = LabDriverNode.inputs + (
        NodeInput(
            name="voltage", label="Voltage", type="number", unit="V",
            default=0.0, min=0.0, max=30.0, required=True,
            help="Output voltage setpoint.",
        ),
        NodeInput(
            name="current_limit", label="Current limit", type="number", unit="A",
            default=1.0, min=0.0, max=10.0, required=True,
            help="Current limit applied before the output is enabled.",
        ),
        NodeInput(
            name="output_on", label="Output enabled", type="bool", default=True,
            help="Switch the output on after applying the setpoints, or off.",
        ),
        NodeInput(
            name="settle_s", label="Settle time", type="number", unit="s",
            default=0.5, min=0.0, max=300.0,
            help="Wait after switching before reading back.",
        ),
        NodeInput(
            name="verify", label="Read back", type="bool", default=True,
            help="Measure the actual output afterwards and log it.",
        ),
    )

    def make_driver(self) -> Any:
        from lab_drivers.drivers.serial import KA3010P

        return KA3010P(auto_connect=False, interactive=self.interactive)

    def work(self, driver: Any, context: NodeContext) -> None:
        # Current limit first: raising the voltage before the limit is set would
        # briefly expose the load to the previous, possibly higher, limit.
        driver.set_current(float(self.config["current_limit"]))
        driver.set_voltage(float(self.config["voltage"]))

        if self.config["output_on"]:
            driver.turn_on()
            context.log(
                f"output on at {self.config['voltage']:g} V, "
                f"limit {self.config['current_limit']:g} A"
            )
        else:
            driver.turn_off()
            context.log("output off")

        context.sleep(float(self.config["settle_s"]))

        if self.config["verify"]:
            context.check_cancelled()
            context.log(
                f"readback: {driver.measure_voltage():.3f} V, "
                f"{driver.measure_current():.3f} A"
            )
