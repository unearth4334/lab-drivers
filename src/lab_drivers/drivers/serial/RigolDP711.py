#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigol DP711 Programmable DC Power Supply Driver
================================================

Driver for Rigol DP711 power supply with serial (RS-232) connectivity.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import serial
import serial.tools.list_ports
from lab_drivers.core.log import get_logger
from lab_drivers.core.ports import resolve_address as _resolve_address, select_port

_log = get_logger(__name__)



_DELAY = 0.2   # inter-command delay (s)
_IDN_DELAY = 0.5  # longer wait after *IDN? on first connect

class RigolDP711:
    """Rigol DP711 programmable power-supply driver.

    Serial-backed driver with voltage/current control, output state commands,
    and measurement helpers for bench automation.
    """
    
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None,
                 baud_rate: int = 9600, *, com_port: Optional[str] = None,
                 interactive: Optional[bool] = None):
        """
        Initialize RigolDP711 driver.

        Args:
            auto_connect: Automatically connect to device on initialization
            address: Optional explicit serial port (e.g., 'COM4', '/dev/ttyUSB0')
            baud_rate: Serial baud rate (default: 9600)
            com_port: Deprecated alias for ``address``.
            interactive: Whether a missing port may be resolved by prompting.
                ``None`` prompts only when stdin is a terminal.
        """
        address = _resolve_address(address, com_port)

        self.ser: Optional[serial.Serial] = None
        self.address: Optional[str] = None
        self.status: str = "Not Connected"
        self.identity: Optional[str] = None
        self._com_port_hint: Optional[str] = address
        self._baud_rate: int = baud_rate
        self._interactive: Optional[bool] = interactive

        if auto_connect:
            self.connect(address=address, baud_rate=baud_rate)

    def connect(self, address: Optional[str] = None, baud_rate: int = 9600, *,
                com_port: Optional[str] = None,
                interactive: Optional[bool] = None) -> None:
        """
        Establish connection to RigolDP711 power supply.

        Args:
            address: Optional serial port (for example, ``"COM4"`` or
                ``"/dev/ttyUSB0"``). When omitted, ``DP711_COM_PORT`` is
                consulted, then the operator is prompted if this process has a
                terminal.
            baud_rate: Serial baud rate.
            com_port: Deprecated alias for ``address``.
            interactive: Override the prompting decision for this call.

        Raises:
            ConnectionError: If device not found, connection fails, or a port is
                needed but this process cannot prompt for one.

        Returns:
            None

        Example:
            >>> psu = RigolDP711(auto_connect=False)
            >>> psu.connect(address="/dev/ttyUSB0")
        """
        address = _resolve_address(address, com_port) or self._com_port_hint
        explicit_port = select_port(
            "Rigol DP711", port=address, env_var="DP711_COM_PORT",
            interactive=self._interactive if interactive is None else interactive,
        )

        # Open serial connection
        try:
            self.ser = serial.Serial(
                explicit_port,
                baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                timeout=2,
            )
            self.address = explicit_port

            # Assert DTR + RTS
            self.ser.dtr = True
            self.ser.rts = True
            time.sleep(0.05)

            # Flush buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            time.sleep(0.1)

            # Try \r\n first (Rigol standard), fall back to \n
            self.identity = None
            for terminator in (b'\r\n', b'\n'):
                self.ser.reset_input_buffer()
                self.ser.write(b'*IDN?' + terminator)
                self.ser.flush()
                time.sleep(_IDN_DELAY)

                n = self.ser.in_waiting
                raw = self.ser.read(n) if n > 0 else b''
                candidate = raw.decode('ascii', errors='ignore').strip()
                if len(candidate) >= 5:
                    self.identity = candidate
                    break

            if not self.identity:
                raise ConnectionError("Device not responding with valid identity")

            self.status = "Connected"
            _log.info(f"Connected to {self.identity}")

        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {explicit_port}: {e}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to {explicit_port}: {e}")

    def disconnect(self) -> None:
        """
        Close the serial connection to the device.

        Returns:
            None

        Example:
            >>> psu.disconnect()
        """
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            finally:
                _log.info(f"Disconnected from Rigol DP711 at {self.address}")
                self.ser = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.ser is None or not self.ser.is_open:
            raise ConnectionError("Not connected to Rigol DP711")
    
    def _write(self, command: str) -> None:
        """Write a command to the device."""
        self._chk()
        self.ser.write(f"{command}\r\n".encode('ascii'))
        self.ser.flush()
        time.sleep(_DELAY)
    
    def _query(self, command: str) -> str:
        """Query the device and return the response."""
        self._chk()
        self.ser.reset_input_buffer()
        self.ser.write(f"{command}\r\n".encode('ascii'))
        self.ser.flush()
        time.sleep(_DELAY)
        n = self.ser.in_waiting
        raw = self.ser.read(n) if n > 0 else b''
        return raw.decode('ascii', errors='ignore').strip()
    
    def get(self, item: str, channel: int = 1) -> float:
        """
        Retrieve a measurement value by item name.

        Args:
            item: Measurement selector. Supported values are ``"CURR"``, ``"CURRENT"``,
                ``"VOLT"``, and ``"VOLTAGE"`` (case-insensitive).
            channel: Unused placeholder for API compatibility.

        Returns:
            Measurement value in base SI units (A or V).

        Raises:
            ValueError: If ``item`` is not supported.
            ConnectionError: If the device is not connected.

        Example:
            >>> volts = psu.get("VOLT")
            >>> amps = psu.get("CURRENT")
        """
        self._chk()

        item_upper = item.strip().upper()
        
        items = {
            "CURR": self.measure_current,
            "CURRENT": self.measure_current,
            "VOLT": self.measure_voltage,
            "VOLTAGE": self.measure_voltage
        }
        
        if item_upper not in items:
            raise ValueError(
                f"Invalid item '{item}'. "
                f"Valid items: {', '.join(items.keys())}"
            )

        return items[item_upper]()

    def set_voltage(self, voltage: float) -> None:
        """
        Set the output voltage setpoint.

        Args:
            voltage: Target voltage in volts. Valid range is 0 to 30.

        Returns:
            None

        Raises:
            ValueError: If ``voltage`` is outside the supported range.
            ConnectionError: If the device is not connected.

        Example:
            >>> psu.set_voltage(12.0)
        """
        self._chk()
        
        if not 0 <= voltage <= 30:
            raise ValueError(f"Voltage {voltage}V out of range (0-30V)")
        
        command = f':VOLT {voltage:.3f}'
        self._write(command)

    def set_current(self, current: float) -> None:
        """
        Set the output current limit.

        Args:
            current: Current limit in amperes. Valid range is 0 to 5.

        Returns:
            None

        Raises:
            ValueError: If ``current`` is outside the supported range.
            ConnectionError: If the device is not connected.

        Example:
            >>> psu.set_current(1.5)
        """
        self._chk()
        
        if not 0 <= current <= 5:
            raise ValueError(f"Current {current}A out of range (0-5A)")
        
        command = f':CURR {current:.3f}'
        self._write(command)

    def measure_voltage(self) -> float:
        """
        Measure the actual output voltage.

        Returns:
            Measured output voltage in volts.

        Raises:
            ValueError: If the returned value cannot be parsed.
            ConnectionError: If the device is not connected.

        Example:
            >>> voltage = psu.measure_voltage()
        """
        try:
            response = self._query(':MEAS:VOLT?')
            return float(response)
        except ValueError as e:
            raise ValueError(f"Failed to parse voltage measurement: {e}")

    def measure_current(self) -> float:
        """
        Measure the actual output current.

        Returns:
            Measured output current in amperes.

        Raises:
            ValueError: If the returned value cannot be parsed.
            ConnectionError: If the device is not connected.

        Example:
            >>> current = psu.measure_current()
        """
        try:
            response = self._query(':MEAS:CURR?')
            return float(response)
        except ValueError as e:
            raise ValueError(f"Failed to parse current measurement: {e}")

    def set_output_state(self, state: bool) -> None:
        """
        Enable or disable the power supply output.

        Args:
            state: ``True`` to enable output, ``False`` to disable output.

        Returns:
            None

        Raises:
            ConnectionError: If the device is not connected.

        Example:
            >>> psu.set_output_state(True)
        """
        self._chk()
        
        if state:
            command = ':OUTP ON'
            _log.info("Rigol DP711 output: ON")
        else:
            command = ':OUTP OFF'
            _log.info("Rigol DP711 output: OFF")
        
        self._write(command)

    def turn_on(self) -> None:
        """
        Turn on the power supply output.

        Returns:
            None

        Example:
            >>> psu.turn_on()
        """
        self.set_output_state(True)

    def turn_off(self) -> None:
        """
        Turn off the power supply output.

        Returns:
            None

        Example:
            >>> psu.turn_off()
        """
        self.set_output_state(False)
