#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file BK4055B.py
#   @brief Driver for B&K Precision 4055B Function/Arbitrary Waveform Generator (VISA/SCPI).
#   @date 11-Jun-2026
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
B&K Precision 4055B Function/Arbitrary Waveform Generator Driver
================================================================

This module provides a driver for the B&K Precision 4055B dual-channel
function/arbitrary waveform generator with VISA connectivity. The 4055B (and the
rest of the 4050B series) uses the Siglent/SDG-style SCPI command set, where the
basic waveform is configured through the ``Cx:BSWV`` command and the output is
controlled through ``Cx:OUTP``.

Features
--------
- **Dual Channels**: Two independent output channels (``CH1`` / ``CH2``)
- **Multiple Waveforms**: Sine, square, ramp, pulse, noise, DC, arbitrary
- **Wide Frequency Range**: Up to 30 MHz (sine)
- **Output Control**: Per-channel enable/disable and output load selection
- **Auto-Detection**: Automatically finds the 4055B on the VISA bus via ``*IDN?``
- **Zero-Config LAN**: Optional mDNS/LXI discovery finds the instrument on a
  DHCP network without per-user static IP setup (requires the ``lan`` extra)
- **Type Hints**: Full type annotations for improved IDE support

Basic Usage
-----------
```python
from lab_drivers.drivers.visa import BK4055B

# Auto-connect to the waveform generator
wfg = BK4055B()

# Configure channel 1 for a 1 kHz, 2 Vpp sine wave
wfg.set_function("SINE", channel=1)
wfg.set_frequency(1000.0, channel=1)   # 1 kHz
wfg.set_amplitude(2.0, channel=1)      # 2 Vpp
wfg.set_offset(0.0, channel=1)         # 0 V offset

# Enable the output
wfg.set_output_state(True, channel=1)

# Clean up
wfg.set_output_state(False, channel=1)
wfg.disconnect()
```

Explicit Addressing
-------------------
```python
# Connect to a specific USB VISA address
wfg = BK4055B(auto_connect=False)
wfg.connect(address="USB0::0xF4EC::0x1101::0123456789::INSTR")

# Connect to a specific TCPIP (LAN) VISA address
wfg = BK4055B(auto_connect=False)
wfg.connect(address="TCPIP0::192.168.1.100::inst0::INSTR")
```

Zero-Config LAN Discovery
-------------------------
```python
# With the 'lan' extra installed (pip install "lab-drivers[lan]") the driver
# can find a DHCP-addressed 4055B on the local network automatically, without
# any static IP setup. Just auto-connect:
wfg = BK4055B()           # browses mDNS/LXI, verifies *IDN?, connects

# Discovery is also available directly:
wfg = BK4055B(auto_connect=False)
candidates = wfg._discover_lan_hosts()   # list of IPv4 addresses
```

Note: mDNS discovery only reaches instruments on the same broadcast domain and
requires the optional ``zeroconf`` dependency. When it is not installed, LAN
auto-detection is skipped and an explicit ``address=`` still works.

Waveform Types
--------------
```python
# Sine wave
wfg.set_function("SINE", channel=1)
wfg.set_frequency(10000.0, channel=1)  # 10 kHz

# Square wave with 25% duty cycle
wfg.set_function("SQUARE", channel=1)
wfg.set_frequency(1000.0, channel=1)
wfg.set_duty_cycle(25.0, channel=1)

# Ramp wave with 80% symmetry
wfg.set_function("RAMP", channel=1)
wfg.set_symmetry(80.0, channel=1)

# Pulse with 100 ns width
wfg.set_function("PULSE", channel=1)
wfg.set_pulse_width(100e-9, channel=1)

# DC level
wfg.set_function("DC", channel=1)
wfg.set_offset(2.5, channel=1)
```

Dual Channel Operation
----------------------
```python
# Configure both channels independently
wfg.set_function("SINE", channel=1)
wfg.set_frequency(1000.0, channel=1)
wfg.set_amplitude(1.0, channel=1)

wfg.set_function("SQUARE", channel=2)
wfg.set_frequency(2000.0, channel=2)
wfg.set_amplitude(2.0, channel=2)

# Enable both outputs
wfg.set_output_state(True, channel=1)
wfg.set_output_state(True, channel=2)
```

Output Load
-----------
```python
# Set the expected output load (50 ohm or high impedance)
wfg.set_load(50.0, channel=1)        # 50 ohm
wfg.set_load("HZ", channel=1)        # high impedance
```

Reading Back Settings
---------------------
```python
# Read the current basic-wave configuration as a dict
cfg = wfg.get_waveform_config(channel=1)
print(cfg["WVTP"])   # e.g. 'SINE'

# Convenience scalar getters
print(f"Frequency: {wfg.get('frequency', channel=1):.6f} Hz")
print(f"Amplitude: {wfg.get('amplitude', channel=1):.6f} V")
print(f"Output on: {wfg.get('output', channel=1)}")
```

Arbitrary Waveforms
-------------------
```python
# Create a custom waveform that ramps 0 -> 5V and then holds at 5V
wfg.configure_ramp_hold_0_to_5(
    frequency=1000.0,
    ramp_fraction=0.2,
    sample_count=1024,
    name="RAMP_HOLD",
    channel=1,
)

# Enable output when ready
wfg.set_output_state(True, channel=1)

# Or load waveform points from a hand-edited file (CSV or whitespace text)
# containing normalized samples in [0.0, 1.0]
wfg.upload_arbitrary_waveform_file(
    file_path="my_waveform.csv",
    name="MY_WAVE",
    frequency=500.0,
    channel=1,
)
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("bk4055b_settings.txt")

dev = logger.connect("bk4055b")
logger.add(dev, "frequency", label="CH1_Freq")
for _ in range(100):
    logger.get_data()
logger.close_file()
```

Note: ``data_logger`` lives in a sibling project, not in this repo — this snippet
is documentation only. Waveform generators do not perform measurements; the
``get`` keys read back the currently programmed settings.

Supported Measurement Commands (for use with data_logger)
---------------------------------------------------------
- ``"frequency"`` - Programmed frequency of the channel (Hz)
- ``"amplitude"`` - Programmed amplitude of the channel (Vpp)
- ``"offset"`` - Programmed DC offset of the channel (V)
- ``"function"`` - Programmed waveform type of the channel (str)
- ``"output"`` - Output enable state of the channel (bool)

Configuration Functions
------------------------
- `set_function(function, channel)` - Set waveform type (SINE/SQUARE/RAMP/PULSE/NOISE/ARB/DC)
- `set_frequency(frequency, channel)` - Set frequency (Hz)
- `set_amplitude(amplitude, channel)` - Set amplitude (Vpp)
- `set_offset(offset, channel)` - Set DC offset (V)
- `set_dc_level(level, channel, ...)` - Set DC output level directly
- `ramp_to_level(target_v, slew_rate_v_per_s, ...)` - Slew-limited stepped DC ramp
- `ramp_to_level_safe(target_v, slew_rate_v_per_s, ...)` - Safe ramp sequence with output muted during mode switch
- `ramp_up_stay_up(...)` - Convenience wrapper to ramp and hold high
- `ramp_down_stay_down(...)` - Convenience wrapper to ramp and hold low
- `ramp_up_stay_up_safe(...)` - Safe-sequence wrapper to ramp and hold high
- `ramp_down_stay_down_safe(...)` - Safe-sequence wrapper to ramp and hold low
- `set_phase(phase, channel)` - Set phase (degrees)
- `set_duty_cycle(duty, channel)` - Set square-wave duty cycle (%)
- `set_symmetry(symmetry, channel)` - Set ramp-wave symmetry (%)
- `set_pulse_width(width, channel)` - Set pulse width (s)
- `set_load(load, channel)` - Set output load (ohm or "HZ")
- `set_output_state(state, channel)` - Enable/disable output
- `configure_sine(frequency, amplitude, offset, channel)` - One-call sine setup
- `upload_arbitrary_waveform(samples, name, ...)` - Upload/select custom ARB waveform
- `upload_arbitrary_waveform_file(file_path, name, ...)` - Load samples from file and upload
- `configure_ramp_hold_0_to_5(...)` - Convenience helper for 0->5V ramp then hold

Measurement / Readback Functions
---------------------------------
- `get_output_state(channel)` - Read output enable state
- `get_waveform_config(channel)` - Read basic-wave configuration as a dict
- `get(item, channel)` - String-keyed dispatcher used by data_logger

Connection
----------
- `connect(address)` - Establish VISA connection (auto-detect or explicit)
- `disconnect()` - Close connection

Error Handling
--------------
```python
try:
    wfg = BK4055B()
    wfg.set_frequency(1000.0, channel=1)
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

SCPI Command Reference
----------------------
- ``*IDN?`` - Instrument identification
- ``Cx:BSWV WVTP,<type>`` - Set basic waveform type
- ``Cx:BSWV FRQ,<hz>`` - Set frequency
- ``Cx:BSWV AMP,<vpp>`` - Set amplitude
- ``Cx:BSWV OFST,<v>`` - Set DC offset
- ``Cx:BSWV PHSE,<deg>`` - Set phase
- ``Cx:BSWV DUTY,<pct>`` - Set duty cycle (square)
- ``Cx:BSWV SYM,<pct>`` - Set symmetry (ramp)
- ``Cx:BSWV WIDTH,<s>`` - Set pulse width
- ``Cx:BSWV?`` - Query basic waveform configuration
- ``Cx:OUTP ON|OFF`` - Enable/disable output
- ``Cx:OUTP LOAD,<ohm|HZ>`` - Set output load
- ``Cx:OUTP?`` - Query output state
- ``Cx:WVDT WVNM,<name>,...,WAVEDATA,<d0>,<d1>,...`` - Upload user ARB data
- ``Cx:ARWV NAME,<name>`` - Select uploaded ARB waveform

Technical Specifications
------------------------
- **Channels**: 2 independent outputs
- **Frequency Range**: 1 uHz to 30 MHz (sine)
- **Waveforms**: Sine, square, ramp, pulse, noise, DC, arbitrary
- **Sample Rate**: 150 MSa/s
- **Interface**: USB, LAN via PyVISA

See Also
--------
- KS33500B: Keysight 33500B waveform generator
- KeysightMSOX4154A: Oscilloscope for waveform capture
- data_logger: Main orchestrator class
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

import pyvisa
from colorama import init, Fore, Style


# Loading module with fallback
try:
    from .loading import loading
except ImportError:
    try:
        from loading import loading
    except ImportError:
        class loading:
            """Fallback loading class if module unavailable."""
            def delay_with_loading_indicator(self, seconds: float) -> None:
                time.sleep(seconds)

# Optional mDNS/zeroconf discovery (the 'lan' extra). When unavailable, LAN
# auto-detection degrades gracefully and explicit address= still works.
try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    _HAS_ZEROCONF = True
except Exception:
    _HAS_ZEROCONF = False

# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.1

# Accepted basic-waveform type tokens (SDG/BK command set)
_FUNCTIONS = ("SINE", "SQUARE", "RAMP", "PULSE", "NOISE", "ARB", "DC")

# 4055B arbitrary waveform maximum points per channel
_MAX_ARB_POINTS = 16384

# LXI service types advertised by LAN-capable SCPI instruments
_LXI_SERVICES = ("_scpi-raw._tcp.local.", "_vxi-11._tcp.local.", "_lxi._tcp.local.")


class BK4055B:
    """B&K Precision 4055B waveform-generator driver.

    VISA-backed SCPI driver for the dual-channel 4055B function/arbitrary
    waveform generator, covering waveform setup, output control, and settings
    readback using the Siglent/SDG-style ``Cx:BSWV`` / ``Cx:OUTP`` command set.
    """

    def __init__(self, auto_connect: bool = True, address: Optional[str] = None, debug: bool = False):
        """
        Initialize BK4055B driver.

        Args:
            auto_connect: Automatically connect to device on initialization.
            address: Optional explicit VISA address.
            debug: Enable debug printing (default: False).

        Example:
            >>> wfg = BK4055B(auto_connect=False)
        """
        init(autoreset=True)

        self.rm: Optional[pyvisa.ResourceManager] = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status: str = "Not Connected"
        self.loading = loading()
        self.debug: bool = debug
        self._idn: Optional[str] = None
        self._address_hint: Optional[str] = address

        if auto_connect:
            self.connect(address=address)

    def connect(self, address: Optional[str] = None) -> None:
        """
        Establish connection to BK4055B waveform generator.

        Connection is attempted in order: (1) an explicit ``address``; (2) a
        VISA bus scan (USB/GPIB and registered TCPIP aliases) matching the
        model in ``*IDN?``; (3) zero-config LAN discovery via mDNS/LXI when the
        optional ``zeroconf`` dependency (the ``lan`` extra) is installed. The
        LAN fallback lets the instrument run on DHCP and be found automatically,
        so no per-user static IP configuration is required.

        Args:
            address: Optional explicit VISA resource string. If None, auto-detect
                by scanning the bus and matching the model in ``*IDN?``, then by
                mDNS LAN discovery.

        Raises:
            ConnectionError: If device not found or connection fails.

        Returns:
            None

        Example:
            >>> wfg = BK4055B(auto_connect=False)
            >>> wfg.connect(address="USB0::0xF4EC::0x1101::0123456789::INSTR")
        """
        # 1) Try explicit address first
        explicit = address or self._address_hint
        if explicit:
            try:
                inst = self.rm.open_resource(explicit)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000

                idn = inst.query("*IDN?").strip()
                if "4055" not in idn:
                    inst.close()
                    raise ConnectionError(
                        _ERROR_STYLE + f"Device at '{explicit}' is not a BK4055B (IDN='{idn}')."
                    )

                self.instrument = inst
                self.address = explicit
                self._idn = idn
            except pyvisa.VisaIOError as e:
                raise ConnectionError(_ERROR_STYLE + f"Failed to connect to '{explicit}': {e}")
            except ConnectionError:
                raise
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE + f"Unexpected error connecting to '{explicit}': {e}")

        # 2) Auto-detect by scanning resources and matching *IDN?
        if self.instrument is None:
            try:
                resources = list(self.rm.list_resources())
            except pyvisa.VisaIOError as e:
                raise ConnectionError(_ERROR_STYLE + f"PyVISA is not able to find any devices: {e}")

            for resource in resources:
                try:
                    inst = self.rm.open_resource(resource)
                    inst.read_termination = '\n'
                    inst.write_termination = '\n'
                    inst.timeout = 5000
                    idn = inst.query("*IDN?").strip()
                except Exception:
                    continue

                if "4055" in idn:
                    inst.timeout = 20000
                    self.instrument = inst
                    self.address = resource
                    self._idn = idn
                    break

                inst.close()

        # 2b) LAN fallback: discover the instrument's IP via mDNS/LXI and
        #     connect over TCPIP. This avoids requiring a per-user static IP.
        if self.instrument is None:
            for ip in self._discover_lan_hosts():
                resource = f"TCPIP0::{ip}::inst0::INSTR"
                try:
                    inst = self.rm.open_resource(resource)
                    inst.read_termination = '\n'
                    inst.write_termination = '\n'
                    inst.timeout = 5000
                    idn = inst.query("*IDN?").strip()
                except Exception:
                    continue

                if "4055" in idn:
                    inst.timeout = 20000
                    self.instrument = inst
                    self.address = resource
                    self._idn = idn
                    break

                inst.close()

            if self.instrument is None:
                raise ConnectionError(_ERROR_STYLE + "BK4055B not found")

        # 3) Confirm connection
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Failed to establish connection to BK4055B")

        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to {self.address}")

    def disconnect(self) -> None:
        """
        Close the connection to the device.

        Returns:
            None

        Example:
            >>> wfg.disconnect()
        """
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from BK4055B at {self.address}")
                self.instrument = None

        self.status = "Not Connected"
        self.address = None

    def _chk(self) -> None:
        """Verify device is connected before operations.

        Raises:
            ConnectionError: If not connected to device.
        """
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to BK4055B")

    def _discover_lan_hosts(self, timeout_s: float = 3.0) -> List[str]:
        """Discover candidate instrument IP addresses on the local network.

        Uses mDNS/zeroconf to browse for LXI service types advertised by
        LAN-capable SCPI instruments. Requires the optional ``zeroconf``
        dependency (the ``lan`` extra); if it is not installed, an empty list
        is returned and LAN auto-detection is skipped. The returned addresses
        are still verified with ``*IDN?`` by the caller, so non-4055B devices
        on the same network are harmless.

        Args:
            timeout_s: Seconds to browse for mDNS responses.

        Returns:
            A list of IPv4 address strings advertising an LXI/SCPI service.

        Example:
            >>> wfg = BK4055B(auto_connect=False)
            >>> isinstance(wfg._discover_lan_hosts(), list)
            True
        """
        if not _HAS_ZEROCONF:
            if self.debug:
                print(_WARNING_STYLE + "zeroconf not installed; LAN discovery skipped "
                      "(install the 'lan' extra).")
            return []

        found: List[str] = []

        class _Listener(ServiceListener):
            def _record(self, zc: "Zeroconf", type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name, timeout=int(timeout_s * 1000))
                if info is None:
                    return
                for addr in info.parsed_addresses():
                    if ":" not in addr and addr not in found:  # IPv4 only
                        found.append(addr)

            def add_service(self, zc: "Zeroconf", type_: str, name: str) -> None:
                self._record(zc, type_, name)

            def update_service(self, zc: "Zeroconf", type_: str, name: str) -> None:
                self._record(zc, type_, name)

            def remove_service(self, zc: "Zeroconf", type_: str, name: str) -> None:
                pass

        zc = Zeroconf()
        try:
            listener = _Listener()
            for service in _LXI_SERVICES:
                ServiceBrowser(zc, service, listener)
            time.sleep(timeout_s)
        finally:
            zc.close()

        if self.debug:
            print(f"LAN discovery found {len(found)} candidate host(s): {found}")
        return found

    @staticmethod
    def _parse_value(raw: str) -> float:
        """Strip a trailing unit from a SCPI value token and return a float.

        Args:
            raw: A value token such as ``"1000HZ"``, ``"2V"`` or ``"0.5"``.

        Returns:
            The numeric portion as a float.

        Raises:
            ValueError: If no numeric value can be parsed.

        Example:
            >>> BK4055B._parse_value("1000HZ")
            1000.0
        """
        match = re.match(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", raw.strip())
        if match is None:
            raise ValueError(_ERROR_STYLE + f"Unable to parse numeric value from '{raw}'")
        return float(match.group(0))

    # --- Configuration ---

    def set_function(self, function: str, channel: int = 1) -> None:
        """
        Set the basic waveform type for a channel.

        Args:
            function: Waveform type. One of SINE, SQUARE, RAMP, PULSE, NOISE,
                ARB, DC (case-insensitive).
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If an unsupported waveform type is requested.

        Returns:
            None

        Example:
            >>> wfg.set_function("SINE", channel=1)
        """
        self._chk()
        func = function.upper()
        if func not in _FUNCTIONS:
            raise ValueError(
                _ERROR_STYLE + f"Unsupported function '{function}'. Expected one of {_FUNCTIONS}."
            )
        command = f"C{channel}:BSWV WVTP,{func}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_frequency(self, frequency: float, channel: int = 1) -> None:
        """
        Set the waveform frequency for a channel.

        Args:
            frequency: Frequency in Hz.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_frequency(1000.0, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV FRQ,{frequency}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_amplitude(self, amplitude: float, channel: int = 1) -> None:
        """
        Set the waveform amplitude for a channel.

        Args:
            amplitude: Amplitude in Vpp (peak-to-peak voltage).
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_amplitude(2.0, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV AMP,{amplitude}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_offset(self, offset: float, channel: int = 1) -> None:
        """
        Set the waveform DC offset for a channel.

        Args:
            offset: DC offset in volts.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_offset(0.5, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV OFST,{offset}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_phase(self, phase: float, channel: int = 1) -> None:
        """
        Set the waveform phase for a channel.

        Args:
            phase: Phase in degrees.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_phase(90.0, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV PHSE,{phase}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_duty_cycle(self, duty: float, channel: int = 1) -> None:
        """
        Set the square-wave duty cycle for a channel.

        Args:
            duty: Duty cycle percentage (0-100).
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_duty_cycle(25.0, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV DUTY,{duty}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_symmetry(self, symmetry: float, channel: int = 1) -> None:
        """
        Set the ramp-wave symmetry for a channel.

        Args:
            symmetry: Symmetry percentage (0-100).
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_symmetry(80.0, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV SYM,{symmetry}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_pulse_width(self, width: float, channel: int = 1) -> None:
        """
        Set the pulse width for a channel.

        Args:
            width: Pulse width in seconds.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_pulse_width(100e-9, channel=1)
        """
        self._chk()
        command = f"C{channel}:BSWV WIDTH,{width}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_load(self, load: Union[float, str], channel: int = 1) -> None:
        """
        Set the expected output load for a channel.

        Args:
            load: Load resistance in ohms (e.g. ``50``), or the string ``"HZ"``
                for high impedance.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If a non-numeric, non-"HZ" string load is provided.

        Returns:
            None

        Example:
            >>> wfg.set_load(50.0, channel=1)
            >>> wfg.set_load("HZ", channel=1)
        """
        self._chk()
        if isinstance(load, str):
            token = load.upper()
            if token != "HZ":
                raise ValueError(_ERROR_STYLE + f"Invalid load '{load}'. Expected a number or 'HZ'.")
        else:
            token = str(load)
        command = f"C{channel}:OUTP LOAD,{token}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_output_state(self, state: bool, channel: int = 1) -> None:
        """
        Enable or disable a channel output.

        Args:
            state: True to enable the output, False to disable it.
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_output_state(True, channel=1)
        """
        self._chk()
        command = f"C{channel}:OUTP {'ON' if state else 'OFF'}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def configure_sine(
        self,
        frequency: float,
        amplitude: float,
        offset: float = 0.0,
        channel: int = 1,
    ) -> None:
        """
        Configure a channel for a sine wave in a single call.

        Args:
            frequency: Frequency in Hz.
            amplitude: Amplitude in Vpp.
            offset: DC offset in volts (default: 0.0).
            channel: Output channel (1 or 2).

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.configure_sine(1000.0, 2.0, offset=0.0, channel=1)
        """
        self._chk()
        command = (
            f"C{channel}:BSWV WVTP,SINE,FRQ,{frequency},AMP,{amplitude},OFST,{offset}"
        )
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_dc_level(
        self,
        level: float,
        channel: int = 1,
        ensure_dc: bool = True,
        settle_s: float = _DELAY,
    ) -> None:
        """
        Set a channel to a specific DC output level.

        Args:
            level: Target DC level in volts.
            channel: Output channel (1 or 2).
            ensure_dc: If True, switch the channel waveform type to DC first.
            settle_s: Optional settle delay after writing the level.

        Raises:
            ConnectionError: If not connected to device.

        Returns:
            None

        Example:
            >>> wfg.set_dc_level(2.5, channel=1)
        """
        self._chk()
        if ensure_dc:
            self.set_function("DC", channel=channel)

        command = f"C{channel}:BSWV OFST,{level}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        if settle_s > 0.0:
            time.sleep(settle_s)

    def ramp_to_level(
        self,
        target_v: float,
        slew_rate_v_per_s: float,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        ensure_dc: bool = True,
        output_on: bool = False,
    ) -> None:
        """
        Ramp DC level to a target using fixed steps and a specified slew rate.

        The method reads the current offset, then steps toward ``target_v``.
        Step timing is chosen so each step obeys ``slew_rate_v_per_s``.

        Args:
            target_v: Final DC level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s (must be > 0).
            channel: Output channel (1 or 2).
            step_v: Step size in volts (must be > 0).
            dwell_s: Minimum dwell after each step in seconds.
            ensure_dc: If True, force waveform type to DC before ramping.
            output_on: If True, enable output after ramp completion.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If slew rate or step size are invalid.

        Returns:
            None

        Example:
            >>> wfg.ramp_to_level(target_v=5.0, slew_rate_v_per_s=1.0, channel=1)
        """
        self._chk()
        if slew_rate_v_per_s <= 0.0:
            raise ValueError(_ERROR_STYLE + "slew_rate_v_per_s must be > 0.")
        if step_v <= 0.0:
            raise ValueError(_ERROR_STYLE + "step_v must be > 0.")

        cfg = self.get_waveform_config(channel=channel)
        start_v = self._parse_value(cfg.get("OFST", "0"))

        if ensure_dc and cfg.get("WVTP", "").upper() != "DC":
            # Preserve the pre-switch offset to avoid a visible 0V dip while
            # changing WVTP to DC.
            self.set_function("DC", channel=channel)
            self.set_dc_level(start_v, channel=channel, ensure_dc=False, settle_s=0.0)
            cfg = self.get_waveform_config(channel=channel)
            start_v = self._parse_value(cfg.get("OFST", str(start_v)))
        delta = target_v - start_v
        if abs(delta) < 1e-12:
            if output_on:
                self.set_output_state(True, channel=channel)
            return

        direction = 1.0 if delta > 0.0 else -1.0
        current = start_v

        while (target_v - current) * direction > step_v:
            next_v = current + direction * step_v
            self.set_dc_level(next_v, channel=channel, ensure_dc=False, settle_s=0.0)
            wait_s = max(abs(next_v - current) / slew_rate_v_per_s, dwell_s)
            if wait_s > 0.0:
                time.sleep(wait_s)
            current = next_v

        self.set_dc_level(target_v, channel=channel, ensure_dc=False, settle_s=0.0)
        final_wait_s = max(abs(target_v - current) / slew_rate_v_per_s, dwell_s)
        if final_wait_s > 0.0:
            time.sleep(final_wait_s)

        if output_on:
            self.set_output_state(True, channel=channel)

    def ramp_to_level_safe(
        self,
        target_v: float,
        slew_rate_v_per_s: float,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        start_v: Optional[float] = None,
        output_on: bool = True,
    ) -> None:
        """
        Ramp to a target using a safe DC-transition sequence.

        This method prevents visible transients caused by internal range/mode
        switching. If the channel is not already in DC mode, it uses:
        1) output OFF, 2) set WVTP=DC, 3) preload start level, 4) output ON,
        5) run slew-limited ramp.

        If already in DC mode, it skips output muting to avoid an apparent
        drop-to-zero at ramp start.

        Args:
            target_v: Final DC level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s.
            channel: Output channel (1 or 2).
            step_v: Step size in volts.
            dwell_s: Minimum dwell after each step in seconds.
            start_v: Optional explicit ramp start level. If None, uses current
                configured offset from ``BSWV?``.
            output_on: If True, keep output enabled at method exit.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If parameters are invalid.

        Returns:
            None

        Example:
            >>> wfg.ramp_to_level_safe(target_v=5.0, slew_rate_v_per_s=0.5)
        """
        self._chk()

        cfg = self.get_waveform_config(channel=channel)
        current_mode = cfg.get("WVTP", "").upper()
        current_v = self._parse_value(cfg.get("OFST", "0"))
        initial_v = current_v if start_v is None else float(start_v)

        if current_mode != "DC":
            self.set_output_state(False, channel=channel)
            self.set_function("DC", channel=channel)
            self.set_dc_level(initial_v, channel=channel, ensure_dc=False, settle_s=0.0)
            if output_on:
                self.set_output_state(True, channel=channel)
        elif abs(initial_v - current_v) > 1e-12:
            # Already in DC mode: do not mute output unless caller requests
            # output_off at end. Just rebase start level directly.
            self.set_dc_level(initial_v, channel=channel, ensure_dc=False, settle_s=0.0)

        self.ramp_to_level(
            target_v=target_v,
            slew_rate_v_per_s=slew_rate_v_per_s,
            channel=channel,
            step_v=step_v,
            dwell_s=dwell_s,
            ensure_dc=False,
            output_on=False,
        )

        if not output_on:
            self.set_output_state(False, channel=channel)

    def ramp_up_stay_up(
        self,
        target_v: float = 5.0,
        slew_rate_v_per_s: float = 1.0,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        ensure_dc: bool = True,
        output_on: bool = False,
    ) -> None:
        """
        Ramp DC level upward and hold at the final high level.

        Args:
            target_v: Final high level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s.
            channel: Output channel (1 or 2).
            step_v: Step size in volts.
            dwell_s: Minimum dwell after each step in seconds.
            ensure_dc: If True, force waveform type to DC before ramping.
            output_on: If True, enable output after ramp completion.

        Returns:
            None

        Example:
            >>> wfg.ramp_up_stay_up(target_v=5.0, slew_rate_v_per_s=0.5)
        """
        self.ramp_to_level(
            target_v=target_v,
            slew_rate_v_per_s=slew_rate_v_per_s,
            channel=channel,
            step_v=step_v,
            dwell_s=dwell_s,
            ensure_dc=ensure_dc,
            output_on=output_on,
        )

    def ramp_down_stay_down(
        self,
        target_v: float = 0.0,
        slew_rate_v_per_s: float = 1.0,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        ensure_dc: bool = True,
        output_on: bool = False,
    ) -> None:
        """
        Ramp DC level downward and hold at the final low level.

        Args:
            target_v: Final low level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s.
            channel: Output channel (1 or 2).
            step_v: Step size in volts.
            dwell_s: Minimum dwell after each step in seconds.
            ensure_dc: If True, force waveform type to DC before ramping.
            output_on: If True, enable output after ramp completion.

        Returns:
            None

        Example:
            >>> wfg.ramp_down_stay_down(target_v=0.0, slew_rate_v_per_s=0.5)
        """
        self.ramp_to_level(
            target_v=target_v,
            slew_rate_v_per_s=slew_rate_v_per_s,
            channel=channel,
            step_v=step_v,
            dwell_s=dwell_s,
            ensure_dc=ensure_dc,
            output_on=output_on,
        )

    def ramp_up_stay_up_safe(
        self,
        target_v: float = 5.0,
        slew_rate_v_per_s: float = 1.0,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        start_v: Optional[float] = None,
        output_on: bool = True,
    ) -> None:
        """
        Safe-sequence wrapper to ramp DC upward and hold at the high level.

        Args:
            target_v: Final high level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s.
            channel: Output channel (1 or 2).
            step_v: Step size in volts.
            dwell_s: Minimum dwell after each step in seconds.
            start_v: Optional explicit ramp start level.
            output_on: If True, keep output enabled at method exit.

        Returns:
            None

        Example:
            >>> wfg.ramp_up_stay_up_safe(target_v=5.0, slew_rate_v_per_s=0.5)
        """
        self.ramp_to_level_safe(
            target_v=target_v,
            slew_rate_v_per_s=slew_rate_v_per_s,
            channel=channel,
            step_v=step_v,
            dwell_s=dwell_s,
            start_v=start_v,
            output_on=output_on,
        )

    def ramp_down_stay_down_safe(
        self,
        target_v: float = 0.0,
        slew_rate_v_per_s: float = 1.0,
        channel: int = 1,
        step_v: float = 0.05,
        dwell_s: float = 0.0,
        start_v: Optional[float] = None,
        output_on: bool = True,
    ) -> None:
        """
        Safe-sequence wrapper to ramp DC downward and hold at the low level.

        Args:
            target_v: Final low level in volts.
            slew_rate_v_per_s: Requested slew rate in V/s.
            channel: Output channel (1 or 2).
            step_v: Step size in volts.
            dwell_s: Minimum dwell after each step in seconds.
            start_v: Optional explicit ramp start level.
            output_on: If True, keep output enabled at method exit.

        Returns:
            None

        Example:
            >>> wfg.ramp_down_stay_down_safe(target_v=0.0, slew_rate_v_per_s=0.5)
        """
        self.ramp_to_level_safe(
            target_v=target_v,
            slew_rate_v_per_s=slew_rate_v_per_s,
            channel=channel,
            step_v=step_v,
            dwell_s=dwell_s,
            start_v=start_v,
            output_on=output_on,
        )

    def upload_arbitrary_waveform(
        self,
        samples: List[float],
        name: str = "wave1",
        channel: int = 1,
        frequency: float = 1000.0,
        amplitude: float = 5.0,
        offset: float = 2.5,
        phase: float = 0.0,
        select: bool = True,
    ) -> None:
        """
        Upload a custom arbitrary waveform to user memory.

        The 4055B accepts user-waveform data with ``Cx:WVDT``. This method
        takes normalized samples in the range [0.0, 1.0], maps them to 14-bit
        DAC codes [0, 16383], uploads them, and optionally selects the uploaded
        waveform for output using ``Cx:ARWV`` + ``Cx:BSWV WVTP,ARB``.

        Args:
            samples: Normalized waveform points in [0.0, 1.0].
            name: User-waveform name in instrument memory.
            channel: Output channel (1 or 2).
            frequency: Output repetition frequency in Hz.
            amplitude: Output amplitude in Vpp when ARB mode is active.
            offset: Output DC offset in volts when ARB mode is active.
            phase: Output phase in degrees when ARB mode is active.
            select: If True, select this waveform as the active ARB.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If sample values are out of range or too few points are
                provided.

        Returns:
            None

        Example:
            >>> wfg.upload_arbitrary_waveform([0.0, 0.5, 1.0, 1.0], name="RAMP_HOLD")
        """
        self._chk()
        if len(samples) < 4:
            raise ValueError(_ERROR_STYLE + "Arbitrary waveform requires at least 4 samples.")
        if len(samples) > _MAX_ARB_POINTS:
            raise ValueError(
                _ERROR_STYLE
                + f"Arbitrary waveform exceeds {_MAX_ARB_POINTS} points (got {len(samples)})."
            )

        dac_values: List[int] = []
        for value in samples:
            if value < 0.0 or value > 1.0:
                raise ValueError(_ERROR_STYLE + "Samples must be normalized to [0.0, 1.0].")
            dac_values.append(int(round(value * 16383.0)))

        data_csv = ",".join(str(v) for v in dac_values)
        command = f"C{channel}:WVDT WVNM,{name},WAVEDATA,{data_csv}"
        if self.debug:
            print(command)
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

        if select:
            select_command = f"C{channel}:ARWV NAME,{name}"
            if self.debug:
                print(select_command)
            self.instrument.write(select_command)
            self.instrument.write(f"C{channel}:BSWV WVTP,ARB")
            # Configure ARB playback parameters after selecting the uploaded
            # waveform. This is more robust than embedding metadata in WVDT.
            self.instrument.write(f"C{channel}:BSWV FRQ,{frequency}")
            self.instrument.write(f"C{channel}:BSWV AMP,{amplitude}")
            self.instrument.write(f"C{channel}:BSWV OFST,{offset}")
            self.instrument.write(f"C{channel}:BSWV PHSE,{phase}")
            self.loading.delay_with_loading_indicator(_DELAY)

    def upload_arbitrary_waveform_file(
        self,
        file_path: str,
        name: str = "wave1",
        channel: int = 1,
        frequency: float = 1000.0,
        amplitude: float = 5.0,
        offset: float = 2.5,
        phase: float = 0.0,
        select: bool = True,
    ) -> None:
        """
        Load waveform points from an ASCII CSV/DAT file and upload as ARB data.

        File format:
        - Numeric sample values normalized to [0.0, 1.0]
        - Comma, whitespace, or newline separators are accepted
        - Lines may contain comments starting with ``#``
        - Typical extensions are ``.csv`` and ``.dat`` (ASCII text)
        - Maximum point count is 16384 samples per channel

        Args:
            file_path: Path to text/CSV waveform file.
            name: User-waveform name in instrument memory.
            channel: Output channel (1 or 2).
            frequency: Output repetition frequency in Hz.
            amplitude: Output amplitude in Vpp when ARB mode is active.
            offset: Output DC offset in volts when ARB mode is active.
            phase: Output phase in degrees when ARB mode is active.
            select: If True, select this waveform as the active ARB.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If the file has no valid numeric samples.

        Returns:
            None

        Example:
            >>> wfg.upload_arbitrary_waveform_file("ramp_hold.csv", name="RAMP_HOLD")
        """
        self._chk()

        path = Path(file_path)
        if not path.exists():
            raise ValueError(_ERROR_STYLE + f"Waveform file not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix and suffix not in (".csv", ".dat", ".txt"):
            raise ValueError(
                _ERROR_STYLE
                + f"Unsupported waveform file extension '{path.suffix}'. Use .csv or .dat ASCII files."
            )

        values: List[float] = []
        try:
            file_text = path.read_text(encoding="ascii")
        except UnicodeDecodeError as e:
            raise ValueError(_ERROR_STYLE + f"Waveform file must be ASCII text: {file_path}") from e

        for line in file_text.splitlines():
            cleaned = line.split("#", 1)[0].strip()
            if not cleaned:
                continue
            parts = re.split(r"[\s,;]+", cleaned)
            for token in parts:
                if token:
                    values.append(float(token))

        if not values:
            raise ValueError(_ERROR_STYLE + f"Waveform file contains no numeric samples: {file_path}")

        self.upload_arbitrary_waveform(
            samples=values,
            name=name,
            channel=channel,
            frequency=frequency,
            amplitude=amplitude,
            offset=offset,
            phase=phase,
            select=select,
        )

    def configure_ramp_hold_0_to_5(
        self,
        frequency: float = 1000.0,
        ramp_fraction: float = 0.2,
        sample_count: int = 1024,
        name: str = "RAMP_HOLD",
        channel: int = 1,
        output_on: bool = False,
    ) -> None:
        """
        Configure a 0->5V ramp waveform that then holds at 5V.

        The generated single-cycle waveform ramps from 0V to 5V over
        ``ramp_fraction`` of the cycle, then stays at 5V for the remainder.
        Internally this is uploaded as a normalized ARB shape and scaled using
        ``AMPL=5V`` and ``OFST=2.5V`` so the final output range is 0V..5V.

        Args:
            frequency: Waveform repetition frequency in Hz.
            ramp_fraction: Fraction of one cycle used for the linear ramp
                (0 < ramp_fraction < 1).
            sample_count: Number of samples in one cycle (>= 8 recommended).
            name: User-waveform name in instrument memory.
            channel: Output channel (1 or 2).
            output_on: If True, enable output after configuration.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If parameters are invalid.

        Returns:
            None

        Example:
            >>> wfg.configure_ramp_hold_0_to_5(frequency=1000.0, ramp_fraction=0.2)
        """
        self._chk()
        if sample_count < 8:
            raise ValueError(_ERROR_STYLE + "sample_count must be >= 8.")
        if ramp_fraction <= 0.0 or ramp_fraction >= 1.0:
            raise ValueError(_ERROR_STYLE + "ramp_fraction must be between 0 and 1.")

        ramp_points = max(2, int(round(sample_count * ramp_fraction)))
        hold_points = sample_count - ramp_points
        if hold_points < 1:
            hold_points = 1
            ramp_points = sample_count - 1

        ramp = [i / float(ramp_points - 1) for i in range(ramp_points)]
        hold = [1.0] * hold_points
        waveform = ramp + hold

        self.upload_arbitrary_waveform(
            waveform,
            name=name,
            channel=channel,
            frequency=frequency,
            amplitude=5.0,
            offset=2.5,
            phase=0.0,
            select=True,
        )
        if output_on:
            self.set_output_state(True, channel=channel)

    # --- Readback ---

    def get_output_state(self, channel: int = 1) -> bool:
        """
        Read the output enable state of a channel.

        Args:
            channel: Output channel (1 or 2).

        Returns:
            True if the output is enabled, False otherwise.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If the instrument returns an unparseable response.

        Example:
            >>> wfg.get_output_state(channel=1)
            True
        """
        self._chk()
        command = f"C{channel}:OUTP?"
        if self.debug:
            print(command)
        raw = self.instrument.query(command).strip()
        # Response form: 'C1:OUTP ON,LOAD,50,PLRT,NOR'
        body = raw.split(" ", 1)[-1]
        state_token = body.split(",", 1)[0].strip().upper()
        if state_token not in ("ON", "OFF"):
            raise ValueError(_ERROR_STYLE + f"Unparseable output state response: '{raw}'")
        return state_token == "ON"

    def get_waveform_config(self, channel: int = 1) -> Dict[str, str]:
        """
        Read the basic-wave configuration of a channel as a dictionary.

        Args:
            channel: Output channel (1 or 2).

        Returns:
            A dictionary of SCPI key/value pairs, e.g.
            ``{"WVTP": "SINE", "FRQ": "1000HZ", "AMP": "2V", "OFST": "0V", ...}``.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If the instrument returns an unparseable response.

        Example:
            >>> cfg = wfg.get_waveform_config(channel=1)
            >>> cfg["WVTP"]
            'SINE'
        """
        self._chk()
        command = f"C{channel}:BSWV?"
        if self.debug:
            print(command)
        raw = self.instrument.query(command).strip()
        # Response form: 'C1:BSWV WVTP,SINE,FRQ,1000HZ,AMP,2V,OFST,0V,...'
        body = raw.split(" ", 1)[-1]
        tokens = [t.strip() for t in body.split(",")]
        if len(tokens) < 2:
            raise ValueError(_ERROR_STYLE + f"Unparseable BSWV response: '{raw}'")
        config: Dict[str, str] = {}
        for i in range(0, len(tokens) - 1, 2):
            config[tokens[i]] = tokens[i + 1]
        return config

    def get(self, item: str, channel: int = 1) -> Union[float, str, bool]:
        """
        String-keyed dispatcher used by data_logger.

        Args:
            item: Measurement/readback key. One of ``"frequency"``,
                ``"amplitude"``, ``"offset"``, ``"function"``, ``"output"``.
            channel: Output channel (1 or 2).

        Returns:
            The requested value: a float for ``frequency``/``amplitude``/
            ``offset``, a string for ``function``, or a bool for ``output``.

        Raises:
            ConnectionError: If not connected to device.
            ValueError: If an unknown key is requested or the response cannot
                be parsed.

        Example:
            >>> wfg.get("frequency", channel=1)
            1000.0
        """
        self._chk()
        key = item.lower()
        if key == "output":
            return self.get_output_state(channel)

        config = self.get_waveform_config(channel)
        if key == "function":
            return config.get("WVTP", "")
        scpi_map = {"frequency": "FRQ", "amplitude": "AMP", "offset": "OFST"}
        if key not in scpi_map:
            raise ValueError(
                _ERROR_STYLE
                + f"Unknown item '{item}'. Expected one of "
                + "frequency, amplitude, offset, function, output."
            )
        scpi_key = scpi_map[key]
        if scpi_key not in config:
            raise ValueError(_ERROR_STYLE + f"Response missing '{scpi_key}': {config}")
        return self._parse_value(config[scpi_key])
