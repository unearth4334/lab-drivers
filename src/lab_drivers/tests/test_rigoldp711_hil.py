#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardware-in-the-loop tests for RigolDP711.

Set ``DP711_COM_PORT`` and ``RUN_DP711_HIL=1`` to run these tests.
They are skipped automatically when hardware is unavailable.
"""

from __future__ import annotations

import os
import time
import unittest

from lab_drivers.drivers.serial.RigolDP711 import RigolDP711


_VOLT_TOL = 0.002
_CURR_TOL = 0.002


def _should_run_hil() -> bool:
    return os.environ.get("RUN_DP711_HIL", "0") == "1"


@unittest.skipUnless(_should_run_hil(), "Set RUN_DP711_HIL=1 to run hardware tests")
class TestRigolDP711HIL(unittest.TestCase):
    """Validate voltage/current/output control against a connected DP711."""

    @classmethod
    def setUpClass(cls) -> None:
        port = os.environ.get("DP711_COM_PORT")
        try:
            cls.psu = RigolDP711(auto_connect=False)
            cls.psu.connect(com_port=port)
        except Exception as exc:
            raise unittest.SkipTest(f"DP711 not reachable (port={port!r}): {exc}")

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.psu.turn_off()
        except Exception:
            pass
        try:
            cls.psu.disconnect()
        except Exception:
            pass

    def test_voltage_set_readback(self) -> None:
        self.psu.set_voltage(12.0)
        self.assertAlmostEqual(self.psu.get_voltage_setpoint(), 12.0, delta=_VOLT_TOL)

    def test_current_set_readback(self) -> None:
        self.psu.set_current(2.5)
        self.assertAlmostEqual(self.psu.get_current_setpoint(), 2.5, delta=_CURR_TOL)

    def test_output_enable_disable(self) -> None:
        self.psu.enable_output()
        time.sleep(0.3)
        self.assertTrue(self.psu.get_output_state())

        self.psu.disable_output()
        time.sleep(0.3)
        self.assertFalse(self.psu.get_output_state())


if __name__ == "__main__":
    unittest.main(verbosity=2)
