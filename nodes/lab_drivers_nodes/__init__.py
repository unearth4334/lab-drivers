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
Most instrument capability reaches the WebUI picker automatically: every
driver class below is expanded, by ``automation_nodes.introspect``, into one
node type per public method (using its type hints and docstring). Hand-write a
node (subclass :class:`~automation_nodes.labdrivers.InstrumentNode`, as
``dmm6500.py``/``ka3010p.py``/``rigoldp711.py`` do) only when several driver
calls belong together as one nicer operator action; list the methods it
replaces in that driver's ``exclude`` entry below so the picker doesn't offer
both.
"""

from __future__ import annotations

from automation_nodes import register
from automation_nodes.introspect import generate_nodes

from lab_drivers.drivers.serial import FLUKE45, KA3010P, RigolDP711, U1233A
from lab_drivers.drivers.visa import (
    DL3021,
    DMM6500,
    DP832,
    KS33500B,
    Keysight34460A,
    KeysightMSOX4154A,
    RSA3030,
    RigolDP832,
    RigolDS7034,
    StanfordPS310,
)

from lab_drivers_nodes._base import LabDriverNode
from lab_drivers_nodes.dmm6500 import DMM6500MeasureNode
from lab_drivers_nodes.ka3010p import KA3010POutputNode
from lab_drivers_nodes.rigoldp711 import RigolDP711OutputNode

#: (driver class, instrument key, instrument label, methods a curated node
#: above already covers). Every other public method on the driver becomes its
#: own generated node type.
_INSTRUMENTS: tuple[tuple[type, str, str, tuple[str, ...]], ...] = (
    (FLUKE45, "fluke45", "Fluke 45 Multimeter", ()),
    (KA3010P, "ka3010p", "Korad KA3010P Power Supply",
     ("set_voltage", "set_current", "turn_on", "turn_off", "set_output_state")),
    (RigolDP711, "rigol-dp711", "Rigol DP711 Power Supply",
     ("set_voltage", "set_current", "turn_on", "turn_off", "set_output_state")),
    (U1233A, "u1233a", "Agilent U1233A Multimeter", ()),
    (DL3021, "dl3021", "Rigol DL3021 Electronic Load", ()),
    (DMM6500, "dmm6500", "Keithley DMM6500",
     ("measure_voltage", "measure_current", "measure_resistance")),
    (DP832, "dp832", "Rigol DP832 Power Supply (DP832 driver)", ()),
    (RigolDP832, "rigol-dp832", "Rigol DP832 Power Supply (RigolDP832 driver)", ()),
    (KS33500B, "ks33500b", "Keysight 33500B Waveform Generator", ()),
    (Keysight34460A, "keysight-34460a", "Keysight 34460A Multimeter", ()),
    (KeysightMSOX4154A, "keysight-msox4154a", "Keysight MSOX4154A Oscilloscope", ()),
    (RSA3030, "rsa3030", "Rigol RSA3030 Spectrum Analyzer", ()),
    (RigolDS7034, "rigol-ds7034", "Rigol DS7034 Oscilloscope", ()),
    (StanfordPS310, "ps310", "Stanford PS310 High-Voltage Power Supply", ()),
)

__all__ = [
    "DMM6500MeasureNode",
    "KA3010POutputNode",
    "RigolDP711OutputNode",
]

for _driver_cls, _key, _label, _exclude in _INSTRUMENTS:
    for _node_cls in generate_nodes(
        _driver_cls,
        instrument_key=_key,
        instrument_label=_label,
        exclude=_exclude,
        base=LabDriverNode,
        hook="work",
    ):
        register(_node_cls)
        globals()[_node_cls.__name__] = _node_cls
        __all__.append(_node_cls.__name__)

del _driver_cls, _key, _label, _exclude, _node_cls
