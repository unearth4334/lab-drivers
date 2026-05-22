#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file TektronixMSO4.py
#   @brief Tektronix 4 Series MSO (MSO4) control: connection, waveform, screenshot, metadata.
#   @date 22-May-2026

"""
Tektronix 4 Series MSO (MSO4) Mixed Signal Oscilloscope Driver
==============================================================

VISA-backed driver for the Tektronix 4 Series MSO (model numbers MSO44 /
MSO46 — i.e. instruments whose ``*IDN?`` response identifies as
``TEKTRONIX,MSO4*``). The public API mirrors :class:`KeysightMSOX4154A`
as closely as the differing SCPI dialect allows so that higher-level code
(e.g. ``data_logger``) can be written once and target either scope.

Features
--------
- **Auto-Detection**: Scans USB (Tektronix VID ``0x0699``) and TCPIP INSTR
  resources, matching on ``TEKTRONIX`` + ``MSO4`` in ``*IDN?``.
- **Waveform Capture**: ``WFMOutpre?`` + ``CURVe?`` with ``RIBinary`` /
  ``SRIbinary`` / ``ASCII`` encodings, optional scaling and time axis.
- **Multi-Channel Capture**: Single-trigger batched downloads.
- **Screenshot Capture**: ``HARDCopy STARt`` → raw PNG bytes.
- **Metadata Snapshot**: Per-channel / timebase / trigger / acquisition
  configuration aggregator for archival.
- **Type Hints**: Full type annotations.

Basic Usage
-----------
```python
from lab_drivers.drivers.visa import TektronixMSO4

scope = TektronixMSO4()                       # auto-scan USB + TCPIP
print(scope.get_idn())

wf = scope.get_waveform(channel=1, points=10_000)
t, y, meta = wf["t"], wf["y"], wf["meta"]
print(f"{len(y)} samples @ {meta['sample_rate_hz']:.3g} S/s")

scope.disconnect()
```

Explicit Connection
-------------------
```python
# Connect by bare IP (TCPIP VISA string is built automatically)
scope = TektronixMSO4(ip="192.168.1.100")

# Or pass an explicit VISA resource string
scope = TektronixMSO4(auto_connect=False)
scope.connect("TCPIP0::192.168.1.100::inst0::INSTR")
scope.connect("USB0::0x0699::0x0527::C012345::INSTR")
```

Multi-Channel Waveform Capture
-------------------------------
```python
wfs = scope.get_waveforms([1, 2, 3, 4], points=10_000)
for ch, wf in wfs.items():
    print(f"CH{ch}: {len(wf['y'])} pts, Fs={wf['meta']['sample_rate_hz']:.3g} S/s")

# Non-analog sources (math, ref, digital) via explicit source string
wf = scope.get_waveform(source="MATH1")
wf = scope.get_waveform(source="CH1_D0")        # digital bit 0 of CH1
```

Screenshot Capture
------------------
```python
scope.save_screenshot("mso4_capture.png")
png_bytes = scope.get_screenshot()
```

Metadata Snapshot
-----------------
```python
md = scope.get_metadata()                       # auto-detect displayed channels
print(md["timebase"]["scale_s_per_div"])
print(md["channels"][1]["coupling"])

wf = scope.get_waveform(1, include_config=True) # embed config in returned meta
wf["meta"]["channel_config"]                    # per-channel settings
wf["meta"]["system"]                            # {"timebase", "trigger", "acquisition"}
```

Waveform Return Shape
---------------------
:meth:`get_waveform` returns a dict with three keys:

- ``"t"``: list of time samples in seconds (or ``None`` when
  ``include_time=False``).
- ``"y"``: list of voltage samples (or raw integer codes when
  ``scaled=False`` with a binary encoding).
- ``"meta"``: dict containing the parsed ``WFMOutpre?`` fields plus
  convenience entries: ``source``, ``channel``, ``npoints``, ``dt_s``,
  ``sample_rate_hz``, ``t_start_s``, ``t_stop_s``, ``format``, ``scaled``,
  ``points``, ``yincr`` (= YMUlt), ``yorig`` (= YZEro), ``yref`` (= YOFf),
  ``xincr`` (= XINcr), ``xorig`` (= XZEro), ``xref`` (= PT_OFf).

Supported get() Commands
------------------------
The :meth:`get` dispatcher recognises:

- ``"statistics"`` — list ``[mean, std_dev, min, max]`` computed from a
  fresh waveform.
- ``"voltage"`` / ``"voltage_rms"`` / ``"voltage_pp"`` /
  ``"frequency"`` / ``"period"`` — single MEASUrement values.
- ``"waveform"`` — full waveform dict (``{"t", "y", "meta"}``).
- ``"metadata"`` — :meth:`get_metadata` for the requested channel.
- ``"channel_config"`` / ``"timebase"`` / ``"trigger"`` /
  ``"acquisition"`` — direct config getters.

Channel / Source Strings
------------------------
- Analog: ``"CH1"``–``"CH4"``
- Digital flexchannel: ``"CH<N>_D0"``–``"CH<N>_D7"``
- Math: ``"MATH1"``–``"MATH4"``
- Reference: ``"REF1"``–``"REF4"``
- Bus: ``"B1"``…

Technical Specifications (typical 4 Series MSO)
-----------------------------------------------
- **Analog Channels**: 4 or 6 FlexChannel inputs (200 MHz – 1.5 GHz BW)
- **Digital Channels**: 8 per analog input when a TLP058 logic probe is
  attached
- **Sample Rate**: up to 6.25 GS/s
- **Record Length**: up to 31.25 Mpts
- **Vertical Resolution**: 12-bit ADC

See Also
--------
- KeysightMSOX4154A: Sibling driver with the same public API.
- data_logger: Higher-level orchestrator that uses :meth:`get`.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List

import pyvisa
from colorama import init, Fore, Style


_ERROR_STYLE   = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

# Sentinel returned by Tektronix measurement subsystem for invalid readings.
_TEK_INVALID = 9.91e37


class TektronixMSO4:
    """Tektronix 4 Series MSO (MSO44 / MSO46) oscilloscope driver.

    VISA-backed driver providing connection management, waveform retrieval,
    screenshot capture, and configuration-metadata snapshots. The public
    method surface mirrors :class:`KeysightMSOX4154A` so that downstream
    code can target either instrument interchangeably.
    """

    def __init__(self,
                 auto_connect: bool = True,
                 ip: Optional[str] = None,
                 timeout_ms: int = 20000,
                 chunk_size: int = 102_400):
        init(autoreset=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status: str = "Not Connected"
        self._timeout_ms = timeout_ms
        self._chunk_size = chunk_size
        self._ip = ip
        # Number of analog channels detected on the connected mainframe (4 or 6).
        # Populated lazily on first config query.
        self._n_analog: Optional[int] = None
        if auto_connect:
            self._auto_connect()

    # ---------- Connect / Disconnect ----------
    @staticmethod
    def _matches_idn(idn: str) -> bool:
        u = idn.upper()
        return "TEKTRONIX" in u and "MSO4" in u

    def _configure_instrument(self, inst: pyvisa.resources.MessageBasedResource) -> None:
        inst.timeout = self._timeout_ms
        inst.chunk_size = self._chunk_size
        inst.write_termination = "\n"
        # Binary block responses include trailing newline; leave read_termination None
        # so query_binary_values can consume the full block.
        inst.read_termination = None
        try:
            # Disable verbose command echo in responses so query() returns just the value.
            inst.write("HEADer OFF")
            inst.write("VERBose OFF")
        except Exception:
            pass

    def _auto_connect(self) -> None:
        """Scan USB (Tektronix VID 0x0699) and TCPIP INSTR resources for an MSO4."""
        if self._ip:
            self.connect(ip=self._ip)
            return
        try:
            resources = self.rm.list_resources()
            for resource in resources:
                is_usb_tek = "0x0699" in resource and "INSTR" in resource
                is_tcpip = resource.upper().startswith("TCPIP") and "INSTR" in resource
                if not (is_usb_tek or is_tcpip):
                    continue
                inst = None
                try:
                    inst = self.rm.open_resource(resource)
                    inst.timeout = self._timeout_ms
                    idn = inst.query("*IDN?").strip()
                    if self._matches_idn(idn):
                        self._configure_instrument(inst)
                        self.instrument = inst
                        self.address = resource
                        self.status = "Connected"
                        print(_SUCCESS_STYLE + f"Auto-connected to Tektronix MSO4 at {resource}")
                        return
                    else:
                        inst.close()
                except Exception:
                    try:
                        if inst is not None:
                            inst.close()
                    except Exception:
                        pass
                    continue
            raise ConnectionError("No Tektronix 4 Series MSO found")
        except Exception as e:
            print(_ERROR_STYLE + f"Auto-connect failed: {e}")
            raise

    def connect(self, address: Optional[str] = None, ip: Optional[str] = None) -> None:
        """Connect to oscilloscope.

        Accepts a VISA resource string (``address``), a bare IP address
        (``ip``, which is wrapped into ``TCPIP0::<ip>::inst0::INSTR``), or
        neither — in which case USB / TCPIP resources are scanned
        automatically.
        """
        if ip and address is None:
            address = f"TCPIP0::{ip}::inst0::INSTR"
        if address is not None:
            if "::INSTR" not in address:
                raise ValueError(_ERROR_STYLE + f"Not a VISA INSTR address: {address}")
            try:
                inst = self.rm.open_resource(address)
                self._configure_instrument(inst)
                self.instrument = inst
                self.address = address
                self.status = "Connected"
                print(_SUCCESS_STYLE + f"Connected to Tektronix MSO4 Oscilloscope at {self.address}")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE + f"Failed to open {address}: {e}")
        else:
            self._auto_connect()

    def disconnect(self) -> None:
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from Tektronix MSO4 Oscilloscope at {self.address}")
                self.instrument = None
                self.status = "Not Connected"
                self.address = None

    # ---------- Generic SCPI passthrough ----------
    def write(self, scpi: str) -> None:
        """Write a SCPI command to the instrument."""
        self._chk()
        self.instrument.write(scpi)  # type: ignore

    def query(self, scpi: str) -> str:
        """Send a SCPI query and return the stripped response."""
        self._chk()
        return self.instrument.query(scpi).strip()  # type: ignore

    # ---------- Helpers ----------
    def _chk(self) -> None:
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected.")

    def get_idn(self) -> str:
        """Return the ``*IDN?`` response string."""
        self._chk()
        return self.instrument.query("*IDN?").strip()  # type: ignore

    def is_running(self) -> bool:
        """Return ``True`` if the acquisition state is RUN."""
        self._chk()
        try:
            return bool(int(self.instrument.query("ACQuire:STATE?").strip()))  # type: ignore
        except Exception:
            return False

    def stop(self) -> None:
        """Issue ``ACQuire:STATE STOP``."""
        self._chk()
        try:
            self.instrument.write("ACQuire:STATE STOP")  # type: ignore
        except Exception:
            pass

    def run(self) -> None:
        """Issue ``ACQuire:STATE RUN``."""
        self._chk()
        try:
            self.instrument.write("ACQuire:STATE RUN")  # type: ignore
            print(_SUCCESS_STYLE + "Oscilloscope acquisition started")
        except Exception:
            pass

    def _q(self, scpi: str) -> Optional[str]:
        """Query SCPI and return stripped string, or ``None`` on failure."""
        self._chk()
        try:
            return self.instrument.query(scpi).strip()  # type: ignore
        except Exception:
            return None

    def _qf(self, scpi: str) -> Optional[float]:
        """Query SCPI and return ``float``, or ``None`` on failure."""
        s = self._q(scpi)
        if s is None:
            return None
        try:
            return float(s)
        except (TypeError, ValueError):
            return None

    def _qbool(self, scpi: str) -> Optional[bool]:
        """Query SCPI and return ``bool``, or ``None`` on failure.

        Recognises ``"1"`` / ``"0"``, ``"ON"`` / ``"OFF"``, ``"TRUE"`` /
        ``"FALSE"``, and ``"RUN"`` / ``"STOP"`` (the last for
        ``ACQuire:STATE?`` on certain firmware revisions).
        """
        s = self._q(scpi)
        if s is None:
            return None
        u = s.upper()
        if u in ("1", "ON", "TRUE", "RUN"):
            return True
        if u in ("0", "OFF", "FALSE", "STOP", "READY"):
            return False
        try:
            return bool(int(float(u)))
        except (TypeError, ValueError):
            return None

    def _detect_n_analog(self) -> int:
        """Return the number of analog input channels on the connected scope.

        Probes ``CH<N>:SCAle?`` for ``N`` = 5 and 6 to distinguish MSO44
        (4 analog) from MSO46 (6 analog). Falls back to 4 if probing fails.
        Result is cached on the instance.
        """
        if self._n_analog is not None:
            return self._n_analog
        n = 4
        for probe in (6, 5):
            if self._qf(f"CH{probe}:SCAle?") is not None:
                n = probe
                break
        self._n_analog = n
        return n

    # ---------- Configuration / Metadata ----------
    def get_channel_config(self, channel: int) -> Dict[str, Any]:
        """Return the full configuration of a single analog channel.

        Issues a sequence of ``CH<N>:…?`` queries (plus
        ``DISplay:GLObal:CH<N>:STATE?`` for the on-screen visibility flag)
        and packs the results into a typed dictionary suitable for
        recording alongside a waveform or screenshot. Any individual
        query that the instrument rejects is reported as ``None`` rather
        than raising.

        Args:
            channel: Analog channel index. Must be in 1-4 for MSO44 or
                1-6 for MSO46. The valid upper bound is detected on
                first use via :meth:`_detect_n_analog`.

        Returns:
            Dictionary with the following keys (values may be ``None`` if
            the instrument does not support a particular query):

            - ``"channel"``: ``int`` — the queried channel number.
            - ``"source"``: ``str`` — canonical source name (``"CH1"`` …).
            - ``"display"``: ``bool`` — whether the trace is visible.
            - ``"coupling"``: ``str`` — ``"AC"``, ``"DC"`` or ``"DCREJ"``.
            - ``"impedance"``: ``str`` — ``"FIFty"`` (50 Ω) or
              ``"MEG"`` (1 MΩ) as reported by ``CH<N>:TERmination?``.
            - ``"bw_limit_hz"``: ``float`` — currently selected analog
              bandwidth in hertz (``CH<N>:BANdwidth?``).
            - ``"invert"``: ``bool`` — trace inversion on/off.
            - ``"scale_v_per_div"``: ``float`` — vertical scale, V/div.
            - ``"offset_v"``: ``float`` — vertical offset, volts.
            - ``"position_div"``: ``float`` — vertical position, divisions.
            - ``"probe_gain"``: ``float`` — probe gain (= 1 / attenuation).
            - ``"probe_attenuation"``: ``float`` — convenience reciprocal of
              ``probe_gain`` (``None`` if gain is unknown or zero).
            - ``"probe_skew_s"``: ``float`` — per-channel deskew, seconds.
            - ``"units"``: ``str`` — vertical units string
              (``CH<N>:PRObe:UNIts?``, typically ``"V"``).
            - ``"label"``: ``str`` — user-assigned channel label.

        Raises:
            ConnectionError: If the driver is not connected.
            ValueError: If ``channel`` is out of range.

        Example:
            >>> scope = TektronixMSO4()
            >>> cfg = scope.get_channel_config(1)
            >>> cfg["scale_v_per_div"], cfg["coupling"]
            (0.5, 'DC')
        """
        n_max = self._detect_n_analog()
        if not isinstance(channel, int) or not (1 <= channel <= n_max):
            raise ValueError(_ERROR_STYLE + f"channel must be int 1-{n_max}, got {channel!r}")
        n = channel
        label = self._q(f"CH{n}:LABel:NAMe?")
        if label is not None:
            label = label.strip().strip('"')
        probe_gain = self._qf(f"CH{n}:PRObe:GAIN?")
        probe_atten: Optional[float] = None
        if probe_gain is not None and probe_gain != 0.0:
            probe_atten = 1.0 / probe_gain
        return {
            "channel":            n,
            "source":             f"CH{n}",
            "display":            self._qbool(f"DISplay:GLObal:CH{n}:STATE?"),
            "coupling":           self._q(f"CH{n}:COUPling?"),
            "impedance":          self._q(f"CH{n}:TERmination?"),
            "bw_limit_hz":        self._qf(f"CH{n}:BANdwidth?"),
            "invert":             self._qbool(f"CH{n}:INVert?"),
            "scale_v_per_div":    self._qf(f"CH{n}:SCAle?"),
            "offset_v":           self._qf(f"CH{n}:OFFSet?"),
            "position_div":       self._qf(f"CH{n}:POSition?"),
            "probe_gain":         probe_gain,
            "probe_attenuation":  probe_atten,
            "probe_skew_s":       self._qf(f"CH{n}:DESKew?"),
            "units":              self._q(f"CH{n}:PRObe:UNIts?"),
            "label":              label,
        }

    def get_timebase_config(self) -> Dict[str, Any]:
        """Return the current horizontal (timebase) configuration.

        Returns:
            Dictionary with keys (values may be ``None`` on unsupported
            queries):

            - ``"scale_s_per_div"``: ``float`` — horizontal scale, s/div
              (``HORizontal:SCAle?``).
            - ``"position_pct"``: ``float`` — horizontal position as a
              percentage 0-100 (``HORizontal:POSition?``).
            - ``"range_s"``: ``float`` — full-screen time span (10 ×
              scale, computed locally for cross-vendor parity).
            - ``"sample_rate_hz"``: ``float`` — current sample rate
              (``HORizontal:SAMPLERate?``).
            - ``"record_length"``: ``int`` — number of points in the
              acquisition record (``HORizontal:RECOrdlength?``).
            - ``"mode"``: ``str`` — ``"AUTO"`` or ``"MANual"``
              (``HORizontal:MODE?``).

        Raises:
            ConnectionError: If the driver is not connected.

        Example:
            >>> scope = TektronixMSO4()
            >>> scope.get_timebase_config()["scale_s_per_div"]
            1e-06
        """
        scale = self._qf("HORizontal:SCAle?")
        rec = self._qf("HORizontal:RECOrdlength?")
        return {
            "scale_s_per_div": scale,
            "position_pct":    self._qf("HORizontal:POSition?"),
            "range_s":         (scale * 10.0) if scale is not None else None,
            "sample_rate_hz":  self._qf("HORizontal:SAMPLERate?"),
            "record_length":   int(rec) if rec is not None else None,
            "mode":            self._q("HORizontal:MODE?"),
        }

    def get_trigger_config(self) -> Dict[str, Any]:
        """Return the current A-trigger configuration.

        Covers the common Edge-trigger fields (the default and most
        common trigger mode on the 4 Series MSO). For non-edge types,
        ``type`` reflects the actual setting and the edge-specific
        fields fall back to ``None`` when the instrument rejects them.

        Returns:
            Dictionary with keys (values may be ``None`` on unsupported
            queries):

            - ``"type"``: ``str`` — ``"EDGE"``, ``"PULSE"``, ``"LOGIc"``,
              etc. (``TRIGger:A:TYPE?``).
            - ``"mode"``: ``str`` — ``"AUTO"`` or ``"NORMal"``
              (``TRIGger:A:MODe?``).
            - ``"holdoff_s"``: ``float`` — trigger holdoff, seconds
              (``TRIGger:A:HOLDoff:TIMe?``).
            - ``"level_v"``: ``float`` — global trigger level, volts
              (``TRIGger:A:LEVel?``).
            - ``"source"``: ``str`` — edge-trigger source (e.g. ``"CH1"``)
              (``TRIGger:A:EDGE:SOUrce?``).
            - ``"slope"``: ``str`` — ``"RISE"``, ``"FALL"`` or ``"EITHer"``
              (``TRIGger:A:EDGE:SLOpe?``).
            - ``"coupling"``: ``str`` — edge-trigger coupling
              (``TRIGger:A:EDGE:COUPling?``).
            - ``"stop_after"``: ``str`` — ``"RUNSTop"`` or ``"SEQuence"``
              (``ACQuire:STOPAfter?``).

        Raises:
            ConnectionError: If the driver is not connected.

        Example:
            >>> scope = TektronixMSO4()
            >>> trig = scope.get_trigger_config()
            >>> trig["type"], trig["source"], trig["level_v"]
            ('EDGE', 'CH1', 1.5)
        """
        return {
            "type":       self._q("TRIGger:A:TYPE?"),
            "mode":       self._q("TRIGger:A:MODe?"),
            "holdoff_s":  self._qf("TRIGger:A:HOLDoff:TIMe?"),
            "level_v":    self._qf("TRIGger:A:LEVel?"),
            "source":     self._q("TRIGger:A:EDGE:SOUrce?"),
            "slope":      self._q("TRIGger:A:EDGE:SLOpe?"),
            "coupling":   self._q("TRIGger:A:EDGE:COUPling?"),
            "stop_after": self._q("ACQuire:STOPAfter?"),
        }

    def get_acquisition_config(self) -> Dict[str, Any]:
        """Return the current acquisition configuration.

        Returns:
            Dictionary with keys (values may be ``None`` on unsupported
            queries):

            - ``"mode"``: ``str`` — ``"SAMple"``, ``"AVErage"``,
              ``"HIRes"``, ``"PEAKdetect"``, ``"ENVelope"``
              (``ACQuire:MODe?``).
            - ``"num_averages"``: ``int`` — averaging count
              (``ACQuire:NUMAVg?``).
            - ``"num_acquisitions"``: ``int`` — completed acquisition
              counter (``ACQuire:NUMACq?``).
            - ``"fast_acq"``: ``bool`` — FastAcq state if supported
              (``ACQuire:FASTAcq:STATE?``).
            - ``"sample_rate_hz"``: ``float`` — current sample rate.
            - ``"points"``: ``int`` — record length.
            - ``"running"``: ``bool`` — whether acquisition is armed.

        Raises:
            ConnectionError: If the driver is not connected.

        Example:
            >>> scope = TektronixMSO4()
            >>> acq = scope.get_acquisition_config()
            >>> acq["mode"], acq["sample_rate_hz"]
            ('SAMPLE', 6.25e9)
        """
        navg = self._qf("ACQuire:NUMAVg?")
        nacq = self._qf("ACQuire:NUMACq?")
        rec = self._qf("HORizontal:RECOrdlength?")
        return {
            "mode":             self._q("ACQuire:MODe?"),
            "num_averages":     int(navg) if navg is not None else None,
            "num_acquisitions": int(nacq) if nacq is not None else None,
            "fast_acq":         self._qbool("ACQuire:FASTAcq:STATE?"),
            "sample_rate_hz":   self._qf("HORizontal:SAMPLERate?"),
            "points":           int(rec) if rec is not None else None,
            "running":          self._qbool("ACQuire:STATE?"),
        }

    def get_metadata(self, channels: Optional[List[int]] = None) -> Dict[str, Any]:
        """Return a comprehensive snapshot of instrument state for archival.

        Aggregates the per-channel, timebase, trigger, and acquisition
        configurations into a single dictionary intended to be saved
        alongside a captured waveform or screenshot for later analysis.
        Also includes the instrument ``*IDN?`` string, the VISA address,
        and a UTC ISO-8601 timestamp.

        Args:
            channels: List of analog channels to include. When ``None``
                (default), only channels whose
                ``DISplay:GLObal:CH<N>:STATE?`` query returns true are
                included. Pass an explicit list (e.g. ``[1, 2, 3, 4]``)
                to snapshot every analog input unconditionally.

        Returns:
            Dictionary with the following structure::

                {
                    "idn": str,                 # *IDN? response
                    "address": str | None,      # VISA resource string
                    "timestamp_iso": str,       # UTC ISO-8601
                    "timebase":    {...},       # see get_timebase_config()
                    "trigger":     {...},       # see get_trigger_config()
                    "acquisition": {...},       # see get_acquisition_config()
                    "channels":    {1: {...}},  # see get_channel_config()
                }

        Raises:
            ConnectionError: If the driver is not connected.

        Example:
            >>> scope = TektronixMSO4()
            >>> meta = scope.get_metadata()
            >>> sorted(meta.keys())
            ['acquisition', 'address', 'channels', 'idn', 'timebase',
             'timestamp_iso', 'trigger']
        """
        self._chk()
        from datetime import datetime, timezone

        n_max = self._detect_n_analog()
        if channels is None:
            wanted: List[int] = []
            for n in range(1, n_max + 1):
                if self._qbool(f"DISplay:GLObal:CH{n}:STATE?"):
                    wanted.append(n)
        else:
            wanted = [int(c) for c in channels]
            for n in wanted:
                if not (1 <= n <= n_max):
                    raise ValueError(_ERROR_STYLE + f"channel must be int 1-{n_max}, got {n!r}")

        return {
            "idn":           self.get_idn(),
            "address":       self.address,
            "timestamp_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timebase":      self.get_timebase_config(),
            "trigger":       self.get_trigger_config(),
            "acquisition":   self.get_acquisition_config(),
            "channels":      {n: self.get_channel_config(n) for n in wanted},
        }

    # ---------- Screenshot ----------
    def get_screenshot(self, inksaver: bool = False) -> bytes:
        """Retrieve the oscilloscope screen capture as raw PNG bytes.

        Uses the ``SAVe:IMAGe:FILEFormat PNG`` + ``HARDCopy STARt``
        sequence: the instrument returns the rendered PNG as an IEEE
        488.2 binary block on the next read.

        Args:
            inksaver: When ``True``, sets ``HARDCopy:INKSaver ON`` before
                capturing (inverts the background colour for printing).

        Returns:
            Raw PNG image data as a ``bytes`` object.

        Raises:
            ConnectionError: If the driver is not connected.
            RuntimeError: If the VISA transfer fails.

        Example:
            >>> scope = TektronixMSO4()
            >>> png = scope.get_screenshot()
            >>> open("screen.png", "wb").write(png)
        """
        self._chk()
        inst = self.instrument  # type: ignore
        try:
            inst.write("SAVe:IMAGe:FILEFormat PNG")
            inst.write(f"HARDCopy:INKSaver {'ON' if inksaver else 'OFF'}")
            data = inst.query_binary_values(
                "HARDCopy STARt",
                datatype='B',
                is_big_endian=True,
                container=bytearray,
                chunk_size=self._chunk_size,
                delay=0,
            )
            return bytes(data)
        except pyvisa.errors.VisaIOError as e:
            raise RuntimeError(_ERROR_STYLE + f"Screenshot failed: {e}")
        except Exception as e:
            raise RuntimeError(_ERROR_STYLE + f"Screenshot failed: {e}")

    def save_screenshot(self, filename: str, inksaver: bool = False) -> bool:
        """Capture the oscilloscope screen and save it to a PNG file.

        Args:
            filename: Destination file path. Use a ``.png`` extension for
                a valid PNG image.
            inksaver: Forwarded to :meth:`get_screenshot`.

        Returns:
            ``True`` if the screenshot was written successfully, ``False``
            if any exception occurred (the exception is printed but not
            raised).

        Raises:
            ConnectionError: If the driver is not connected.
        """
        try:
            data = self.get_screenshot(inksaver=inksaver)
            with open(filename, "wb") as f:
                f.write(data)
            print(_SUCCESS_STYLE + f"Screenshot saved: {filename}")
            return True
        except Exception as e:
            print(_ERROR_STYLE + f"Screenshot failed: {e}")
            return False

    # ---------- Waveform ----------
    def _read_preamble(self) -> Dict[str, Any]:
        """Parse ``WFMOutpre?`` field-by-field and return a normalised dict.

        The 4 Series MSO ``WFMOutpre`` query returns a comma-separated
        record describing the next ``CURVe?`` payload. Rather than rely
        on positional ordering (which varies by firmware and active
        encoding), this helper issues one query per field. The returned
        dict uses the same naming scheme as :class:`KeysightMSOX4154A`'s
        preamble parser (``xincr``, ``xorig``, ``xref``, ``yincr``,
        ``yorig``, ``yref``, ``points``) so cross-vendor code can share
        post-processing.

        Returns:
            Dictionary with at least the keys listed above plus the raw
            Tek fields (``BYT_Nr``, ``BIT_Nr``, ``ENCdg``, ``BN_Fmt``,
            ``BYT_Or``, ``XUNit``, ``YUNit``).

        Raises:
            ConnectionError: If the driver is not connected.
            RuntimeError: If any required field cannot be parsed.
        """
        self._chk()
        inst = self.instrument  # type: ignore
        try:
            return {
                "format":   inst.query("WFMOutpre:ENCdg?").strip(),
                "type":     inst.query("WFMOutpre:BN_Fmt?").strip(),
                "byte_order": inst.query("WFMOutpre:BYT_Or?").strip(),
                "bytes_per_pt": int(float(inst.query("WFMOutpre:BYT_Nr?").strip())),
                "bits_per_pt":  int(float(inst.query("WFMOutpre:BIT_Nr?").strip())),
                "points":   int(float(inst.query("WFMOutpre:NR_Pt?").strip())),
                "xincr":    float(inst.query("WFMOutpre:XINcr?").strip()),
                "xorig":    float(inst.query("WFMOutpre:XZEro?").strip()),
                "xref":     float(inst.query("WFMOutpre:PT_OFf?").strip()),
                "xunit":    inst.query("WFMOutpre:XUNit?").strip().strip('"'),
                "yincr":    float(inst.query("WFMOutpre:YMUlt?").strip()),
                "yorig":    float(inst.query("WFMOutpre:YZEro?").strip()),
                "yref":     float(inst.query("WFMOutpre:YOFf?").strip()),
                "yunit":    inst.query("WFMOutpre:YUNit?").strip().strip('"'),
            }
        except Exception as e:
            raise RuntimeError(_ERROR_STYLE + f"Failed to read WFMOutpre: {e}")

    def get_waveform(self,
                     channel: Optional[int] = None,
                     *,
                     source: Optional[str] = None,
                     points: Optional[int] = None,
                     points_mode: str = "RAW",
                     fmt: str = "BYTE",
                     include_time: bool = True,
                     scaled: bool = True,
                     include_config: bool = False,
                     stop_during_read: bool = False,
                     debug: bool = False,
                     ) -> Dict[str, Any]:
        """Download a waveform from the oscilloscope and return it as a dict.

        Accepts either an integer ``channel`` (1-4 / 1-6 depending on
        mainframe) or an explicit ``source`` string (e.g. ``"CH1"``,
        ``"MATH1"``, ``"REF2"``, ``"CH1_D0"``). Exactly one of the two
        must be provided. Supports ``BYTE`` / ``WORD`` / ``ASCII``
        encodings (mapped onto Tek's ``SRIbinary`` / ``ASCIi`` settings)
        and lets callers opt out of time-axis generation or scaling.

        Args:
            channel: Analog channel index. Mutually exclusive with
                ``source``. Defaults to channel 1 if neither is given.
            source: Explicit waveform source string. Use for non-analog
                sources such as ``"MATH1"`` or ``"CH1_D0"``.
            points: Optional record-length window. If ``None``, the
                instrument's currently configured record length is used.
                Otherwise the helper sets ``DATa:START 1`` and
                ``DATa:STOP <points>``.
            points_mode: Accepted for cross-vendor API parity; on the
                4 Series MSO there is no equivalent of Keysight's
                ``POINts:MODE``, so this argument is currently ignored.
            fmt: Waveform transfer format. One of ``"BYTE"`` (8-bit
                signed binary, default and fastest), ``"WORD"`` (16-bit
                signed binary), or ``"ASCII"`` (comma-separated scaled
                floats).
            include_time: When ``True``, generate and return a time axis
                computed from the preamble. When ``False``, ``"t"`` is
                ``None`` (skip generation for large captures).
            scaled: When ``True`` (binary formats only), convert raw
                codes to physical units using the preamble. When
                ``False``, return raw integer codes. Ignored for ASCII
                format (already scaled).
            include_config: When ``True``, attach instrument-state
                metadata to the returned ``meta`` dict:
                ``meta["channel_config"]`` (for analog sources only) and
                ``meta["system"] = {"timebase", "trigger", "acquisition"}``.
            stop_during_read: When ``True``, issue ``ACQuire:STATE STOP``
                before reading and restore the prior run state after.
            debug: When ``True``, print a one-line summary of the transfer.

        Returns:
            Dictionary with keys:

            - ``"t"``: ``list[float]`` time samples in seconds, or
              ``None`` when ``include_time=False``.
            - ``"y"``: ``list[float]`` voltage samples (or raw codes if
              ``scaled=False`` with a binary format).
            - ``"meta"``: ``dict`` containing the parsed preamble plus
              ``source``, ``channel``, ``npoints``, ``dt_s``,
              ``sample_rate_hz``, ``t_start_s``, ``t_stop_s``,
              ``format``, ``scaled``.

        Raises:
            ConnectionError: If the driver is not connected.
            ValueError: If both ``channel`` and ``source`` are given, if
                ``channel`` is out of range, or if ``fmt`` is unknown.
            RuntimeError: If the instrument returns an unparseable
                preamble or the VISA transfer fails.

        Example:
            >>> scope = TektronixMSO4()
            >>> wf = scope.get_waveform(1, points=10_000)
            >>> len(wf["y"]), wf["meta"]["sample_rate_hz"]
            (10000, 6.25e9)
        """
        self._chk()
        _ = points_mode  # accepted for API parity, no MSO4 equivalent

        # Resolve source
        if channel is not None and source is not None:
            raise ValueError(_ERROR_STYLE + "pass either channel or source, not both")
        if source is None:
            ch = 1 if channel is None else channel
            n_max = self._detect_n_analog()
            if not isinstance(ch, int) or not (1 <= ch <= n_max):
                raise ValueError(_ERROR_STYLE + f"channel must be int 1-{n_max}, got {channel!r}")
            resolved_source = f"CH{ch}"
            resolved_channel: Optional[int] = ch
        else:
            resolved_source = source
            resolved_channel = None

        fmt_upper = fmt.upper()
        if fmt_upper == "ASC":
            fmt_upper = "ASCII"
        if fmt_upper not in ("BYTE", "WORD", "ASCII"):
            raise ValueError(_ERROR_STYLE + f"fmt must be BYTE, WORD, or ASCII; got {fmt!r}")

        inst = self.instrument  # type: ignore

        was_running = self.is_running() if stop_during_read else False
        try:
            if stop_during_read and was_running:
                self.stop()

            # Configure transfer
            inst.write(f"DATa:SOUrce {resolved_source}")
            if fmt_upper == "ASCII":
                inst.write("DATa:ENCdg ASCIi")
            else:
                inst.write("DATa:ENCdg SRIbinary")  # signed integer, LSB first
                inst.write(f"DATa:WIDth {1 if fmt_upper == 'BYTE' else 2}")

            # Record window
            rec = self._qf("HORizontal:RECOrdlength?")
            stop_idx = int(rec) if rec is not None else 0
            if points is not None:
                stop_idx = int(points)
            inst.write("DATa:STARt 1")
            if stop_idx > 0:
                inst.write(f"DATa:STOP {stop_idx}")

            meta = self._read_preamble()

            # Fetch data
            if fmt_upper == "BYTE":
                raw = inst.query_binary_values("CURVe?",
                                               datatype='b',
                                               is_big_endian=False,
                                               container=list,
                                               chunk_size=self._chunk_size)
            elif fmt_upper == "WORD":
                raw = inst.query_binary_values("CURVe?",
                                               datatype='h',
                                               is_big_endian=False,
                                               container=list,
                                               chunk_size=self._chunk_size)
            else:  # ASCII
                resp = inst.query("CURVe?").strip()
                raw = [float(v) for v in resp.split(",") if v.strip()]
        finally:
            if stop_during_read and was_running:
                self.run()

        n = len(raw)

        # Scale (binary only; ASCII is already in physical units)
        if fmt_upper in ("BYTE", "WORD") and scaled:
            yref = meta["yref"]
            yincr = meta["yincr"]
            yorig = meta["yorig"]
            y: List[float] = [((v - yref) * yincr) + yorig for v in raw]
        else:
            y = list(raw)

        xincr = meta["xincr"]
        xorig = meta["xorig"]
        xref = meta["xref"]
        sample_rate = (1.0 / xincr) if xincr and xincr > 0 else float("nan")
        # Tek time axis: t[i] = xorig + (i - xref) * xincr
        if include_time:
            t: Optional[List[float]] = [xorig + (i - xref) * xincr for i in range(n)]
            t_start = t[0] if n else None
            t_stop = t[-1] if n else None
        else:
            t = None
            t_start = xorig - xref * xincr if n else None
            t_stop = xorig + (n - 1 - xref) * xincr if n else None

        if debug:
            print(f"[{resolved_source}] points={n}, xincr={xincr} s, Fs={sample_rate} Hz")

        meta.update({
            "source": resolved_source,
            "channel": resolved_channel,
            "format": fmt_upper,
            "scaled": bool(scaled) if fmt_upper in ("BYTE", "WORD") else True,
            "npoints": n,
            "dt_s": xincr,
            "sample_rate_hz": sample_rate,
            "t_start_s": t_start,
            "t_stop_s": t_stop,
        })
        if include_config:
            if resolved_channel is not None:
                meta["channel_config"] = self.get_channel_config(resolved_channel)
            meta["system"] = {
                "timebase":    self.get_timebase_config(),
                "trigger":     self.get_trigger_config(),
                "acquisition": self.get_acquisition_config(),
            }
        return {"t": t, "y": y, "meta": meta}

    def get_waveforms(self,
                      channels: List[int],
                      *,
                      points: Optional[int] = None,
                      points_mode: str = "RAW",
                      fmt: str = "BYTE",
                      include_time: bool = True,
                      scaled: bool = True,
                      include_config: bool = False,
                      stop_during_read: bool = True,
                      ) -> Dict[int, Dict[str, Any]]:
        """Download waveforms from multiple analog channels in a single batch.

        Stops the acquisition (when ``stop_during_read=True`` and the
        scope is currently running) so all returned channels are
        captured from the same trigger event, then restores the prior
        run state.

        Args:
            channels: Iterable of analog channel indices.
            points: Forwarded to :meth:`get_waveform`.
            points_mode: Accepted for API parity; ignored on MSO4.
            fmt: Forwarded to :meth:`get_waveform`.
            include_time: Forwarded to :meth:`get_waveform`.
            scaled: Forwarded to :meth:`get_waveform`.
            include_config: Forwarded to :meth:`get_waveform`.
            stop_during_read: When ``True``, stop acquisition for the
                duration of the batch.

        Returns:
            Dictionary keyed by channel index, mapping each to the dict
            returned by :meth:`get_waveform`.

        Raises:
            ConnectionError: If the driver is not connected.
            ValueError: If any channel is out of range or ``fmt`` is
                unknown.
        """
        self._chk()
        was_running = self.is_running() if stop_during_read else False
        try:
            if stop_during_read and was_running:
                self.stop()
            return {
                int(ch): self.get_waveform(
                    int(ch),
                    points=points,
                    points_mode=points_mode,
                    fmt=fmt,
                    include_time=include_time,
                    scaled=scaled,
                    include_config=include_config,
                    stop_during_read=False,
                )
                for ch in channels
            }
        finally:
            if stop_during_read and was_running:
                self.run()

    # ---------- Measurements ----------
    def get_measurement(self, parameter: str, channel: Optional[str] = None) -> float:
        """Read a single measurement value via the IMMed subsystem.

        Uses ``MEASUrement:IMMed:TYPe <parameter>`` +
        ``MEASUrement:IMMed:SOUrce1 <channel>`` +
        ``MEASUrement:IMMed:VALue?``. Returns ``nan`` if the instrument
        reports an invalid measurement (``9.91e37``) or the query fails.

        Args:
            parameter: Tek measurement type. Common values:
                ``"FREQuency"``, ``"PERIod"``, ``"PK2PK"``,
                ``"AMPLITUDE"``, ``"MEAN"``, ``"RMS"``, ``"MAXimum"``,
                ``"MINImum"``, ``"RISETIME"``, ``"FALLTIME"``,
                ``"PWIDTH"``, ``"NWIDTH"``, ``"DUTYCYCLE"``.
            channel: Source channel string (e.g. ``"CH1"``). If
                ``None``, the current ``MEASUrement:IMMed:SOUrce1``
                setting is used.

        Returns:
            Measurement value as a ``float``, or ``nan`` on failure.

        Raises:
            ConnectionError: If the driver is not connected.
        """
        self._chk()
        inst = self.instrument  # type: ignore
        try:
            if channel is not None:
                inst.write(f"MEASUrement:IMMed:SOUrce1 {channel}")
            inst.write(f"MEASUrement:IMMed:TYPe {parameter}")
            result = inst.query("MEASUrement:IMMed:VALue?").strip()
            value = float(result)
            if abs(value) >= _TEK_INVALID:
                return float("nan")
            return value
        except Exception as e:
            print(_ERROR_STYLE + f"Measurement {parameter} failed: {e}")
            return float("nan")

    def measure_frequency(self, channel: int = 1) -> float:
        """Convenience wrapper: signal frequency in Hz on ``CH<channel>``."""
        return self.get_measurement("FREQuency", f"CH{int(channel)}")

    def measure_period(self, channel: int = 1) -> float:
        """Convenience wrapper: signal period in seconds on ``CH<channel>``."""
        return self.get_measurement("PERIod", f"CH{int(channel)}")

    def measure_vpp(self, channel: int = 1) -> float:
        """Convenience wrapper: peak-to-peak voltage on ``CH<channel>``."""
        return self.get_measurement("PK2PK", f"CH{int(channel)}")

    def measure_vrms(self, channel: int = 1) -> float:
        """Convenience wrapper: RMS voltage on ``CH<channel>``."""
        return self.get_measurement("RMS", f"CH{int(channel)}")

    def measure_mean(self, channel: int = 1) -> float:
        """Convenience wrapper: mean voltage on ``CH<channel>``."""
        return self.get_measurement("MEAN", f"CH{int(channel)}")

    def get_statistics(self, channel: str = "CH1") -> Dict[str, Any]:
        """Compute basic statistics from a freshly downloaded waveform.

        Mirrors :meth:`KeysightMSOX4154A.get_statistics` so that
        ``data_logger`` workflows are portable.

        Args:
            channel: Channel string (e.g. ``"CH1"``) or integer.

        Returns:
            Dictionary with keys:

            - ``"statistics"``: ``[mean, std_dev, min, max]`` computed
              from the captured waveform samples.
            - ``"voltage"``, ``"voltage_rms"``, ``"voltage_pp"``,
              ``"frequency"``, ``"period"``: scalar values queried from
              the MEASUrement subsystem.
            - ``"sample_count"``, ``"sample_rate_hz"``, ``"duration_s"``.
        """
        self._chk()
        if isinstance(channel, int):
            ch_str = f"CH{channel}"
        else:
            ch_str = channel
        try:
            wf = self.get_waveform(source=ch_str, debug=False)
            t, y, meta = wf["t"], wf["y"], wf["meta"]

            if not y:
                return {"error": "No waveform data available"}

            import statistics as stats
            avg = stats.mean(y)
            sd = stats.stdev(y) if len(y) > 1 else 0.0
            vmin = min(y)
            vmax = max(y)

            return {
                "statistics":     [avg, sd, vmin, vmax],
                "voltage":        avg,
                "voltage_rms":    self.get_measurement("RMS", ch_str),
                "voltage_pp":     self.get_measurement("PK2PK", ch_str),
                "frequency":      self.get_measurement("FREQuency", ch_str),
                "period":         self.get_measurement("PERIod", ch_str),
                "sample_count":   len(y),
                "sample_rate_hz": meta.get("sample_rate_hz", float("nan")),
                "duration_s":     (t[-1] - t[0]) if t and len(t) > 1 else 0.0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get(self, item: str, channel: int = 1) -> Any:
        """Generic measurement dispatcher (``data_logger``-compatible).

        Supported ``item`` values (case-insensitive):

        - ``"statistics"`` → ``[mean, std_dev, min, max]``
        - ``"voltage"``, ``"voltage_rms"``, ``"voltage_pp"``,
          ``"frequency"``, ``"period"`` → ``float``
        - ``"waveform"`` → ``{"t", "y", "meta"}``
        - ``"metadata"`` → :meth:`get_metadata` for ``[channel]``
        - ``"channel_config"`` / ``"channel_cfg"`` →
          :meth:`get_channel_config`
        - ``"timebase"`` → :meth:`get_timebase_config`
        - ``"trigger"`` → :meth:`get_trigger_config`
        - ``"acquisition"`` → :meth:`get_acquisition_config`
        - Any other string is forwarded to :meth:`get_measurement` as a
          Tek measurement type name.

        Args:
            item: Measurement key.
            channel: Analog channel number (1-based).

        Returns:
            The matching measurement, dict, or list — or ``nan`` on
            failure for scalar requests.
        """
        self._chk()
        ch_str = f"CH{int(channel)}"
        key = item.lower()
        try:
            if key == "statistics":
                return self.get_statistics(ch_str).get("statistics", [float("nan")] * 4)
            elif key == "voltage":
                return self.get_statistics(ch_str).get("voltage", float("nan"))
            elif key == "voltage_rms":
                return self.get_measurement("RMS", ch_str)
            elif key == "voltage_pp":
                return self.get_measurement("PK2PK", ch_str)
            elif key == "frequency":
                return self.get_measurement("FREQuency", ch_str)
            elif key == "period":
                return self.get_measurement("PERIod", ch_str)
            elif key == "all_measurements":
                return self.get_statistics(ch_str)
            elif key == "waveform":
                return self.get_waveform(int(channel))
            elif key == "metadata":
                return self.get_metadata([int(channel)])
            elif key in ("channel_config", "channel_cfg"):
                return self.get_channel_config(int(channel))
            elif key == "timebase":
                return self.get_timebase_config()
            elif key == "trigger":
                return self.get_trigger_config()
            elif key == "acquisition":
                return self.get_acquisition_config()
            else:
                return self.get_measurement(item.upper(), ch_str)
        except Exception as e:
            print(_ERROR_STYLE + f"Measurement '{item}' failed: {e}")
            return float("nan")
