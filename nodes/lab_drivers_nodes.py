"""DM-TP automation nodes for lab-drivers instruments.

This module is the entry point named in ``dmtp_nodes.toml``: DM-TP imports it
during node discovery so the ``@register`` decorators below publish each node
type to the WebUI picker. It carries no orchestration of its own -- every node
derives from :class:`automation_nodes.labdrivers.InstrumentNode`, which manages
the driver ``connect()`` / ``disconnect()`` lifecycle around a single
:meth:`perform` call.

Only instruments whose lab-drivers ``connect(address=...)`` signature matches the
``InstrumentNode`` contract are wrapped here; the ``Address`` input (inherited
from ``InstrumentNode``) accepts a VISA resource string, and an empty value lets
the driver auto-detect on the bus.

Drivers are imported by explicit module path rather than ``from
lab_drivers.drivers.visa import ...`` because the transport ``__init__`` modules
declare ``__all__`` without re-exporting the classes.
"""

from __future__ import annotations

from automation_nodes import NodeInput, register
from automation_nodes.labdrivers import InstrumentNode
from lab_drivers.drivers.visa.DMM6500 import DMM6500
from lab_drivers.drivers.visa.DL3021 import DL3021
from lab_drivers.drivers.visa.StanfordPS310 import StanfordPS310


@register
class DMM6500MeasureNode(InstrumentNode):
    """Read a single quantity from a Keithley/Tektronix DMM6500 multimeter."""

    type_key = "dmm6500-measure"
    label = "DMM6500 Measure"
    summary = "Read voltage, current or resistance from a Keithley/Tektronix DMM6500."
    inputs = InstrumentNode.inputs + (
        NodeInput(
            name="quantity", label="Quantity", type="select",
            options=["voltage", "current", "resistance"], default="voltage",
            required=True, help="Which quantity to measure.",
        ),
        NodeInput(
            name="four_wire", label="4-wire resistance", type="bool", default=False,
            help="Use 4-wire sensing (resistance measurements only).",
        ),
        NodeInput(
            name="samples", label="Samples", type="integer", default=1, min=1, max=10000,
            help="Number of readings to take.",
        ),
    )

    def make_driver(self):
        return DMM6500(auto_connect=False)

    def perform(self, driver, context):
        quantity = self.config["quantity"]
        samples = int(self.config["samples"])
        four_wire = bool(self.config["four_wire"])
        for i in range(samples):
            context.check_cancelled()
            if quantity == "voltage":
                value, unit = driver.measure_voltage(), "V"
            elif quantity == "current":
                value, unit = driver.measure_current(), "A"
            else:
                value, unit = driver.measure_resistance(four_wire=four_wire), "ohm"
            context.log(f"{quantity} [{i + 1}/{samples}]: {value:.6g} {unit}")


@register
class DL3021MeasureNode(InstrumentNode):
    """Read a single quantity from a Rigol DL3021 DC electronic load."""

    type_key = "dl3021-measure"
    label = "DL3021 Load Measure"
    summary = "Read voltage, current or power from a Rigol DL3021 electronic load."
    inputs = InstrumentNode.inputs + (
        NodeInput(
            name="quantity", label="Quantity", type="select",
            options=["voltage", "current", "power"], default="voltage",
            required=True, help="Which quantity to measure.",
        ),
    )

    def make_driver(self):
        return DL3021(auto_connect=False)

    def perform(self, driver, context):
        quantity = self.config["quantity"]
        reader, unit = {
            "voltage": (driver.measure_voltage, "V"),
            "current": (driver.measure_current, "A"),
            "power": (driver.measure_power, "W"),
        }[quantity]
        context.log(f"{quantity}: {reader():.6g} {unit}")


@register
class StanfordPS310MeasureNode(InstrumentNode):
    """Read the output voltage or current of a Stanford Research PS310 HV supply."""

    type_key = "stanfordps310-measure"
    label = "PS310 Measure"
    summary = "Read the output voltage or current of a Stanford Research PS310 HV supply."
    inputs = InstrumentNode.inputs + (
        NodeInput(
            name="quantity", label="Quantity", type="select",
            options=["voltage", "current"], default="voltage",
            required=True, help="Which quantity to measure.",
        ),
    )

    def make_driver(self):
        return StanfordPS310(auto_connect=False)

    def perform(self, driver, context):
        if self.config["quantity"] == "voltage":
            context.log(f"voltage: {driver.measure_voltage():.6g} V")
        else:
            context.log(f"current: {driver.measure_current():.6g} A")


@register
class StanfordPS310SetVoltageNode(InstrumentNode):
    """Set the output voltage of a Stanford Research PS310 HV supply."""

    type_key = "stanfordps310-set-voltage"
    label = "PS310 Set Voltage"
    summary = "Set a Stanford Research PS310 HV supply's output voltage and switch its output on or off."
    inputs = InstrumentNode.inputs + (
        NodeInput(
            name="voltage_v", label="Voltage", type="number", unit="V", default=0.0,
            required=True, help="Target output voltage.",
        ),
        NodeInput(
            name="output_on", label="Output on", type="bool", default=True,
            help="Enable (True) or disable (False) the HV output after setting the voltage.",
        ),
    )

    def make_driver(self):
        return StanfordPS310(auto_connect=False)

    def perform(self, driver, context):
        voltage = float(self.config["voltage_v"])
        output_on = bool(self.config["output_on"])
        driver.set_voltage(voltage)
        driver.set_output_state(output_on)
        context.log(f"PS310 set to {voltage:g} V, output {'on' if output_on else 'off'}")
