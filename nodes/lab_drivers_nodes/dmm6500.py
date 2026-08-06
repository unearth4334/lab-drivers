"""Keithley DMM6500 measurement node."""

from __future__ import annotations

import statistics
from typing import Any

from automation_nodes import NodeInput, register
from automation_nodes.base import NodeContext, NodeExecutionError

from lab_drivers_nodes._base import LabDriverNode

_FUNCTIONS = {
    "DC voltage": ("measure_voltage", "V"),
    "DC current": ("measure_current", "A"),
    "Resistance": ("measure_resistance", "ohm"),
}


@register
class DMM6500MeasureNode(LabDriverNode):
    """Take one or more readings from a DMM6500."""

    type_key = "dmm6500-measure"
    label = "DMM6500 Measure"
    summary = "Read voltage, current or resistance from a Keithley DMM6500."
    instrument_key = "dmm6500"
    instrument_label = "Keithley DMM6500"
    inputs = LabDriverNode.inputs + (
        NodeInput(
            name="function", label="Function", type="select", default="DC voltage",
            options=list(_FUNCTIONS), required=True,
            help="Measurement to take.",
        ),
        NodeInput(
            name="samples", label="Samples", type="integer", default=1, min=1, max=10000,
            help="How many readings to take. More than one is averaged.",
        ),
        NodeInput(
            name="nplc", label="Integration time", type="number", unit="NPLC",
            default=1.0, min=0.0005, max=15.0,
            help="Power-line cycles per reading. Higher is slower and quieter.",
        ),
    )

    def make_driver(self) -> Any:
        from lab_drivers.drivers.visa import DMM6500

        return DMM6500(auto_connect=False)

    def work(self, driver: Any, context: NodeContext) -> None:
        method_name, unit = _FUNCTIONS[self.config["function"]]
        measure = getattr(driver, method_name)

        try:
            driver.set_nplc(float(self.config["nplc"]))
        except Exception as ex:  # noqa: BLE001 - a refused NPLC must not fail the run
            context.log(f"could not set NPLC: {ex}", level="warn")

        readings = []
        for _ in range(int(self.config["samples"])):
            context.check_cancelled()
            readings.append(float(measure()))

        if not readings:
            raise NodeExecutionError("No readings were taken")

        if len(readings) == 1:
            context.log(f"{self.config['function']}: {readings[0]:.6g} {unit}")
        else:
            mean = statistics.fmean(readings)
            stdev = statistics.pstdev(readings)
            context.log(
                f"{self.config['function']}: mean {mean:.6g} {unit}, "
                f"sd {stdev:.3g} {unit} over {len(readings)} readings"
            )
