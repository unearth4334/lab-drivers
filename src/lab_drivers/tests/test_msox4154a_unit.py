#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.visa.KeysightMSOX4154A` setters."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from lab_drivers.drivers.visa.KeysightMSOX4154A import KeysightMSOX4154A


class TestKeysightMSOX4154AControls(unittest.TestCase):
    """Validate control-setter command formatting, validation, and guards."""

    @patch("lab_drivers.drivers.visa.KeysightMSOX4154A.pyvisa.ResourceManager")
    def _make_connected(self, mock_rm_ctor: MagicMock) -> KeysightMSOX4154A:
        mock_rm_ctor.return_value = MagicMock()
        scope = KeysightMSOX4154A(auto_connect=False)
        scope.status = "Connected"
        scope.instrument = MagicMock()
        return scope

    # ---- channel controls ---------------------------------------------------

    def test_set_channel_display_on(self) -> None:
        scope = self._make_connected()
        scope.set_channel_display(1, True)
        scope.instrument.write.assert_called_once_with(":CHANnel1:DISPlay 1")

    def test_set_channel_display_off(self) -> None:
        scope = self._make_connected()
        scope.set_channel_display(3, False)
        scope.instrument.write.assert_called_once_with(":CHANnel3:DISPlay 0")

    def test_set_channel_scale_sends_scale(self) -> None:
        scope = self._make_connected()
        scope.set_channel_scale(1, 0.5)
        scope.instrument.write.assert_called_once_with(":CHANnel1:SCALe 0.5")

    def test_set_channel_offset_sends_offset(self) -> None:
        scope = self._make_connected()
        scope.set_channel_offset(2, 0.0)
        scope.instrument.write.assert_called_once_with(":CHANnel2:OFFSet 0.0")

    def test_set_channel_coupling_dc(self) -> None:
        scope = self._make_connected()
        scope.set_channel_coupling(1, "DC")
        scope.instrument.write.assert_called_once_with(":CHANnel1:COUPling DC")

    def test_set_channel_coupling_is_case_insensitive(self) -> None:
        scope = self._make_connected()
        scope.set_channel_coupling(1, "ac")
        scope.instrument.write.assert_called_once_with(":CHANnel1:COUPling AC")

    def test_set_channel_coupling_rejects_bad_value(self) -> None:
        scope = self._make_connected()
        with self.assertRaises(ValueError):
            scope.set_channel_coupling(1, "GND")

    def test_channel_setters_reject_out_of_range_channel(self) -> None:
        scope = self._make_connected()
        with self.assertRaises(ValueError):
            scope.set_channel_scale(5, 1.0)

    # ---- timebase controls --------------------------------------------------

    def test_set_timebase_scale(self) -> None:
        scope = self._make_connected()
        scope.set_timebase_scale(1e-6)
        scope.instrument.write.assert_called_once_with(":TIMebase:SCALe 1e-06")

    def test_set_timebase_position(self) -> None:
        scope = self._make_connected()
        scope.set_timebase_position(0.0)
        scope.instrument.write.assert_called_once_with(":TIMebase:POSition 0.0")

    def test_set_timebase_reference(self) -> None:
        scope = self._make_connected()
        scope.set_timebase_reference("CENT")
        scope.instrument.write.assert_called_once_with(":TIMebase:REFerence CENT")

    # ---- trigger controls ---------------------------------------------------

    def test_set_trigger_mode(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_mode("EDGE")
        scope.instrument.write.assert_called_once_with(":TRIGger:MODE EDGE")

    def test_set_trigger_sweep(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_sweep("NORM")
        scope.instrument.write.assert_called_once_with(":TRIGger:SWEep NORM")

    def test_set_trigger_source_uses_channel(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_source(2)
        scope.instrument.write.assert_called_once_with(":TRIGger:EDGE:SOURce CHAN2")

    def test_set_trigger_slope(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_slope("POS")
        scope.instrument.write.assert_called_once_with(":TRIGger:EDGE:SLOPe POS")

    def test_set_trigger_slope_rejects_bad_value(self) -> None:
        scope = self._make_connected()
        with self.assertRaises(ValueError):
            scope.set_trigger_slope("UP")

    def test_set_trigger_level(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_level(1.5)
        scope.instrument.write.assert_called_once_with(":TRIGger:EDGE:LEVel 1.5")

    def test_set_trigger_holdoff(self) -> None:
        scope = self._make_connected()
        scope.set_trigger_holdoff(60e-9)
        scope.instrument.write.assert_called_once_with(":TRIGger:HOLDoff 6e-08")

    # ---- acquisition controls -----------------------------------------------

    def test_set_acquisition_type(self) -> None:
        scope = self._make_connected()
        scope.set_acquisition_type("HRES")
        scope.instrument.write.assert_called_once_with(":ACQuire:TYPE HRES")

    def test_set_acquisition_mode(self) -> None:
        scope = self._make_connected()
        scope.set_acquisition_mode("RTIM")
        scope.instrument.write.assert_called_once_with(":ACQuire:MODE RTIM")

    def test_set_averaging_sets_type_then_count(self) -> None:
        scope = self._make_connected()
        scope.set_averaging(16)
        calls = [c.args[0] for c in scope.instrument.write.call_args_list]
        self.assertEqual(calls, [":ACQuire:TYPE AVERage", ":ACQuire:COUNt 16"])

    def test_set_averaging_rejects_out_of_range(self) -> None:
        scope = self._make_connected()
        with self.assertRaises(ValueError):
            scope.set_averaging(1)

    def test_autoscale(self) -> None:
        scope = self._make_connected()
        scope.autoscale()
        scope.instrument.write.assert_called_once_with(":AUToscale")

    def test_single(self) -> None:
        scope = self._make_connected()
        scope.single()
        scope.instrument.write.assert_called_once_with(":SINGle")

    # ---- connection guard ---------------------------------------------------

    def test_setters_require_connection(self) -> None:
        scope = self._make_connected()
        scope.instrument = None
        with self.assertRaises(ConnectionError):
            scope.set_trigger_level(1.0)


if __name__ == "__main__":
    unittest.main()
