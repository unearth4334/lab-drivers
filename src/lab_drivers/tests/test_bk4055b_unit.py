#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.visa.BK4055B`."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from lab_drivers.drivers.visa.BK4055B import BK4055B


class TestBK4055BUnit(unittest.TestCase):
    """Validate command formatting, readback parsing, and connection guards."""

    @patch("lab_drivers.drivers.visa.BK4055B.pyvisa.ResourceManager")
    def _make_connected(self, mock_rm_ctor: MagicMock) -> BK4055B:
        mock_rm_ctor.return_value = MagicMock()
        wfg = BK4055B(auto_connect=False)
        wfg.status = "Connected"
        wfg.instrument = MagicMock()
        return wfg

    def test_set_function_sends_bswv_wvtp(self) -> None:
        wfg = self._make_connected()
        wfg.set_function("sine", channel=2)
        wfg.instrument.write.assert_called_once_with("C2:BSWV WVTP,SINE")

    def test_set_function_rejects_unknown_type(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.set_function("triangle", channel=1)

    def test_set_frequency_sends_bswv_frq(self) -> None:
        wfg = self._make_connected()
        wfg.set_frequency(1000.0, channel=1)
        wfg.instrument.write.assert_called_once_with("C1:BSWV FRQ,1000.0")

    def test_set_output_state_on(self) -> None:
        wfg = self._make_connected()
        wfg.set_output_state(True, channel=1)
        wfg.instrument.write.assert_called_once_with("C1:OUTP ON")

    def test_set_load_high_impedance(self) -> None:
        wfg = self._make_connected()
        wfg.set_load("hz", channel=2)
        wfg.instrument.write.assert_called_once_with("C2:OUTP LOAD,HZ")

    def test_set_load_rejects_bad_string(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.set_load("open", channel=1)

    def test_get_output_state_parses_response(self) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:OUTP ON,LOAD,50,PLRT,NOR"
        self.assertTrue(wfg.get_output_state(channel=1))

    def test_get_waveform_config_parses_pairs(self) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,SINE,FRQ,1000HZ,AMP,2V,OFST,0V"
        cfg = wfg.get_waveform_config(channel=1)
        self.assertEqual(cfg["WVTP"], "SINE")
        self.assertEqual(cfg["FRQ"], "1000HZ")

    def test_get_frequency_strips_unit(self) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,SINE,FRQ,1000HZ,AMP,2V,OFST,0V"
        self.assertEqual(wfg.get("frequency", channel=1), 1000.0)

    def test_get_function_returns_type(self) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,SQUARE,FRQ,1000HZ,AMP,2V,OFST,0V"
        self.assertEqual(wfg.get("function", channel=1), "SQUARE")

    def test_get_rejects_unknown_key(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.get("temperature", channel=1)

    def test_methods_require_connection(self) -> None:
        wfg = self._make_connected()
        wfg.status = "Not Connected"
        wfg.instrument = None
        with self.assertRaises(ConnectionError):
            wfg.set_frequency(1000.0, channel=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
