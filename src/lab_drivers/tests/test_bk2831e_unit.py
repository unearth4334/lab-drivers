#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.serial.BK2831E`."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from lab_drivers.drivers.serial.BK2831E import BK2831E


class TestBK2831EUnit(unittest.TestCase):
    """Validate command formatting, readback parsing, and connection guards."""

    def _make_connected(self) -> BK2831E:
        dmm = BK2831E(auto_connect=False)
        dmm.status = "Connected"
        dmm.ser = MagicMock()
        dmm.ser.is_open = True
        return dmm

    @staticmethod
    def _last_written(dmm: BK2831E) -> str:
        return dmm.ser.write.call_args.args[0].decode("ascii").strip()

    def test_set_function_sends_scpi(self) -> None:
        dmm = self._make_connected()
        dmm.set_function("resistance")
        self.assertEqual(self._last_written(dmm), ":FUNCtion RESistance")

    def test_set_function_accepts_alias(self) -> None:
        dmm = self._make_connected()
        dmm.set_function("ohms")
        self.assertEqual(self._last_written(dmm), ":FUNCtion RESistance")

    def test_set_function_rejects_unknown(self) -> None:
        dmm = self._make_connected()
        with self.assertRaises(ValueError):
            dmm.set_function("capacitance")

    def test_set_resistance_range_sends_expected_value(self) -> None:
        dmm = self._make_connected()
        dmm.set_resistance_range(20e3)
        self.assertEqual(self._last_written(dmm), ":RESistance:RANGe:UPPer 20000.0")

    def test_set_resistance_range_rejects_out_of_span(self) -> None:
        dmm = self._make_connected()
        with self.assertRaises(ValueError):
            dmm.set_resistance_range(50e6)

    def test_set_resistance_autorange_on_off(self) -> None:
        dmm = self._make_connected()
        dmm.set_resistance_autorange(True)
        self.assertEqual(self._last_written(dmm), ":RESistance:RANGe:AUTO ON")
        dmm.set_resistance_autorange(False)
        self.assertEqual(self._last_written(dmm), ":RESistance:RANGe:AUTO OFF")

    def test_set_speed_maps_to_nplc(self) -> None:
        dmm = self._make_connected()
        dmm.set_speed("FAST")
        self.assertEqual(self._last_written(dmm), ":RESistance:NPLCycles 0.1")

    def test_set_speed_rejects_unknown(self) -> None:
        dmm = self._make_connected()
        with self.assertRaises(ValueError):
            dmm.set_speed("turbo")

    def test_parse_value_scientific(self) -> None:
        self.assertAlmostEqual(BK2831E._parse_value("+1.23456E+01"), 12.3456)

    def test_parse_value_overload_is_inf(self) -> None:
        self.assertEqual(BK2831E._parse_value("9.9E37"), float("inf"))

    def test_parse_value_rejects_non_numeric(self) -> None:
        with self.assertRaises(ValueError):
            BK2831E._parse_value("OVLD")

    def test_measure_resistance_fetches_reading(self) -> None:
        dmm = self._make_connected()
        dmm._query = MagicMock(return_value="+6.00000E+02")
        self.assertEqual(dmm.measure_resistance(), 600.0)
        dmm._query.assert_called_with(":FETCh?")

    def test_get_dispatches_resistance(self) -> None:
        dmm = self._make_connected()
        dmm._query = MagicMock(return_value="+1.00000E+03")
        self.assertEqual(dmm.get("resistance"), 1000.0)

    def test_get_rejects_unknown_key(self) -> None:
        dmm = self._make_connected()
        with self.assertRaises(ValueError):
            dmm.get("temperature")

    def test_methods_require_connection(self) -> None:
        dmm = self._make_connected()
        dmm.status = "Not Connected"
        dmm.ser = None
        with self.assertRaises(ConnectionError):
            dmm.set_function("resistance")


if __name__ == "__main__":
    unittest.main()
