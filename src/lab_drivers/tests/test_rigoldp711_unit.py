#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.serial.RigolDP711`.

These tests use a fake serial transport so they can run without hardware.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from lab_drivers.drivers.serial.RigolDP711 import RigolDP711


class TestRigolDP711Unit(unittest.TestCase):
    """Validate set/query and output-control command behavior."""

    def setUp(self) -> None:
        self.psu = RigolDP711(auto_connect=False)
        self.psu.status = "Connected"
        self.psu.ser = MagicMock()
        self.psu.ser.is_open = True

    def test_set_voltage_sends_expected_scpi(self) -> None:
        self.psu.set_voltage(12.345)
        self.psu.ser.write.assert_called_with(b":VOLT 12.345\r\n")

    def test_set_current_sends_expected_scpi(self) -> None:
        self.psu.set_current(2.5)
        self.psu.ser.write.assert_called_with(b":CURR 2.500\r\n")

    def test_set_output_state_on_and_off(self) -> None:
        # Report the requested state so no re-assert write is issued.
        self.psu.get_output_state = MagicMock(return_value=True)
        self.psu.set_output_state(True)
        self.psu.ser.write.assert_any_call(b":OUTP ON\r\n")

        self.psu.get_output_state = MagicMock(return_value=False)
        self.psu.set_output_state(False)
        self.psu.ser.write.assert_any_call(b":OUTP OFF\r\n")

    def test_set_output_state_reasserts_on_mismatch(self) -> None:
        # Device reports the wrong state, so the absolute command is re-sent.
        self.psu.get_output_state = MagicMock(return_value=False)
        self.psu.set_output_state(True)
        on_writes = [
            call for call in self.psu.ser.write.call_args_list
            if call.args[0] == b":OUTP ON\r\n"
        ]
        self.assertEqual(len(on_writes), 2)

    def test_set_output_state_is_absolute_when_already_enabled(self) -> None:
        # Output already enabled: enabling again still issues the absolute ON.
        self.psu.get_output_state = MagicMock(return_value=True)
        self.psu.set_output_state(True)
        self.psu.ser.write.assert_any_call(b":OUTP ON\r\n")

    def test_get_voltage_setpoint_uses_query(self) -> None:
        self.psu._query = MagicMock(return_value="5.000")
        self.assertEqual(self.psu.get_voltage_setpoint(), 5.0)
        self.psu._query.assert_called_once_with(":VOLT?")

    def test_get_current_setpoint_uses_query(self) -> None:
        self.psu._query = MagicMock(return_value="1.250")
        self.assertEqual(self.psu.get_current_setpoint(), 1.25)
        self.psu._query.assert_called_once_with(":CURR?")

    def test_get_output_state_parses_on_off(self) -> None:
        self.psu._query = MagicMock(return_value="ON")
        self.assertTrue(self.psu.get_output_state())

        self.psu._query = MagicMock(return_value="0")
        self.assertFalse(self.psu.get_output_state())

    def test_get_supports_output_tokens(self) -> None:
        self.psu.get_output_state = MagicMock(return_value=True)
        self.assertEqual(self.psu.get("OUTP"), 1.0)
        self.assertEqual(self.psu.get("OUTPUT"), 1.0)

    def test_out_of_range_checks(self) -> None:
        with self.assertRaises(ValueError):
            self.psu.set_voltage(31)
        with self.assertRaises(ValueError):
            self.psu.set_current(6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
