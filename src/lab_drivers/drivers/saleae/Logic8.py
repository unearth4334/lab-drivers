#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file Logic8.py
#   @brief Driver for the Saleae Logic 8 logic analyzer via the Logic 2
#          automation API (gRPC).
#   @date 01-Jun-2026

"""
Saleae Logic 8 Driver
=====================

Thin wrapper around the official ``logic2-automation`` Python package
(import name ``saleae``) for controlling the Saleae Logic 8 hardware
through the Logic 2 desktop application.

Unlike the other drivers in this package, the Logic 8 is **not** a VISA
or serial instrument. Instead, the Logic 2 application exposes a local
gRPC server (default ``127.0.0.1:10430``) that the
``logic2-automation`` client connects to. Logic 2 must be running with
the *Automation Server* enabled (Edit -> Preferences -> Automation).

Prerequisites
-------------
1. Install the Logic 2 desktop application (>= 2.4.0).
2. Enable the Automation server in Logic 2 preferences.
3. Install the Python client::

       pip install logic2-automation

Basic Usage
-----------
```python
from lab_drivers.drivers.saleae.Logic8 import Logic8

logic = Logic8()  # auto-connects to a running Logic 2 instance
logic.start_capture(
    digital_channels=[0, 1, 2, 3],
    sample_rate_hz=10_000_000,
    duration_s=1.0,
)
logic.wait_capture()
logic.export_raw(r"C:\\temp\\capture")  # writes <path>/digital_*.bin etc.
logic.close_capture()
logic.disconnect()
```

Notes
-----
- The Logic 2 automation API is capture-centric: configuration is passed
  per-capture rather than being a persistent device state.
- Analog channels on the Logic 8 are sampled up to 10 MS/s; digital up
  to 100 MS/s (subject to active channel count). The API will raise if
  the requested rate is not supported.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional, Sequence

try:
    from colorama import init as _color_init, Fore, Style
    _color_init(autoreset=True)
    _ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
    _SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
except Exception:  # pragma: no cover - colorama optional
    _ERROR_STYLE = "Error! "
    _SUCCESS_STYLE = ""

# The Logic 2 automation package is an optional dependency. Defer the
# import error until the user actually tries to construct the driver so
# that simply importing `lab_drivers.drivers.saleae` does not require
# the package to be installed.
try:
    from saleae import automation  # type: ignore
    _IMPORT_ERROR: Optional[Exception] = None
except Exception as _exc:  # pragma: no cover - exercised only when missing
    automation = None  # type: ignore[assignment]
    _IMPORT_ERROR = _exc


class Logic8:
    """Driver for the Saleae Logic 8 via the Logic 2 automation API.

    Parameters
    ----------
    auto_connect:
        If True (default), open a connection to the Logic 2 application
        immediately.
    host:
        gRPC host of the Logic 2 automation server. Defaults to
        ``127.0.0.1``.
    port:
        gRPC port. Defaults to ``10430`` (the Logic 2 default).
    connect_timeout_s:
        Timeout when establishing the gRPC connection.
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 10430

    def __init__(
        self,
        auto_connect: bool = True,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        connect_timeout_s: float = 5.0,
    ) -> None:
        if _IMPORT_ERROR is not None:
            raise ImportError(
                _ERROR_STYLE
                + "The 'logic2-automation' package is required for the "
                "Logic8 driver. Install it with: pip install logic2-automation"
            ) from _IMPORT_ERROR

        self.host = host
        self.port = port
        self.connect_timeout_s = connect_timeout_s
        self.manager: Optional["automation.Manager"] = None
        self.capture: Optional["automation.Capture"] = None
        self.status: str = "Not Connected"

        if auto_connect:
            self.connect()

    # -----------------------------
    # Connection lifecycle
    # -----------------------------
    def connect(self) -> None:
        """Open a gRPC connection to the Logic 2 application."""
        try:
            self.manager = automation.Manager.connect(
                address=self.host,
                port=self.port,
                connect_timeout_seconds=self.connect_timeout_s,
            )
        except Exception as exc:
            raise ConnectionError(
                _ERROR_STYLE
                + f"Failed to connect to Logic 2 at {self.host}:{self.port}. "
                "Is the Logic 2 app running with the automation server enabled? "
                f"({exc})"
            ) from exc

        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to Saleae Logic 2 at {self.host}:{self.port}")

    def disconnect(self) -> None:
        """Close any active capture and the gRPC connection."""
        if self.capture is not None:
            try:
                self.capture.close()
            except Exception:
                pass
            self.capture = None

        if self.manager is not None:
            try:
                self.manager.close()
            finally:
                print(f"\rDisconnected from Saleae Logic 2 at {self.host}:{self.port}")
        self.manager = None
        self.status = "Not Connected"

    def __enter__(self) -> "Logic8":
        if self.manager is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # -----------------------------
    # Helpers
    # -----------------------------
    def _chk(self) -> None:
        if self.status != "Connected" or self.manager is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to Logic 2.")

    def _chk_capture(self) -> None:
        if self.capture is None:
            raise RuntimeError(
                _ERROR_STYLE
                + "No active capture. Call start_capture() first."
            )

    # -----------------------------
    # Capture control
    # -----------------------------
    def start_capture(
        self,
        digital_channels: Optional[Sequence[int]] = None,
        analog_channels: Optional[Sequence[int]] = None,
        digital_sample_rate_hz: Optional[int] = None,
        analog_sample_rate_hz: Optional[int] = None,
        sample_rate_hz: Optional[int] = None,
        duration_s: Optional[float] = None,
        device_id: Optional[str] = None,
    ) -> None:
        """Start a timed capture on the connected Logic 8.

        Parameters
        ----------
        digital_channels:
            Digital channel indices to enable (0-7 on the Logic 8).
        analog_channels:
            Analog channel indices to enable (0-7 on the Logic 8).
        digital_sample_rate_hz / analog_sample_rate_hz:
            Per-domain sample rates. If ``sample_rate_hz`` is given it
            is used for whichever domain rate is left unspecified.
        sample_rate_hz:
            Convenience fallback applied to enabled domains when the
            per-domain rate is not provided.
        duration_s:
            Capture duration in seconds. If ``None`` a manual-trigger
            capture is started (caller must call :py:meth:`stop_capture`).
        device_id:
            Optional Saleae device serial. If ``None`` the first
            available device is used.
        """
        self._chk()

        digital_channels = list(digital_channels) if digital_channels else []
        analog_channels = list(analog_channels) if analog_channels else []

        if not digital_channels and not analog_channels:
            raise ValueError(
                "At least one digital or analog channel must be specified."
            )

        d_rate = digital_sample_rate_hz if digital_sample_rate_hz is not None else sample_rate_hz
        a_rate = analog_sample_rate_hz if analog_sample_rate_hz is not None else sample_rate_hz

        if digital_channels and d_rate is None:
            raise ValueError("digital_sample_rate_hz (or sample_rate_hz) is required when digital_channels are set.")
        if analog_channels and a_rate is None:
            raise ValueError("analog_sample_rate_hz (or sample_rate_hz) is required when analog_channels are set.")

        device_config = automation.LogicDeviceConfiguration(
            enabled_digital_channels=digital_channels,
            enabled_analog_channels=analog_channels,
            digital_sample_rate=d_rate if digital_channels else None,
            analog_sample_rate=a_rate if analog_channels else None,
        )

        if duration_s is not None:
            capture_config = automation.CaptureConfiguration(
                capture_mode=automation.TimedCaptureMode(duration_seconds=float(duration_s)),
            )
        else:
            capture_config = automation.CaptureConfiguration(
                capture_mode=automation.ManualCaptureMode(),
            )

        self.capture = self.manager.start_capture(  # type: ignore[union-attr]
            device_id=device_id,
            device_configuration=device_config,
            capture_configuration=capture_config,
        )

    def wait_capture(self) -> None:
        """Block until the active timed capture completes."""
        self._chk_capture()
        self.capture.wait()  # type: ignore[union-attr]

    def stop_capture(self) -> None:
        """Stop a manual-trigger capture."""
        self._chk_capture()
        self.capture.stop()  # type: ignore[union-attr]

    def close_capture(self) -> None:
        """Discard the active capture and free its resources."""
        if self.capture is None:
            return
        try:
            self.capture.close()
        finally:
            self.capture = None

    # -----------------------------
    # Export / save
    # -----------------------------
    def save_capture(self, path: str) -> None:
        """Save the active capture to a ``.sal`` archive."""
        self._chk_capture()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.capture.save_capture(filepath=path)  # type: ignore[union-attr]

    def export_raw(
        self,
        directory: str,
        digital_channels: Optional[Sequence[int]] = None,
        analog_channels: Optional[Sequence[int]] = None,
    ) -> None:
        """Export raw per-channel binary data into ``directory``."""
        self._chk_capture()
        os.makedirs(directory, exist_ok=True)
        self.capture.export_raw_data_binary(  # type: ignore[union-attr]
            directory=directory,
            digital_channels=list(digital_channels) if digital_channels else None,
            analog_channels=list(analog_channels) if analog_channels else None,
        )

    def export_csv(
        self,
        directory: str,
        digital_channels: Optional[Sequence[int]] = None,
        analog_channels: Optional[Sequence[int]] = None,
    ) -> None:
        """Export the capture to CSV files inside ``directory``."""
        self._chk_capture()
        os.makedirs(directory, exist_ok=True)
        self.capture.export_raw_data_csv(  # type: ignore[union-attr]
            directory=directory,
            digital_channels=list(digital_channels) if digital_channels else None,
            analog_channels=list(analog_channels) if analog_channels else None,
        )

    # -----------------------------
    # Introspection
    # -----------------------------
    def list_devices(self) -> List[dict]:
        """Return information about all devices visible to Logic 2."""
        self._chk()
        devices = self.manager.get_devices()  # type: ignore[union-attr]
        return [
            {
                "device_id": getattr(d, "device_id", None),
                "device_type": getattr(d, "device_type", None),
                "is_simulation": getattr(d, "is_simulation", None),
            }
            for d in devices
        ]
