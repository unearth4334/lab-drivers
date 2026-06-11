#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for :mod:`lab_drivers.drivers.visa.BK4055B`."""

from __future__ import annotations

import tempfile
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

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B._discover_lan_hosts", return_value=[])
    @patch("lab_drivers.drivers.visa.BK4055B.pyvisa.ResourceManager")
    def test_connect_auto_detect_prefers_usb_before_tcpip(
        self,
        mock_rm_ctor: MagicMock,
        _mock_discover: MagicMock,
    ) -> None:
        rm = MagicMock()
        mock_rm_ctor.return_value = rm

        usb = "USB0::0xF4EC::0x1101::SN123::INSTR"
        tcp = "TCPIP0::169.254.209.10::inst0::INSTR"
        rm.list_resources.return_value = (tcp, usb)

        usb_inst = MagicMock()
        usb_inst.query.return_value = "B&K Precision,4055B,SN123,1.00"

        def _open_resource(resource: str) -> MagicMock:
            if resource == usb:
                return usb_inst
            raise AssertionError(f"Unexpected resource attempt: {resource}")

        rm.open_resource.side_effect = _open_resource

        wfg = BK4055B(auto_connect=False)
        wfg.connect()

        self.assertEqual(wfg.address, usb)
        self.assertEqual(rm.open_resource.call_count, 1)
        rm.open_resource.assert_called_once_with(usb)

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B._discover_lan_hosts", return_value=[])
    @patch("lab_drivers.drivers.visa.BK4055B.pyvisa.ResourceManager")
    def test_connect_auto_detect_falls_back_to_tcpip_after_usb(
        self,
        mock_rm_ctor: MagicMock,
        _mock_discover: MagicMock,
    ) -> None:
        rm = MagicMock()
        mock_rm_ctor.return_value = rm

        usb = "USB0::0xF4EC::0x1101::SN123::INSTR"
        tcp = "TCPIP0::169.254.209.10::inst0::INSTR"
        rm.list_resources.return_value = (tcp, usb)

        usb_inst = MagicMock()
        usb_inst.query.return_value = "Some Vendor,Model1234,SN,1.0"

        tcp_inst = MagicMock()
        tcp_inst.query.return_value = "B&K Precision,4055B,SN999,1.00"

        def _open_resource(resource: str) -> MagicMock:
            if resource == usb:
                return usb_inst
            if resource == tcp:
                return tcp_inst
            raise AssertionError(f"Unexpected resource attempt: {resource}")

        rm.open_resource.side_effect = _open_resource

        wfg = BK4055B(auto_connect=False)
        wfg.connect()

        self.assertEqual(wfg.address, tcp)
        self.assertEqual(rm.open_resource.call_count, 2)
        self.assertEqual(rm.open_resource.call_args_list[0].args[0], usb)
        self.assertEqual(rm.open_resource.call_args_list[1].args[0], tcp)

    def test_upload_arbitrary_waveform_sends_wvdt_and_select(self) -> None:
        wfg = self._make_connected()
        wfg.upload_arbitrary_waveform(
            samples=[0.0, 0.5, 1.0, 1.0],
            name="RAMP_HOLD",
            channel=1,
            frequency=1000.0,
            amplitude=5.0,
            offset=2.5,
        )
        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertTrue(any(cmd.startswith("C1:WVDT WVNM,RAMP_HOLD") for cmd in calls))
        self.assertIn("C1:ARWV NAME,RAMP_HOLD", calls)
        self.assertIn("C1:BSWV WVTP,ARB", calls)

    def test_upload_arbitrary_waveform_rejects_out_of_range_sample(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.upload_arbitrary_waveform(samples=[0.0, 0.5, 1.1, 1.0])

    def test_configure_ramp_hold_validates_fraction(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.configure_ramp_hold_0_to_5(ramp_fraction=1.0)

    def test_upload_arbitrary_waveform_file_parses_csv_and_uploads(self) -> None:
        wfg = self._make_connected()
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("0.0, 0.5, 1.0\n")
            f.write("# comment\n")
            f.write("1.0 0.25\n")
            path = f.name

        wfg.upload_arbitrary_waveform_file(file_path=path, name="FILE_WAVE", channel=1)
        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertTrue(any(cmd.startswith("C1:WVDT WVNM,FILE_WAVE") for cmd in calls))

    def test_upload_arbitrary_waveform_file_missing_raises(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.upload_arbitrary_waveform_file(file_path="definitely_missing_waveform.csv")

    def test_upload_arbitrary_waveform_file_accepts_dat(self) -> None:
        wfg = self._make_connected()
        with tempfile.NamedTemporaryFile("w", suffix=".dat", delete=False, encoding="ascii") as f:
            f.write("0.0 0.25 0.5 0.75 1.0\n")
            path = f.name

        wfg.upload_arbitrary_waveform_file(file_path=path, name="FILE_DAT", channel=1)
        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertTrue(any(cmd.startswith("C1:WVDT WVNM,FILE_DAT") for cmd in calls))

    def test_upload_arbitrary_waveform_rejects_too_many_points(self) -> None:
        wfg = self._make_connected()
        samples = [0.5] * 16385
        with self.assertRaises(ValueError):
            wfg.upload_arbitrary_waveform(samples=samples, name="TOO_LONG")

    @patch("lab_drivers.drivers.visa.BK4055B.time.sleep", return_value=None)
    def test_ramp_to_level_sets_dc_and_reaches_target(self, _mock_sleep: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,SINE,FRQ,1000HZ,AMP,2V,OFST,0V"

        wfg.ramp_to_level(target_v=0.2, slew_rate_v_per_s=1.0, channel=1, step_v=0.1)

        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertIn("C1:BSWV WVTP,DC", calls)
        self.assertIn("C1:BSWV OFST,0.2", calls)

    @patch("lab_drivers.drivers.visa.BK4055B.time.sleep", return_value=None)
    def test_ramp_to_level_preserves_offset_when_switching_to_dc(self, _mock_sleep: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,ARB,FRQ,50HZ,AMP,5V,OFST,2.5V"

        wfg.ramp_to_level(target_v=3.0, slew_rate_v_per_s=1.0, channel=1, step_v=0.5)

        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        dc_idx = calls.index("C1:BSWV WVTP,DC")
        # Immediately after mode switch, restore previous offset to avoid 0V dip.
        self.assertIn("C1:BSWV OFST,2.5", calls[dc_idx + 1 :])

    def test_ramp_to_level_rejects_invalid_slew(self) -> None:
        wfg = self._make_connected()
        with self.assertRaises(ValueError):
            wfg.ramp_to_level(target_v=1.0, slew_rate_v_per_s=0.0)

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level_safe")
    def test_ramp_to_wrapper_calls_ramp_to_level_safe(self, mock_safe: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.ramp_to(target_v=2.0, slew_rate_v_per_s=0.5, channel=1)
        mock_safe.assert_called_once()

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level")
    def test_ramp_down_wrapper_calls_ramp_to_level(self, mock_ramp_to_level: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.ramp_down_stay_down(target_v=0.0, slew_rate_v_per_s=0.5)
        mock_ramp_to_level.assert_called_once()

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level_safe")
    def test_ramp_up_safe_wrapper_calls_ramp_to_level_safe(self, mock_safe: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.ramp_up_stay_up_safe(target_v=5.0, slew_rate_v_per_s=0.5)
        mock_safe.assert_called_once()

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level_safe")
    def test_ramp_down_safe_wrapper_calls_ramp_to_level_safe(self, mock_safe: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.ramp_down_stay_down_safe(target_v=0.0, slew_rate_v_per_s=0.5)
        mock_safe.assert_called_once()

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level")
    def test_ramp_to_level_safe_sequences_mode_switch(self, mock_ramp_to_level: MagicMock) -> None:
        wfg = self._make_connected()

        def _query(cmd: str) -> str:
            if cmd == "C1:BSWV?":
                return "C1:BSWV WVTP,ARB,FRQ,1HZ,AMP,5V,OFST,2.5V"
            if cmd == "C1:OUTP?":
                return "C1:OUTP ON,LOAD,HZ,PLRT,NOR"
            return ""

        wfg.instrument.query.side_effect = _query

        wfg.ramp_to_level_safe(target_v=5.0, slew_rate_v_per_s=0.5, channel=1, step_v=0.1, output_on=True)

        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertIn("C1:OUTP OFF", calls)
        self.assertIn("C1:BSWV WVTP,DC", calls)
        self.assertIn("C1:BSWV OFST,2.5", calls)
        self.assertIn("C1:OUTP ON", calls)
        mock_ramp_to_level.assert_called_once()

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level")
    def test_ramp_to_level_safe_can_leave_output_off(self, mock_ramp_to_level: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,DC,OFST,1V"

        wfg.ramp_to_level_safe(target_v=2.0, slew_rate_v_per_s=1.0, channel=1, output_on=False)

        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        # It must finish with output OFF when requested.
        self.assertEqual(calls[-1], "C1:OUTP OFF")

    @patch("lab_drivers.drivers.visa.BK4055B.BK4055B.ramp_to_level")
    def test_ramp_to_level_safe_skips_output_mute_when_already_dc(self, mock_ramp_to_level: MagicMock) -> None:
        wfg = self._make_connected()
        wfg.instrument.query.return_value = "C1:BSWV WVTP,DC,OFST,10V"

        wfg.ramp_to_level_safe(target_v=0.0, slew_rate_v_per_s=0.5, channel=1, start_v=10.0, output_on=True)

        calls = [c.args[0] for c in wfg.instrument.write.call_args_list]
        self.assertNotIn("C1:OUTP OFF", calls)
        self.assertNotIn("C1:BSWV WVTP,DC", calls)
        mock_ramp_to_level.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
