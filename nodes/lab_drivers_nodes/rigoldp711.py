"""Rigol DP711 power-supply output node."""

from __future__ import annotations

from typing import Any

from automation_nodes import NodeInput, register
from automation_nodes.base import NodeContext

from lab_drivers_nodes._base import LabDriverNode


@register
class RigolDP711OutputNode(LabDriverNode):
    """Set a DP711's output and optionally read it back."""

    type_key = "rigol-dp711-output"
    label = "DP711 Output"
    summary = "Set voltage/current on a Rigol DP711 and switch its output."
    instrument_key = "rigol-dp711"
    instrument_label = "Rigol DP711 Power Supply"
    inputs = LabDriverNode.inputs + (
        NodeInput(
            name="voltage", label="Voltage", type="number", unit="V",
            default=0.0, min=0.0, max=30.0, required=True,
            help="Output voltage setpoint.",
        ),
        NodeInput(
            name="current_limit", label="Current limit", type="number", unit="A",
            default=1.0, min=0.0, max=5.0, required=True,
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
        from lab_drivers.drivers.serial import RigolDP711

        return RigolDP711(auto_connect=False, interactive=self.interactive)

    def work(self, driver: Any, context: NodeContext) -> None:
        driver.set_current(float(self.config["current_limit"]))
        driver.set_voltage(float(self.config["voltage"]))

        if self.config["output_on"]:
            driver.set_output_state(True)
            context.log(
                f"output on at {self.config['voltage']:g} V, "
                f"limit {self.config['current_limit']:g} A"
            )
        else:
            driver.set_output_state(False)
            context.log("output off")

        context.sleep(float(self.config["settle_s"]))

        if self.config["verify"]:
            context.check_cancelled()
            context.log(
                f"readback: {driver.measure_voltage():.3f} V, "
                f"{driver.measure_current():.3f} A"
            )
