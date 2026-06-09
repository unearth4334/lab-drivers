#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.visa.DMM6500`."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from lab_drivers.drivers.visa.DMM6500 import DMM6500


class TestDMM6500Unit(unittest.TestCase):
    """Validate trigger-model initiation behavior."""

    @patch("lab_drivers.drivers.visa.DMM6500.pyvisa.ResourceManager")
    def test_initiate_trigger_model_sends_init(self, mock_rm_ctor: MagicMock) -> None:
        mock_rm_ctor.return_value = MagicMock()

        dmm = DMM6500(auto_connect=False)
        dmm.status = "Connected"
        dmm.instrument = MagicMock()

        dmm.initiate_trigger_model()

        dmm.instrument.write.assert_called_once_with(":INIT")

    @patch("lab_drivers.drivers.visa.DMM6500.pyvisa.ResourceManager")
    def test_initiate_trigger_model_requires_connection(self, mock_rm_ctor: MagicMock) -> None:
        mock_rm_ctor.return_value = MagicMock()

        dmm = DMM6500(auto_connect=False)
        dmm.status = "Not Connected"
        dmm.instrument = None

        with self.assertRaises(ConnectionError):
            dmm.initiate_trigger_model()


if __name__ == "__main__":
    unittest.main(verbosity=2)
