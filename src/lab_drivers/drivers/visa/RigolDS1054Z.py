"""Rigol DS1054Z Digital Oscilloscope Driver.

Pure SCPI / PyVISA driver for the Rigol DS1000Z series (tested on DS1054Z).

Features
--------
- Auto-detection of USB / TCPIP DS1000Z scopes via ``*IDN?`` probing.
- Screen capture as BMP via ``:DISP:DATA?``.
- Waveform readback (NORMal screen data or RAW full-memory) for any enabled
  channel, with correct preamble-based scaling to volts and seconds.
- CSV export of all currently-enabled channels.

Basic Usage
-----------
```python
from lab_drivers.drivers.visa.RigolDS1054Z import RigolDS1054Z

scope = RigolDS1054Z()
scope.save_screenshot("shot.bmp")
scope.save_waveform("trace.csv")              # NORMal mode (1200 pts)
scope.save_waveform("trace_raw.csv", raw=True)  # full memory depth
scope.disconnect()
```
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Iterable, Optional

import pyvisa

# DS1000Z returns a fixed 800x480 24-bit BMP plus header => 1,152,054 bytes.
_BMP_EXPECTED_BYTES = 1_152_054

# DS1000Z caps :WAV:DATA? returns to ~250000 bytes per query in RAW mode.
# 100k is a safe chunk that keeps TMC framing happy.
_RAW_CHUNK = 100_000

_IDN_KEYWORDS = ("DS1054Z", "DS1074Z", "DS1104Z", "DS1Z", "DS1000Z")


class RigolDS1054Z:
    """Rigol DS1054Z (DS1000Z series) oscilloscope driver."""

    # ------------------------------------------------------------------
    # Init / connect / disconnect
    # ------------------------------------------------------------------
    def __init__(
        self,
        auto_connect: bool = True,
        address: Optional[str] = None,
        ip_address: Optional[str] = None,
        timeout_ms: int = 60_000,
    ) -> None:
        self.rm = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status = "Not Connected"
        self.idn: Optional[str] = None
        self._timeout_ms = timeout_ms
        self._address_hint = address
        self._ip_address = ip_address

        if auto_connect:
            self.connect(address=address, ip_address=ip_address)

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
        """
        ip = ip_address or self._ip_address
        if ip and not (address or self._address_hint):
            address = f"TCPIP0::{ip}::inst0::INSTR"

        candidate = address or self._address_hint
        if candidate:
            self._open(candidate, verify_idn=True)
            return

        resources = self.rm.list_resources()
        if not resources:
            raise ConnectionError(
                "No VISA resources found. Is the scope powered on and connected?"
            )

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

        raise ConnectionError(
            f"DS1054Z not found. Available resources: {resources}"
        )

    def _open(self, resource: str, verify_idn: bool) -> None:
        try:
            inst = self.rm.open_resource(resource)
        except pyvisa.VisaIOError as e:
            raise ConnectionError(
                f"Failed to open VISA resource '{resource}': {e}"
            ) from e
        inst.timeout = self._timeout_ms
        inst.chunk_size = 1024 * 1024
        try:
            inst.read_termination = "\n"
        except Exception:
            pass
        idn = inst.query("*IDN?").strip()
        if verify_idn and not any(k in idn.upper() for k in _IDN_KEYWORDS):
            inst.close()
            raise ConnectionError(
                f"Resource '{resource}' is not a DS1000Z (IDN='{idn}')."
            )
        self.instrument = inst
        self.address = resource
        self.idn = idn
        self.status = "Connected"
        print(f"Connected to {idn} at {resource}")

    def disconnect(self) -> None:
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                self.instrument = None
                self.status = "Not Connected"

    def __enter__(self) -> "RigolDS1054Z":
        if self.instrument is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Low-level SCPI passthrough
    # ------------------------------------------------------------------
    def write(self, cmd: str) -> None:
        self._require_connected()
        self.instrument.write(cmd)

    def query(self, cmd: str) -> str:
        self._require_connected()
        return self.instrument.query(cmd).strip()

    def _require_connected(self) -> None:
        if self.instrument is None:
            raise ConnectionError("Not connected to DS1054Z.")

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------
    def get_screenshot(self) -> bytes:
        """Return the current screen as raw BMP bytes."""
        self._require_connected()
        return self.instrument.query_binary_values(
            ":DISP:DATA?", datatype="B", container=bytes
        )

    def save_screenshot(self, filename: Optional[str] = None) -> str:
        """Save the current screen to a BMP file. Returns the path written."""
        if filename is None:
            filename = f"DS1054Z_{time.strftime('%Y%m%d_%H%M%S')}.bmp"
        if not filename.lower().endswith(".bmp"):
            filename += ".bmp"
        path = Path(filename)
        data = self.get_screenshot()
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if len(data) != _BMP_EXPECTED_BYTES:
            print(
                f"Warning: screenshot size {len(data)} bytes "
                f"(expected {_BMP_EXPECTED_BYTES})"
            )
        print(f"Saved screenshot ({len(data)} bytes) to {path}")
        return str(path)

    # ------------------------------------------------------------------
    # Waveform
    # ------------------------------------------------------------------
    def enabled_channels(self) -> list[int]:
        """Return the list of analog channels currently displayed (1..4)."""
        out: list[int] = []
        for ch in (1, 2, 3, 4):
            if self.query(f":CHAN{ch}:DISP?") in ("1", "ON"):
                out.append(ch)
        return out

    def get_waveform(
        self,
        channel: int = 1,
        raw: bool = False,
    ) -> tuple[list[float], list[float], dict]:
        """Return (times_s, volts, preamble) for one channel.

        Args:
            channel: Analog channel index (1..4).
            raw: If True, capture full memory depth (scope is stopped during
                the read and resumed afterwards). Otherwise grab the 1200-pt
                on-screen NORMal trace.
        """
        self._require_connected()
        if channel not in (1, 2, 3, 4):
            raise ValueError(f"channel must be 1..4 (got {channel})")

        mode = "RAW" if raw else "NORM"
        was_running = self.query(":TRIG:STAT?") not in ("STOP", "STOP\n")
        if raw and was_running:
            self.write(":STOP")
            time.sleep(0.2)
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
        """Save waveform(s) to a CSV. Returns the path written.

        Columns are ``time_s, CHAN<n>_V`` for each captured channel. All
        channels are sampled with the same scope time base, so the time
        column is shared.
        """
        if channels is None:
            channels = self.enabled_channels()
        channels = list(channels)
        if not channels:
            raise RuntimeError("No channels selected/enabled for waveform capture.")

        if filename is None:
            filename = f"DS1054Z_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        if not filename.lower().endswith(".csv"):
            filename += ".csv"
        path = Path(filename)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        traces: dict[int, tuple[list[float], list[float]]] = {}
        time_axis: list[float] = []
        for ch in channels:
            print(f"  capturing CHAN{ch} ({'RAW' if raw else 'NORM'})...")
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

        print(f"Saved waveform ({n_pts} pts x {len(channels)} ch) to {path}")
        return str(path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _read_waveform_bytes(self, n_points: int, raw: bool) -> bytes:
        self._require_connected()
        if not raw:
            return self.instrument.query_binary_values(
                ":WAV:DATA?", datatype="B", container=bytes
            )
        out = bytearray()
        start = 1
        while start <= n_points:
            stop = min(start + _RAW_CHUNK - 1, n_points)
            self.write(f":WAV:STAR {start}")
            self.write(f":WAV:STOP {stop}")
            chunk = self.instrument.query_binary_values(
                ":WAV:DATA?", datatype="B", container=bytes
            )
            out.extend(chunk)
            print(f"    {min(stop, n_points)}/{n_points} samples", end="\r")
            start = stop + 1
        print()
        return bytes(out)

    @staticmethod
    def _parse_preamble(pre: str) -> dict:
        parts = pre.strip().split(",")
        if len(parts) < 10:
            raise RuntimeError(f"Unexpected WAV:PRE? response: {pre!r}")
        keys = (
            "format", "type", "points", "count",
            "xinc", "xorig", "xref", "yinc", "yorig", "yref",
        )
        p = dict(zip(keys, parts))
        return {
            "format": int(p["format"]),
            "type": int(p["type"]),
            "points": int(p["points"]),
            "count": int(p["count"]),
            "xinc": float(p["xinc"]),
            "xorig": float(p["xorig"]),
            "xref": float(p["xref"]),
            "yinc": float(p["yinc"]),
            "yorig": float(p["yorig"]),
            "yref": float(p["yref"]),
        }


if __name__ == "__main__":
    with RigolDS1054Z() as scope:
        scope.save_screenshot()
        scope.save_waveform()
