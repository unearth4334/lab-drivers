#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file BK2831E.py
#   @brief Driver for B&K Precision 2831E / 5491B 4.5-digit bench multimeter.
#   @date 21-Aug-2026
#
#   Licensed to the Apache Software Foundation (ASF) under one
#   or more contributor license agreements.  See the NOTICE file
#   distributed with this work for additional information
#   regarding copyright ownership.  The ASF licenses this file
#   to you under the Apache License, Version 2.0 (the
#   "License"); you may not use this file except in compliance
#   with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing,
#   software distributed under the License is distributed on an
#   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#   KIND, either express or implied.  See the License for the
#   specific language governing permissions and limitations
#   under the License.


"""
B&K Precision 2831E / 5491B Bench Multimeter Driver
===================================================

This module provides a driver for the B&K Precision 2831E (and the closely
related 5491B) 4.5-digit true-RMS bench digital multimeter. The meter exposes a
USB "virtual COM" serial port (the 5491B additionally offers RS-232) that speaks
a small SCPI command set, so this driver is serial-backed and built on
``pyserial``.

Features
--------
- **Serial Interface**: USB virtual COM / RS-232 (default 9600 baud)
- **Auto-Detection**: Verifies the instrument with ``*IDN?`` on connect
- **Measurement Functions**: DC/AC voltage, DC/AC current, 2-wire resistance,
  frequency and period
- **Manual or Auto Ranging**: Select a fixed resistance range by expected value
  or let the meter auto-range
- **Measurement Speed**: FAST / MEDium / SLOW integration (NPLC 0.1 / 1 / 10)
- **Type Hints**: Full type annotations for improved IDE support

Basic Usage
-----------
```python
from lab_drivers.drivers.serial import BK2831E

# Connect to the meter on an explicit COM port
dmm = BK2831E(com_port="COM7")

# Measure a resistor on the 20 kΩ range
dmm.set_function("RESISTANCE")
dmm.set_resistance_range(20e3)     # selects the 20 kΩ range
resistance = dmm.measure_resistance()
print(f"Resistance: {resistance:.3f} Ω")

dmm.disconnect()
```

Context Manager
---------------
```python
with BK2831E(com_port="COM7") as dmm:
    print(dmm.measure_resistance())
```

Resistance Ranges (model 2831E)
-------------------------------
``200 Ω, 2 kΩ, 20 kΩ, 200 kΩ, 2 MΩ, 20 MΩ``. A range is selected by passing the
expected reading to :meth:`set_resistance_range`; for example ``20`` selects the
200 Ω range and ``20e3`` selects the 20 kΩ range. The 5491B uses the 5xx series
(``500 Ω, 5 kΩ, ...``); the same "expected value" selection logic applies.

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following keys are supported by the :meth:`get` method:

- **"voltage"** - DC voltage measurement in volts
- **"current"** - DC current measurement in amperes
- **"resistance"** - 2-wire resistance measurement in ohms
- **"frequency"** - frequency measurement in hertz

Available Methods
-----------------
- `set_function(function)` - Select the active measurement function
- `get_function()` - Query the active measurement function
- `set_resistance_range(value)` - Select a fixed resistance range by expected value
- `set_resistance_autorange(enable)` - Enable/disable resistance auto-ranging
- `set_speed(speed)` - Set integration speed (FAST/MEDIUM/SLOW)
- `measure_voltage()` / `measure_current()` - DC voltage / current
- `measure_resistance(...)` - 2-wire resistance
- `measure_frequency()` - Frequency
- `get(item)` - Generic getter (voltage/current/resistance/frequency)
- `connect(com_port, baud_rate)` / `disconnect()` - Serial connection control

SCPI Command Reference
----------------------
- ``*IDN?`` - Instrument identification
- ``*RST`` - Reset the instrument
- ``:FUNCtion <name>`` - Select function (VOLTage:DC, VOLTage:AC, CURRent:DC,
  CURRent:AC, RESistance, FREQuency, PERiod)
- ``:FUNCtion?`` - Query the active function
- ``:RESistance:RANGe[:UPPer] <n>`` - Set resistance range by expected value
- ``:RESistance:RANGe:AUTO <b>`` - Enable/disable resistance auto-ranging
- ``:RESistance:NPLCycles <n>`` - Set integration rate (0.1 / 1 / 10)
- ``:FETCh?`` - Return the last available reading

See Also
--------
- FLUKE45: Alternative serial bench multimeter driver
- DMM6500: Modern high-speed VISA multimeter driver
"""

from __future__ import annotations

import os
import re
import time
import statistics
from typing import Optional, Tuple

import serial
import serial.tools.list_ports
from colorama import init, Fore, Style


# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.05  # inter-command settle time, in seconds

# Canonical SCPI function tokens accepted by :FUNCtion
_FUNCTIONS = {
    "VOLTAGE:DC": "VOLTage:DC",
    "VOLTAGE:AC": "VOLTage:AC",
    "CURRENT:DC": "CURRent:DC",
    "CURRENT:AC": "CURRent:AC",
    "RESISTANCE": "RESistance",
    "FREQUENCY": "FREQuency",
    "PERIOD": "PERiod",
}

# Aliases for convenience / backwards compatibility
_FUNCTION_ALIASES = {
    "VDC": "VOLTAGE:DC",
    "VAC": "VOLTAGE:AC",
    "IDC": "CURRENT:DC",
    "IAC": "CURRENT:AC",
    "RES": "RESISTANCE",
    "OHM": "RESISTANCE",
    "OHMS": "RESISTANCE",
    "FREQ": "FREQUENCY",
    "PER": "PERIOD",
}

# Integration speed -> NPLC (per the 2831E/5491B programming manual)
_SPEED_NPLC = {"FAST": 0.1, "MEDIUM": 1.0, "MED": 1.0, "SLOW": 10.0}

# Readings at/above this magnitude indicate an over-range (OVL.D) condition
_OVERLOAD_THRESHOLD = 1e30


class BK2831E:
    """B&K Precision 2831E / 5491B bench multimeter driver.

    Serial-backed driver exposing connection helpers, direct measurement
    methods, and a generic :meth:`get` interface for data-logger workflows.
    """

    def __init__(self, auto_connect: bool = True, com_port: Optional[str] = None,
                 baud_rate: int = 9600, debug: bool = False):
        """
        Initialize BK2831E driver.

        Args:
            auto_connect: Automatically connect to device on initialization.
            com_port: Optional explicit COM port (e.g., 'COM7', '/dev/ttyUSB0').
            baud_rate: Serial baud rate (default: 9600, the factory default).
            debug: Enable debug printing (default: False).

        Example:
            >>> dmm = BK2831E(auto_connect=False)
        """
        init(autoreset=True)

        self.ser: Optional[serial.Serial] = None
        self.address: Optional[str] = None
        self.status: str = "Not Connected"
        self.identity: Optional[str] = None
        self.debug: bool = debug
        self._com_port_hint: Optional[str] = com_port
        self._baud_rate: int = baud_rate

        if auto_connect:
            self.connect(com_port=com_port, baud_rate=baud_rate)

    def connect(self, com_port: Optional[str] = None, baud_rate: Optional[int] = None) -> None:
        """
        Establish a serial connection to the 2831E / 5491B multimeter.

        Args:
            com_port: Optional COM port (e.g., 'COM7', '/dev/ttyUSB0'). If None,
                the ``BK2831E_COM_PORT`` environment variable is used, otherwise
                the user is prompted to select from the available ports.
            baud_rate: Serial baud rate. Defaults to the value supplied at
                construction (9600 unless overridden).

        Raises:
            ConnectionError: If the device is not found or the connection fails.

        Example:
            >>> dmm = BK2831E(auto_connect=False)
            >>> dmm.connect(com_port="COM7")
        """
        baud_rate = baud_rate or self._baud_rate

        # 1) Explicit COM port (argument beats ctor hint)
        explicit_port = com_port or self._com_port_hint

        # 2) Environment variable
        if explicit_port is None:
            explicit_port = os.environ.get("BK2831E_COM_PORT")

        # 3) Prompt user to select a COM port
        if explicit_port is None:
            ports = serial.tools.list_ports.comports()
            if not ports:
                raise ConnectionError(_ERROR_STYLE + "No COM ports found")

            print("\nAvailable COM ports:")
            for i, port in enumerate(ports, start=1):
                print(f"  {i}. {port.device} - {port.description}")

            while True:
                try:
                    selection = int(input("Select COM port for BK2831E (1, 2, ...): "))
                    if 1 <= selection <= len(ports):
                        explicit_port = ports[selection - 1].device
                        break
                    print(_ERROR_STYLE + "Invalid selection")
                except ValueError:
                    print(_ERROR_STYLE + "Invalid input. Enter a number.")

        # 4) Open the serial connection and verify identity
        try:
            self.ser = serial.Serial(explicit_port, baud_rate, timeout=5)
            self.address = explicit_port
            self._baud_rate = baud_rate

            self.identity = self._query("*IDN?")
            if not self.identity or "2831E" not in self.identity.upper() and "5491B" not in self.identity.upper():
                # Some firmware revisions report only a version string; accept any
                # non-empty identity but warn if the model can't be confirmed.
                if not self.identity:
                    raise ConnectionError(_ERROR_STYLE + "Device not responding to *IDN?")
                print(_WARNING_STYLE + f"Unconfirmed identity: '{self.identity}'")

            self.status = "Connected"
            os.environ["BK2831E_COM_PORT"] = explicit_port
            print(_SUCCESS_STYLE + f"Connected to {self.identity or 'BK2831E'} at {explicit_port}")

        except serial.SerialException as e:
            raise ConnectionError(_ERROR_STYLE + f"Failed to connect to {explicit_port}: {e}")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Unexpected error connecting to {explicit_port}: {e}")

    def disconnect(self) -> None:
        """
        Close the serial connection to the device.

        Example:
            >>> dmm.disconnect()
        """
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            finally:
                print(f"\rDisconnected from BK2831E at {self.address}")
                self.ser = None

        self.status = "Not Connected"
        self.address = None

    def __enter__(self) -> "BK2831E":
        if self.ser is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # -----------------------------
    # Low-level serial helpers
    # -----------------------------
    def _chk(self) -> None:
        """Verify the meter is connected before performing an operation."""
        if self.status != "Connected" or self.ser is None or not self.ser.is_open:
            raise ConnectionError(_ERROR_STYLE + "Not connected to BK2831E")

    def write(self, command: str) -> None:
        """Send a raw command to the meter (no response expected).

        Args:
            command: SCPI command string, without the trailing terminator.
        """
        if self.ser is None or not self.ser.is_open:
            raise ConnectionError(_ERROR_STYLE + "Not connected to BK2831E")
        if self.debug:
            print(f"WRITE: {command}")
        self.ser.reset_input_buffer()
        self.ser.write((command + "\n").encode("ascii"))
        time.sleep(_DELAY)

    def _query(self, command: str) -> str:
        """Send a query and return the (stripped) response line."""
        if self.ser is None or not self.ser.is_open:
            raise ConnectionError(_ERROR_STYLE + "Not connected to BK2831E")
        if self.debug:
            print(f"QUERY: {command}")
        self.ser.reset_input_buffer()
        self.ser.write((command + "\n").encode("ascii"))
        time.sleep(_DELAY)
        response = self.ser.readline().decode("ascii", errors="ignore").strip()
        if self.debug:
            print(f"  -> '{response}'")
        return response

    @staticmethod
    def _parse_value(raw: str) -> float:
        """Parse a numeric reading from a SCPI response string.

        Handles optional sign, decimal point and scientific notation, and maps
        an over-range magnitude to positive infinity.

        Args:
            raw: The raw response, e.g. ``"+1.23456E+01"``.

        Returns:
            The parsed value as a float; ``float('inf')`` on over-range.

        Raises:
            ValueError: If no numeric value can be parsed.
        """
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", raw)
        if match is None:
            raise ValueError(_ERROR_STYLE + f"Unable to parse numeric value from '{raw}'")
        value = float(match.group(0))
        if abs(value) >= _OVERLOAD_THRESHOLD:
            return float("inf")
        return value

    # -----------------------------
    # Configuration
    # -----------------------------
    def set_function(self, function: str) -> None:
        """Select the active measurement function.

        Args:
            function: Function name (case-insensitive). One of
                ``VOLTAGE:DC``, ``VOLTAGE:AC``, ``CURRENT:DC``, ``CURRENT:AC``,
                ``RESISTANCE``, ``FREQUENCY``, ``PERIOD`` (aliases such as
                ``VDC``, ``RES``/``OHMS`` are also accepted).

        Raises:
            ConnectionError: If not connected to the device.
            ValueError: If an unsupported function is requested.
        """
        self._chk()
        key = function.strip().upper()
        key = _FUNCTION_ALIASES.get(key, key)
        if key not in _FUNCTIONS:
            raise ValueError(_ERROR_STYLE + f"Unsupported function '{function}'. "
                             f"Valid: {', '.join(sorted(_FUNCTIONS))}")
        self.write(f":FUNCtion {_FUNCTIONS[key]}")

    def get_function(self) -> str:
        """Query and return the active measurement function string."""
        self._chk()
        return self._query(":FUNCtion?")

    def set_resistance_range(self, expected_ohms: float) -> None:
        """Select a fixed 2-wire resistance range by expected reading.

        The meter chooses the lowest range that accommodates ``expected_ohms``.
        For the 2831E, ``20`` selects the 200 Ω range and ``20e3`` selects the
        20 kΩ range. Selecting a fixed range disables auto-ranging.

        Args:
            expected_ohms: Expected reading in ohms (0 to 20e6).

        Raises:
            ConnectionError: If not connected to the device.
            ValueError: If the value is outside the supported span.
        """
        self._chk()
        if not 0 <= expected_ohms <= 20e6:
            raise ValueError(_ERROR_STYLE + "Resistance range must be between 0 and 20e6 ohms")
        self.write(f":RESistance:RANGe:UPPer {expected_ohms}")

    def set_resistance_autorange(self, enable: bool = True) -> None:
        """Enable or disable resistance auto-ranging.

        Args:
            enable: ``True`` to auto-range, ``False`` for the present manual range.
        """
        self._chk()
        self.write(f":RESistance:RANGe:AUTO {'ON' if enable else 'OFF'}")

    def set_speed(self, speed: str) -> None:
        """Set the resistance integration speed (measurement rate).

        Args:
            speed: One of ``FAST`` (NPLC 0.1), ``MEDIUM`` (NPLC 1) or ``SLOW``
                (NPLC 10). Slower speeds give lower noise and more resolution.

        Raises:
            ValueError: If an unsupported speed is requested.
        """
        self._chk()
        key = speed.strip().upper()
        if key not in _SPEED_NPLC:
            raise ValueError(_ERROR_STYLE + f"Unsupported speed '{speed}'. "
                             "Valid: FAST, MEDIUM, SLOW")
        self.write(f":RESistance:NPLCycles {_SPEED_NPLC[key]}")

    # -----------------------------
    # Measurements
    # -----------------------------
    def _fetch(self) -> float:
        """Fetch the last available reading via ``:FETCh?``."""
        return self._parse_value(self._query(":FETCh?"))

    def measure_voltage(self, ac: bool = False) -> float:
        """Measure DC (or AC) voltage in volts."""
        self.set_function("VOLTAGE:AC" if ac else "VOLTAGE:DC")
        time.sleep(_DELAY)
        return self._fetch()

    def measure_current(self, ac: bool = False) -> float:
        """Measure DC (or AC) current in amperes."""
        self.set_function("CURRENT:AC" if ac else "CURRENT:DC")
        time.sleep(_DELAY)
        return self._fetch()

    def measure_resistance(self, expected_ohms: Optional[float] = None,
                           autorange: bool = False) -> float:
        """Measure 2-wire resistance in ohms.

        Args:
            expected_ohms: If provided, select the fixed range for this expected
                reading before measuring.
            autorange: If ``True`` (and ``expected_ohms`` is None), enable
                auto-ranging before measuring.

        Returns:
            Resistance in ohms; ``float('inf')`` on over-range.
        """
        self.set_function("RESISTANCE")
        if expected_ohms is not None:
            self.set_resistance_range(expected_ohms)
        elif autorange:
            self.set_resistance_autorange(True)
        time.sleep(_DELAY)
        return self._fetch()

    def measure_frequency(self) -> float:
        """Measure frequency in hertz."""
        self.set_function("FREQUENCY")
        time.sleep(_DELAY)
        return self._fetch()

    def calculate_statistics(self, n: int = 100, delay_s: float = 0.0) -> Tuple[float, float]:
        """Collect ``n`` readings of the active function and return (mean, stdev).

        Args:
            n: Number of readings to collect.
            delay_s: Optional delay between readings, in seconds.

        Returns:
            Tuple of (mean, sample standard deviation). ``stdev`` is 0.0 for a
            single reading.
        """
        self._chk()
        values = []
        for _ in range(max(1, int(n))):
            values.append(self._fetch())
            if delay_s > 0:
                time.sleep(delay_s)
        mean = statistics.fmean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        return mean, stdev

    def get(self, item: str, channel: int = 1) -> float:
        """Retrieve a measurement value by name (data_logger dispatcher).

        Args:
            item: One of ``voltage``, ``current``, ``resistance``, ``frequency``
                (case-insensitive).
            channel: Unused; accepted for interface compatibility.

        Returns:
            The measurement value.

        Raises:
            ValueError: If an invalid item is requested.
        """
        self._chk()
        key = item.strip().lower()
        if key == "voltage":
            return self.measure_voltage()
        if key == "current":
            return self.measure_current()
        if key == "resistance":
            return self.measure_resistance()
        if key == "frequency":
            return self.measure_frequency()
        raise ValueError(_ERROR_STYLE + f"Invalid item '{item}'. "
                         "Valid items: voltage, current, resistance, frequency")

    def reset(self) -> None:
        """Reset the instrument via ``*RST``."""
        self.write("*RST")
