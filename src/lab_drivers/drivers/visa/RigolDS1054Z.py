#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file RigolDS1054Z.py
#   @brief Rigol DS1054Z (DS1000Z series) digital oscilloscope, VISA/SCPI.
#   @date 27-May-2026
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
Rigol DS1054Z Digital Oscilloscope Driver
==========================================

This module provides a driver for the Rigol DS1000Z series digital storage
oscilloscope (tested on DS1054Z) with support for screenshot and waveform
capture from any enabled analog channel.

Features
--------
- **4 Analog Channels**: 50 MHz bandwidth per channel (DS1054Z); same SCPI
  surface as DS1074Z (70 MHz) and DS1104Z (100 MHz).
- **Auto-Detection**: Automatically finds DS1000Z scopes on the VISA bus
  (USB or LAN) via resource-string match plus ``*IDN?`` probing.
- **Screenshot Capture**: Save the live screen as a BMP image
  (~1,152,054 bytes for the 800x480 24-bit display).
- **Waveform Readback**: Pull the on-screen 1200-pt NORMal trace or the
  full memory-depth RAW record from each enabled channel.
- **CSV Export**: ``save_waveform()`` writes all enabled channels to a CSV
  with a shared time column (volts and seconds via the WAV preamble).

Basic Usage
-----------
```python
from lab_drivers.drivers.visa.RigolDS1054Z import RigolDS1054Z

# Auto-connect to the first DS1000Z found on the bus.
scope = RigolDS1054Z()

# Capture the live screen as BMP.
scope.save_screenshot("shot.bmp")

# Capture the on-screen waveform of every enabled channel (1200 pts each).
scope.save_waveform("trace.csv")

# Capture the full memory depth (scope is stopped, then resumed).
scope.save_waveform("trace_raw.csv", raw=True)

scope.disconnect()
```

Explicit Connection
-------------------
```python
# Explicit VISA resource string.
scope = RigolDS1054Z(auto_connect=False)
scope.connect(address="USB0::0x1AB1::0x04CE::DS1ZA171004073::INSTR")

# Or connect by IP address (LAN option).
scope = RigolDS1054Z(ip_address="192.168.1.100")
```

Waveform Capture
----------------
```python
# Per-channel readback returns (times_s, volts, preamble).
t, v, pre = scope.get_waveform(channel=1)
print(f"{len(v)} samples at {1/pre['xinc']:.0f} Sa/s")

# Full memory depth (DS1054Z can record up to 24 Mpts single-channel).
t, v, _ = scope.get_waveform(channel=1, raw=True)
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("ds1054z_capture.txt")
scope = logger.connect("ds1054z")
logger.add(scope, "SCREENSHOT")
logger.add(scope, "WAVEFORM", label="ch1", channel=1)
logger.get_data()
logger.close_file()
```

Note: ``data_logger`` lives in a sibling project, not in this repo — this
snippet is documentation only.

Supported Measurement Commands (for use with data_logger)
---------------------------------------------------------
- ``"SCREENSHOT"`` - Capture the live screen to a BMP file
  (uses ``save_screenshot()``; pass a path via ``set_screenshot_path()``).
- ``"WAVEFORM"`` - Capture all enabled channels to a CSV file
  (uses ``save_waveform()``; pass a path via ``set_waveform_path()``).

Available Methods
-----------------
- ``connect(address=None, ip_address=None)`` - Open a VISA session.
- ``disconnect()`` - Close the VISA session.
- ``get(item, channel=1)`` - String-keyed dispatcher.
- ``get_screenshot()`` - Return raw BMP bytes.
- ``save_screenshot(filename=None)`` - Save BMP to disk.
- ``set_screenshot_path(filename)`` - Default path for ``"SCREENSHOT"``.
- ``enabled_channels()`` - List of currently-displayed analog channels.
- ``get_waveform(channel=1, raw=False)`` - Per-channel ``(t, v, preamble)``.
- ``save_waveform(filename=None, channels=None, raw=False)`` - Multi-channel
  CSV export.
- ``set_waveform_path(filename)`` - Default path for ``"WAVEFORM"``.
- ``write(cmd)`` / ``query(cmd)`` - Low-level SCPI passthroughs.

Error Handling
--------------
```python
try:
    scope = RigolDS1054Z()
    scope.save_screenshot("shot.bmp")
except ConnectionError as e:
    print(f"Scope unreachable: {e}")
```

SCPI Command Reference
----------------------
- ``:DISP:DATA?`` - Returns the screen as an 800x480 24-bit BMP image
  (IEEE 488.2 definite-length binary block, ~1,152,054 bytes).
- ``:WAV:SOUR CHAN<n>`` - Select source channel for waveform readout.
- ``:WAV:MODE NORM|MAX|RAW`` - Pick on-screen trace vs full-memory record.
- ``:WAV:FORM BYTE|WORD|ASCII`` - This driver always uses ``BYTE``.
- ``:WAV:STAR n`` / ``:WAV:STOP n`` - Inclusive 1-based sample window
  (required for chunked RAW reads; per query <= ~250 000 bytes).
- ``:WAV:PRE?`` - Returns 10 comma-separated preamble fields:
  ``format, type, points, count, xinc, xorig, xref, yinc, yorig, yref``.
- ``:WAV:DATA?`` - Returns the configured sample window as a binary block.
- ``:CHAN<n>:DISP?`` - 1 if the channel is currently displayed.
- ``:STOP`` / ``:RUN`` / ``:TRIG:STAT?`` - Run-state control (required to
  use ``:WAV:MODE RAW``).

Technical Specifications
------------------------
- **Channels**: 4 analog (DS1054Z), software-upgradable bandwidth.
- **Bandwidth**: 50 MHz (DS1054Z), 70 MHz (DS1074Z), 100 MHz (DS1104Z).
- **Sample Rate**: Up to 1 GSa/s (single-channel), 500 MSa/s (dual),
  250 MSa/s (3-4 channel).
- **Memory Depth**: Up to 24 Mpts (single-channel), 12 Mpts (dual),
  6 Mpts (3-4 channel).
- **Vertical Resolution**: 8 bits.
- **Screen**: 800x480, 24-bit BMP via ``:DISP:DATA?``.
- **Interface**: USB Device, LAN via PyVISA.

See Also
--------
- RigolDS7034: Higher-end Rigol scope with the same SCPI family.
- KeysightMSOX4154A / TektronixMSO4: Alternative scope drivers in this repo.
- data_logger: Sibling orchestrator that consumes the ``get(item)`` keys.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pyvisa
from colorama import Fore, Style, init

# Optional UX helper to mirror the rest of the codebase.
try:
    from loading import loading
except Exception:
    class loading:
        def delay_with_loading_indicator(self, seconds: float) -> None:
            time.sleep(seconds)


# Module-level style constants (match the other drivers in this repo).
_ERROR_STYLE   = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "
_DELAY         = 0.1  # seconds

# DS1000Z returns a fixed 800x480 24-bit BMP plus header => 1,152,054 bytes.
_BMP_EXPECTED_BYTES = 1_152_054

# DS1000Z caps :WAV:DATA? returns to ~250000 bytes per query in RAW mode.
# 100k is a safe chunk that keeps TMC framing happy.
_RAW_CHUNK = 100_000

# Substrings used to identify a DS1000Z either in the VISA resource string
# or in the *IDN? response.
_IDN_KEYWORDS = ("DS1054Z", "DS1074Z", "DS1104Z", "DS1Z", "DS1000Z")


class RigolDS1054Z:
    """Rigol DS1054Z (DS1000Z series) oscilloscope driver.

    VISA-backed SCPI driver covering screen capture and per-channel waveform
    readback in either on-screen (NORMal) or full-memory (RAW) mode.

    Supported ``get(item, ...)`` keys include ``"SCREENSHOT"`` and
    ``"WAVEFORM"``.
    """

    # -----------------------------
    # Init / Connect / Disconnect
    # -----------------------------
    def __init__(
        self,
        auto_connect: bool = True,
        address: Optional[str] = None,
        ip_address: Optional[str] = None,
        timeout_ms: int = 60_000,
        debug: bool = False,
    ) -> None:
        """Initialize the driver and optionally connect.

        Args:
            auto_connect: If True, call ``connect()`` immediately.
            address: Explicit VISA resource string (skips auto-discovery).
            ip_address: Scope IP address; constructs a TCPIP resource string.
            timeout_ms: VISA I/O timeout in milliseconds.
            debug: Print extra diagnostic messages.

        Example:
            >>> scope = RigolDS1054Z()
            >>> scope.disconnect()
        """
        init(autoreset=True)

        self.rm = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.loading = loading()
        self.status = "Not Connected"
        self._idn: Optional[str] = None
        self._address_hint = address
        self._ip_address = ip_address
        self._timeout_ms = timeout_ms
        self.debug = debug

        # Default destination paths used by the get(item) dispatcher.
        self.screenshot_filename: Optional[str] = None
        self.waveform_filename: Optional[str] = None

        if auto_connect:
            self.connect(address=self._address_hint, ip_address=self._ip_address)

    def connect(
        self,
        address: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Open a VISA session to the scope.

        Resolution order:

        1. Explicit ``address`` argument (or ``ip_address`` -> TCPIP string).
        2. Constructor hints (``self._address_hint`` / ``self._ip_address``).
        3. Auto-scan: any resource string containing a DS1000Z keyword.
        4. Auto-scan: probe USB/TCPIP resources with ``*IDN?``.

        Args:
            address: Explicit VISA resource string.
            ip_address: IP address (LAN) used to build a TCPIP resource.

        Raises:
            ConnectionError: If no DS1000Z is reachable.

        Example:
            >>> scope = RigolDS1054Z(auto_connect=False)
            >>> scope.connect(ip_address="192.168.1.100")
        """
        ip = ip_address or self._ip_address
        if ip and not (address or self._address_hint):
            address = f"TCPIP0::{ip}::inst0::INSTR"

        candidate = address or self._address_hint
        if candidate:
            self._open(candidate, verify_idn=True)
            return

        resources = self.rm.list_resources()
        if self.debug:
            print(f"\n[DEBUG] Found {len(resources)} VISA resources:")
            for r in resources:
                print(f"  {r}")

        if not resources:
            raise ConnectionError(_ERROR_STYLE +
                "No VISA resources found. Is the scope powered on and connected?")

        for res in resources:
            if any(k in res.upper() for k in _IDN_KEYWORDS):
                self._open(res, verify_idn=True)
                return

        for res in resources:
            if not (res.startswith("USB") or res.startswith("TCPIP")):
                continue
            try:
                inst = self.rm.open_resource(res)
                inst.timeout = 2000
                idn = inst.query("*IDN?").strip()
                inst.close()
            except pyvisa.VisaIOError:
                continue
            if any(k in idn.upper() for k in _IDN_KEYWORDS):
                self._open(res, verify_idn=True)
                return

        raise ConnectionError(_ERROR_STYLE +
            f"DS1054Z not found. Available resources: {resources}")

    def _open(self, resource: str, verify_idn: bool) -> None:
        """Open ``resource`` and (optionally) verify it is a DS1000Z."""
        try:
            inst = self.rm.open_resource(resource)
        except pyvisa.VisaIOError as e:
            raise ConnectionError(_ERROR_STYLE +
                f"Failed to open VISA resource '{resource}': {e}") from e
        inst.timeout = self._timeout_ms
        inst.chunk_size = 1024 * 1024
        try:
            inst.read_termination = "\n"
        except Exception:
            pass
        idn = inst.query("*IDN?").strip()
        if verify_idn and not any(k in idn.upper() for k in _IDN_KEYWORDS):
            inst.close()
            raise ConnectionError(_ERROR_STYLE +
                f"Resource '{resource}' is not a DS1000Z (IDN='{idn}').")
        self.instrument = inst
        self.address = resource
        self._idn = idn
        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to {idn} at {resource}")

    def disconnect(self) -> None:
        """Close the VISA session and reset connection state.

        Example:
            >>> scope.disconnect()
        """
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                self.instrument = None
                self.address = None
                self.status = "Not Connected"

    def __enter__(self) -> "RigolDS1054Z":
        if self.instrument is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _chk(self) -> None:
        """Raise ``ConnectionError`` if no VISA session is open."""
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE +
                "Not connected to Rigol DS1054Z Oscilloscope.")

    # -----------------------------
    # Low-level SCPI passthrough
    # -----------------------------
    def write(self, cmd: str) -> None:
        """Send a raw SCPI command (no response).

        Args:
            cmd: SCPI command string.

        Raises:
            ConnectionError: If not connected.

        Example:
            >>> scope.write(":CHAN1:DISP ON")
        """
        self._chk()
        self.instrument.write(cmd)

    def query(self, cmd: str) -> str:
        """Send a SCPI query and return the stripped response.

        Args:
            cmd: SCPI query string ending in ``?``.

        Returns:
            Trimmed response text.

        Raises:
            ConnectionError: If not connected.

        Example:
            >>> scope.query("*IDN?")
            'RIGOL TECHNOLOGIES,DS1054Z,...'
        """
        self._chk()
        return self.instrument.query(cmd).strip()

    # -----------------------------
    # get() dispatcher
    # -----------------------------
    def get(self, item: str, channel: int = 1):
        """String-keyed dispatcher used by ``data_logger``.

        Args:
            item: ``"SCREENSHOT"`` or ``"WAVEFORM"`` (case-sensitive,
                uppercase to match the other scope drivers in this repo).
            channel: Reserved for future per-channel keys (waveform CSV
                always exports every enabled channel).

        Returns:
            For ``"SCREENSHOT"``: the path written.
            For ``"WAVEFORM"``: the path written.

        Raises:
            ConnectionError: If not connected.
            ValueError: If ``item`` is not a recognized key.

        Example:
            >>> scope.set_screenshot_path("shot.bmp")
            >>> scope.get("SCREENSHOT")
            'shot.bmp'
        """
        self._chk()
        key = item.upper()
        if key == "SCREENSHOT":
            return self.save_screenshot(self.screenshot_filename)
        if key == "WAVEFORM":
            return self.save_waveform(self.waveform_filename)
        raise ValueError(_ERROR_STYLE +
            f"Invalid item: {item!r} request to Rigol DS1054Z oscilloscope")

    # -----------------------------
    # Screenshot
    # -----------------------------
    def get_screenshot(self) -> bytes:
        """Return the current screen as raw BMP bytes.

        Returns:
            BMP image bytes (~1,152,054 bytes for the 800x480 24-bit screen).

        Raises:
            ConnectionError: If not connected.

        Example:
            >>> data = scope.get_screenshot()
            >>> data[:2]
            b'BM'
        """
        self._chk()
        return self.instrument.query_binary_values(
            ":DISP:DATA?", datatype="B", container=bytes,
        )

    def save_screenshot(self, filename: Optional[str] = None) -> str:
        """Save the current screen to a BMP file.

        Args:
            filename: Destination path. If omitted, a timestamped name like
                ``DS1054Z_<YYYYmmdd_HHMMSS>.bmp`` is used in the cwd.

        Returns:
            The path written.

        Raises:
            ConnectionError: If not connected.

        Example:
            >>> scope.save_screenshot("captures/run1.bmp")
            'captures/run1.bmp'
        """
        if filename is None:
            filename = f"DS1054Z_{time.strftime('%Y%m%d_%H%M%S')}.bmp"
        if not filename.lower().endswith(".bmp"):
            filename += ".bmp"
        path = Path(filename)
        data = self.get_screenshot()
        self.loading.delay_with_loading_indicator(_DELAY)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if len(data) != _BMP_EXPECTED_BYTES:
            print(_WARNING_STYLE +
                f"screenshot size {len(data)} bytes (expected {_BMP_EXPECTED_BYTES})")
        print(_SUCCESS_STYLE + f"Saved screenshot ({len(data)} bytes) to {path}")
        return str(path)

    def set_screenshot_path(self, filename: str) -> None:
        """Set the default screenshot path used by ``get('SCREENSHOT')``.

        Args:
            filename: Destination path (``.bmp`` extension is added if missing).

        Example:
            >>> scope.set_screenshot_path("captures/shot.bmp")
        """
        self.screenshot_filename = filename

    # -----------------------------
    # Waveform
    # -----------------------------
    def enabled_channels(self) -> List[int]:
        """Return the list of analog channels currently displayed (1..4).

        Returns:
            Channel indices with ``:CHAN<n>:DISP?`` == 1.

        Raises:
            ConnectionError: If not connected.

        Example:
            >>> scope.enabled_channels()
            [1, 2]
        """
        self._chk()
        out: List[int] = []
        for ch in (1, 2, 3, 4):
            if self.query(f":CHAN{ch}:DISP?") in ("1", "ON"):
                out.append(ch)
        return out

    def get_waveform(
        self,
        channel: int = 1,
        raw: bool = False,
    ) -> Tuple[List[float], List[float], dict]:
        """Read one channel and return scaled samples.

        Args:
            channel: Analog channel index (1..4).
            raw: If True, capture the full memory-depth record (the scope is
                stopped during the read and resumed afterwards). If False,
                grab the 1200-pt on-screen NORMal trace.

        Returns:
            Tuple ``(times_s, volts, preamble)`` where ``times_s`` and
            ``volts`` are equal-length lists in seconds and volts, and
            ``preamble`` is the parsed ``:WAV:PRE?`` dict.

        Raises:
            ConnectionError: If not connected.
            ValueError: If ``channel`` is not 1..4.

        Example:
            >>> t, v, pre = scope.get_waveform(channel=1)
            >>> len(v) == pre["points"]
            True
        """
        self._chk()
        if channel not in (1, 2, 3, 4):
            raise ValueError(_ERROR_STYLE +
                f"channel must be 1..4 (got {channel})")

        mode = "RAW" if raw else "NORM"
        was_running = self.query(":TRIG:STAT?") not in ("STOP", "STOP\n")
        if raw and was_running:
            self.write(":STOP")
            self.loading.delay_with_loading_indicator(_DELAY)
        try:
            self.write(":WAV:FORM BYTE")
            self.write(f":WAV:MODE {mode}")
            self.write(f":WAV:SOUR CHAN{channel}")
            pre = self._parse_preamble(self.query(":WAV:PRE?"))
            data = self._read_waveform_bytes(pre["points"], raw=raw)
        finally:
            if raw and was_running:
                self.write(":RUN")

        n = min(len(data), pre["points"])
        xinc, xorig, xref = pre["xinc"], pre["xorig"], pre["xref"]
        yinc, yorig, yref = pre["yinc"], pre["yorig"], pre["yref"]
        times = [(i - xref) * xinc + xorig for i in range(n)]
        volts = [(data[i] - yorig - yref) * yinc for i in range(n)]
        return times, volts, pre

    def save_waveform(
        self,
        filename: Optional[str] = None,
        channels: Optional[Iterable[int]] = None,
        raw: bool = False,
    ) -> str:
        """Save waveform(s) to a CSV.

        Columns are ``time_s, CHAN<n>_V`` for each captured channel. All
        channels share the same scope time base, so the time column is
        shared.

        Args:
            filename: Destination path. If omitted, a timestamped name
                ``DS1054Z_<YYYYmmdd_HHMMSS>.csv`` is used in the cwd.
            channels: Iterable of channel indices. Defaults to whatever is
                currently displayed on the scope.
            raw: If True, capture the full memory-depth record.

        Returns:
            The path written.

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If no channels are enabled / selected.

        Example:
            >>> scope.save_waveform("trace.csv", channels=[1, 2], raw=True)
            'trace.csv'
        """
        if channels is None:
            channels = self.enabled_channels()
        channels = list(channels)
        if not channels:
            raise RuntimeError(_ERROR_STYLE +
                "No channels selected/enabled for waveform capture.")

        if filename is None:
            filename = f"DS1054Z_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        path = Path(filename)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        traces: dict = {}
        time_axis: List[float] = []
        for ch in channels:
            print(_SUCCESS_STYLE +
                f"capturing CHAN{ch} ({'RAW' if raw else 'NORM'})...")
            t, v, _ = self.get_waveform(channel=ch, raw=raw)
            traces[ch] = (t, v)
            if not time_axis:
                time_axis = t

        n_pts = min(len(time_axis), *(len(traces[ch][1]) for ch in channels))
        header = ["time_s"] + [f"CHAN{ch}_V" for ch in channels]
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for i in range(n_pts):
                row = [f"{time_axis[i]:.9e}"]
                for ch in channels:
                    row.append(f"{traces[ch][1][i]:.6e}")
                writer.writerow(row)

        print(_SUCCESS_STYLE +
            f"Saved waveform ({n_pts} pts x {len(channels)} ch) to {path}")
        return str(path)

    def set_waveform_path(self, filename: str) -> None:
        """Set the default waveform CSV path used by ``get('WAVEFORM')``.

        Args:
            filename: Destination path (``.csv`` extension is added if missing).

        Example:
            >>> scope.set_waveform_path("captures/trace.csv")
        """
        self.waveform_filename = filename

    # -----------------------------
    # Private helpers
    # -----------------------------
    def _read_waveform_bytes(self, n_points: int, raw: bool) -> bytes:
        """Read ``n_points`` sample bytes, chunking the RAW transfer if needed."""
        self._chk()
        if not raw:
            return self.instrument.query_binary_values(
                ":WAV:DATA?", datatype="B", container=bytes,
            )
        out = bytearray()
        start = 1
        while start <= n_points:
            stop = min(start + _RAW_CHUNK - 1, n_points)
            self.write(f":WAV:STAR {start}")
            self.write(f":WAV:STOP {stop}")
            chunk = self.instrument.query_binary_values(
                ":WAV:DATA?", datatype="B", container=bytes,
            )
            out.extend(chunk)
            print(f"    {min(stop, n_points)}/{n_points} samples", end="\r")
            start = stop + 1
        print()
        return bytes(out)

    @staticmethod
    def _parse_preamble(pre: str) -> dict:
        """Parse a ``:WAV:PRE?`` response into a typed dict.

        Raises:
            ValueError: If the response does not contain 10 comma-separated
                fields.
        """
        parts = pre.strip().split(",")
        if len(parts) < 10:
            raise ValueError(_ERROR_STYLE +
                f"Unexpected WAV:PRE? response: {pre!r}")
        keys = (
            "format", "type", "points", "count",
            "xinc", "xorig", "xref", "yinc", "yorig", "yref",
        )
        p = dict(zip(keys, parts))
        return {
            "format": int(p["format"]),
            "type":   int(p["type"]),
            "points": int(p["points"]),
            "count":  int(p["count"]),
            "xinc":   float(p["xinc"]),
            "xorig":  float(p["xorig"]),
            "xref":   float(p["xref"]),
            "yinc":   float(p["yinc"]),
            "yorig":  float(p["yorig"]),
            "yref":   float(p["yref"]),
        }


# Convenience entry point for ``python -m lab_drivers.drivers.visa.RigolDS1054Z``.
if __name__ == "__main__":
    with RigolDS1054Z() as scope:
        scope.save_screenshot()
        scope.save_waveform()
