#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file KeysightEL34143A.py
#   @brief Keysight EL34143A electronic load VISA driver.
#   @date 08-Jun-2026

"""Keysight EL34143A DC Electronic Load Driver.

This module provides a VISA-backed driver for the Keysight EL34143A electronic
load with connection helpers, core measurements, transient pulse helpers, and
array waveform capture methods.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyvisa
from colorama import Fore, Style, init

_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "


class KeysightEL34143A:
    """Keysight EL34143A electronic load driver.

    Parameters
    ----------
    auto_connect:
        If True, connect during initialization.
    address:
        Explicit VISA resource string.
    ip_address:
        Instrument IPv4 address used to build a TCPIP VISA resource.
    timeout_ms:
        VISA IO timeout in milliseconds.
    debug:
        If True, print diagnostic connection/capture messages.
    """

    MIN_CURRENT_A = 0.012

    def __init__(
        self,
        auto_connect: bool = True,
        address: Optional[str] = None,
        ip_address: Optional[str] = None,
        timeout_ms: int = 20_000,
        debug: bool = False,
    ):
        init(autoreset=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status: str = "Not Connected"
        self.debug = debug
        self._timeout_ms = timeout_ms
        self._address_hint = address
        self._ip_hint = ip_address

        if auto_connect:
            self.connect(address=self._address_hint, ip_address=self._ip_hint)

    def _open_and_validate(self, resource: str) -> pyvisa.resources.MessageBasedResource:
        inst = self.rm.open_resource(resource)
        inst.timeout = self._timeout_ms
        inst.read_termination = "\n"
        inst.write_termination = "\n"
        idn = inst.query("*IDN?").strip()
        if "EL34143A" not in idn.upper():
            inst.close()
            raise ConnectionError(_ERROR_STYLE + f"Resource '{resource}' is not EL34143A (IDN='{idn}')")
        return inst

    def connect(self, address: Optional[str] = None, ip_address: Optional[str] = None) -> None:
        """Connect to the instrument.

        If neither ``address`` nor ``ip_address`` is provided, scans VISA
        resources and connects to the first device identifying as EL34143A.
        """

        if self.instrument is not None:
            return

        explicit_address = address or self._address_hint
        ip = ip_address or self._ip_hint

        if explicit_address:
            self.instrument = self._open_and_validate(explicit_address)
            self.address = explicit_address
            self.status = "Connected"
            print(_SUCCESS_STYLE + f"Connected to Keysight EL34143A at {self.address}")
            return

        if ip:
            candidates = [
                f"TCPIP0::{ip}::inst0::INSTR",
                f"TCPIP0::{ip}::hislip0::INSTR",
            ]
            for candidate in candidates:
                try:
                    self.instrument = self._open_and_validate(candidate)
                    self.address = candidate
                    self.status = "Connected"
                    print(_SUCCESS_STYLE + f"Connected to Keysight EL34143A at {self.address}")
                    return
                except Exception:
                    continue
            raise ConnectionError(_ERROR_STYLE + f"Could not connect to EL34143A at IP '{ip}'")

        resources = self.rm.list_resources()
        if self.debug:
            print(f"Scanning {len(resources)} VISA resources for EL34143A")

        for resource in resources:
            if "INSTR" not in resource:
                continue
            if not (resource.upper().startswith("USB") or resource.upper().startswith("TCPIP")):
                continue
            try:
                inst = self._open_and_validate(resource)
                self.instrument = inst
                self.address = resource
                self.status = "Connected"
                print(_SUCCESS_STYLE + f"Auto-connected to Keysight EL34143A at {self.address}")
                return
            except Exception as exc:
                if self.debug:
                    print(_WARNING_STYLE + f"Skipping '{resource}': {exc}")

        raise ConnectionError(_ERROR_STYLE + "No Keysight EL34143A found on available VISA resources")

    def disconnect(self) -> None:
        """Disable load input and close VISA session."""

        if self.instrument is None:
            return

        try:
            self.disable_output()
        except Exception:
            pass

        try:
            self.instrument.close()
        finally:
            print(f"\rDisconnected from Keysight EL34143A at {self.address}")
            self.instrument = None
            self.address = None
            self.status = "Not Connected"

    def _require_connection(self) -> pyvisa.resources.MessageBasedResource:
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to Keysight EL34143A")
        return self.instrument

    def get_idn(self) -> str:
        """Return the instrument identification string from ``*IDN?``."""

        return self._require_connection().query("*IDN?").strip()

    def reset(self) -> None:
        """Reset the instrument using ``*RST``."""

        inst = self._require_connection()
        inst.write("*RST")
        time.sleep(1.0)

    def set_current(self, current_a: float) -> None:
        """Set constant-current level in amperes.

        Values below :attr:`MIN_CURRENT_A` are clamped to the minimum.
        """

        clamped = max(float(current_a), self.MIN_CURRENT_A)
        self._require_connection().write(f"CURR {clamped}")

    def get_current_setpoint(self) -> float:
        """Query the configured constant-current setpoint in amperes."""

        return float(self._require_connection().query("CURR?"))

    def measure_current(self) -> float:
        """Measure load current in amperes."""

        return float(self._require_connection().query("MEAS:CURR?"))

    def measure_voltage(self) -> float:
        """Measure load voltage in volts."""

        return float(self._require_connection().query("MEAS:VOLT?"))

    def measure_power(self) -> float:
        """Measure dissipated power in watts."""

        return float(self._require_connection().query("MEAS:POW?"))

    def enable_output(self) -> None:
        """Enable the load input."""

        self._require_connection().write("INP ON")

    def disable_output(self) -> None:
        """Disable the load input."""

        self._require_connection().write("INP OFF")

    def is_output_enabled(self) -> bool:
        """Return True when load input is enabled."""

        response = self._require_connection().query("INP?").strip().upper()
        return response in {"1", "ON"}

    def set_sense_mode(self, remote: bool = True) -> None:
        """Set sense mode.

        Parameters
        ----------
        remote:
            True for 4-wire remote sense (EXT), False for local sense (INT).
        """

        mode = "EXT" if remote else "INT"
        self._require_connection().write(f"VOLT:SENS {mode}")

    def get_sense_mode(self) -> str:
        """Return current sense mode (EXT or INT)."""

        return self._require_connection().query("VOLT:SENS?").strip()

    def sequencer_stop(self) -> None:
        """Exit list sequencing and return to fixed current mode."""

        self._require_connection().write("CURR:MODE FIX")

    def sequencer_start(self) -> None:
        """Re-enter list sequencing mode and start execution."""

        inst = self._require_connection()
        inst.write("CURR:MODE LIST")
        inst.write("INIT")

    def configure_pulse(
        self,
        current_level_a: float,
        pulse_width_s: float,
        trigger_source: str = "IMM",
    ) -> None:
        """Configure and arm a transient current pulse."""

        inst = self._require_connection()
        src = trigger_source.upper()
        inst.write(f"TRAN:TWID {float(pulse_width_s)}")
        inst.write(f"CURR:TLEV {float(current_level_a)}")
        inst.write(f"TRIG:TRAN:SOUR {src}")
        inst.write("INIT:TRAN")

    def trigger_pulse(self) -> None:
        """Send a software bus trigger (``*TRG``)."""

        self._require_connection().write("*TRG")

    def get(self, item: str) -> Any:
        """Generic data-logger friendly getter.

        Supported keys are ``current``, ``voltage``, and ``power``.
        """

        key = item.lower()
        items = {
            "current": self.measure_current,
            "voltage": self.measure_voltage,
            "power": self.measure_power,
        }
        if key not in items:
            raise ValueError(_ERROR_STYLE + f"Unknown item '{item}'. Expected current, voltage, or power")
        return items[key]()

    def configure_digitizer(
        self,
        measure_type: str = "VOLTAGE",
        sample_rate_hz: Optional[float] = None,
        points: Optional[int] = None,
        auto_range: bool = True,
    ) -> None:
        """Configure array capture settings for voltage or current."""

        inst = self._require_connection()
        mode = measure_type.upper()
        if mode not in {"VOLTAGE", "CURRENT"}:
            raise ValueError("measure_type must be 'VOLTAGE' or 'CURRENT'")

        inst.write(f":SENSe:FUNCtion:ON \"{mode}\"")
        if auto_range:
            inst.write(f":SENSe:{mode}:RANGe:AUTO ON")
        if sample_rate_hz is not None:
            if sample_rate_hz <= 0:
                raise ValueError("sample_rate_hz must be > 0")
            inst.write(f":SENSe:{mode}:APERture {1.0 / sample_rate_hz}")
        if points is not None:
            if points <= 0:
                raise ValueError("points must be > 0")
            inst.write(f":SENSe:{mode}:POINts {int(points)}")

    def get_waveform(
        self,
        measure_type: str = "VOLTAGE",
        configure: bool = True,
        sample_rate_hz: Optional[float] = 10_000,
        points: Optional[int] = 1000,
        debug: bool = False,
    ) -> Tuple[List[float], List[float], Dict[str, Any]]:
        """Capture an array waveform.

        Returns
        -------
        tuple
            ``(time_s, values, metadata)`` where metadata includes sample rate,
            point count, and basic statistics.
        """

        inst = self._require_connection()
        mode = measure_type.upper()
        if mode not in {"VOLTAGE", "CURRENT"}:
            raise ValueError("measure_type must be 'VOLTAGE' or 'CURRENT'")

        if configure:
            self.configure_digitizer(
                measure_type=mode,
                sample_rate_hz=sample_rate_hz,
                points=points,
                auto_range=True,
            )
            time.sleep(0.1)

        try:
            actual_points = int(float(inst.query(f":SENSe:{mode}:POINts?")))
        except Exception:
            actual_points = int(points or 1000)

        try:
            aperture_s = float(inst.query(f":SENSe:{mode}:APERture?"))
            actual_sample_rate_hz = 1.0 / aperture_s if aperture_s > 0 else float(sample_rate_hz or 10_000)
        except Exception:
            actual_sample_rate_hz = float(sample_rate_hz or 10_000)

        inst.write("INIT")
        inst.query("*OPC?")

        cmd = "FETC:ARR:VOLT?" if mode == "VOLTAGE" else "FETC:ARR:CURR?"
        response = inst.query(cmd).strip()
        values = [float(v) for v in response.split(",") if v]

        if not values and actual_points > 0:
            # Conservative fallback path when array-fetch command is unavailable.
            values = [float(inst.query("READ?")) for _ in range(actual_points)]

        dt_s = 1.0 / actual_sample_rate_hz if actual_sample_rate_hz > 0 else 0.0
        time_s = [i * dt_s for i in range(len(values))]

        metadata: Dict[str, Any] = {
            "measure_type": mode,
            "npoints": len(values),
            "sample_rate_hz": actual_sample_rate_hz,
            "dt_s": dt_s,
            "duration_s": (len(values) - 1) * dt_s if len(values) > 1 else 0.0,
            "t_start_s": 0.0,
            "t_stop_s": (len(values) - 1) * dt_s if len(values) > 1 else 0.0,
        }
        if values:
            metadata["mean"] = sum(values) / len(values)
            metadata["min"] = min(values)
            metadata["max"] = max(values)
            metadata["peak_to_peak"] = metadata["max"] - metadata["min"]

        if debug:
            print(
                _SUCCESS_STYLE
                + f"Captured {metadata['npoints']} {mode.lower()} points at {metadata['sample_rate_hz']:.3f} Hz"
            )

        return time_s, values, metadata

    def save_waveform(
        self,
        filename: str,
        measure_type: str = "VOLTAGE",
        sample_rate_hz: Optional[float] = 10_000,
        points: Optional[int] = 1000,
        debug: bool = False,
    ) -> bool:
        """Capture waveform and save it as CSV.

        Returns True if capture and write succeed, else False.
        """

        try:
            output_path = Path(filename)
            if not output_path.is_absolute() and output_path.parent == Path("."):
                output_path = Path("output") / "el34143a_waveforms" / output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            t_s, values, meta = self.get_waveform(
                measure_type=measure_type,
                configure=True,
                sample_rate_hz=sample_rate_hz,
                points=points,
                debug=debug,
            )

            unit = "V" if measure_type.upper() == "VOLTAGE" else "A"
            with output_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["# Keysight EL34143A Waveform Capture"])
                writer.writerow([f"# Measure Type: {meta['measure_type']}"])
                writer.writerow([f"# Sample Rate: {meta['sample_rate_hz']} Hz"])
                writer.writerow([f"# Points: {meta['npoints']}"])
                writer.writerow([f"# Duration: {meta['duration_s']} s"])
                writer.writerow([])
                writer.writerow(["Time (s)", f"{meta['measure_type'].capitalize()} ({unit})"])
                for t, value in zip(t_s, values):
                    writer.writerow([f"{t:.9f}", f"{value:.9f}"])

            print(_SUCCESS_STYLE + f"Waveform saved to: {output_path}")
            return True
        except Exception as exc:
            print(_ERROR_STYLE + f"Failed to save waveform: {exc}")
            return False
