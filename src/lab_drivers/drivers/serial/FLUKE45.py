#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file FLUKE45.py
#   @brief Driver for Fluke 45 Digital Multimeter
#   @date 27-Jan-2026
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
Fluke 45 Digital Multimeter Driver
===================================

This module provides a driver for the Fluke 45 dual-display bench multimeter
with RS-232 serial interface.

Features
--------
- **Dual Display**: Simultaneous measurement of two parameters
- **Serial Interface**: RS-232 communication
- **High Accuracy**: 4.5-digit resolution
- **Multiple Functions**: DC/AC voltage, DC/AC current, resistance, frequency
- **Auto-Ranging**: Automatic range selection

Basic Usage
-----------
```python
from lab_drivers.drivers.serial import FLUKE45

# Connect to Fluke 45
dmm = FLUKE45(com_port="COM3")

# Measure voltage
voltage = dmm.measure_voltage()
print(f"Voltage: {voltage:.4f} V")

# Measure resistance
resistance = dmm.measure_resistance()
print(f"Resistance: {resistance:.2f} Ω")

dmm.disconnect()
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("fluke45_data.txt")

dmm = logger.connect("fluke45")

logger.add(dmm, "voltage", label="FLUKE45_V")
logger.add(dmm, "current", label="FLUKE45_I")

for i in range(100):
    logger.get_data()
    
logger.close_file()
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"voltage"** - DC voltage measurement in volts

Example:
```python
dmm = logger.connect("fluke45")
voltage = dmm.get("voltage")
```

Available Methods
-----------------
- `measure_voltage()` - Measure voltage
- `measure_current()` - Measure current
- `measure_resistance()` - Measure resistance
- `get(item)` - Generic getter (voltage)
- `connect(com_port)` - Establish serial connection
- `disconnect()` - Close serial connection

Technical Specifications
------------------------
- **Resolution**: 4.5 digits (20,000 counts)
- **DC Voltage**: 0.001V to 1000V
- **AC Voltage**: 0.001V to 750V
- **DC Current**: 0.01μA to 10A
- **AC Current**: 0.01μA to 10A
- **Resistance**: 0.01Ω to 50MΩ
- **Interface**: RS-232 serial

See Also
--------
- DMM6500: Modern high-speed multimeter
- Keysight34460A: 6.5-digit multimeter
- data_logger: Main orchestrator class
"""

from __future__ import annotations

import os
import time
import statistics
from typing import Optional, Tuple

import numpy
import serial
import serial.tools.list_ports
from lab_drivers.core.log import get_logger
from lab_drivers.core.ports import resolve_address as _resolve_address, select_port

_log = get_logger(__name__)



_DELAY = 0.01  # in seconds

class FLUKE45:
    """Fluke 45 bench multimeter driver.

    Serial-backed driver exposing connection helpers, direct measurement methods,
    and a generic `get()` interface for data-logger workflows.
    """
    
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None,
                 baud_rate: int = 9600, debug: bool = False, *,
                 com_port: Optional[str] = None, interactive: Optional[bool] = None):
        """
        Initialize FLUKE45 driver.

        Args:
            auto_connect: Automatically connect to device on initialization
            address: Optional explicit serial port (e.g., 'COM7', '/dev/ttyUSB0')
            baud_rate: Serial baud rate (default: 9600)
            debug: Enable debug logging (default: False)
            com_port: Deprecated alias for ``address``.
            interactive: Whether a missing port may be resolved by prompting.
                ``None`` prompts only when stdin is a terminal.
        """
        address = _resolve_address(address, com_port)

        self.ser: Optional[serial.Serial] = None
        self.address: Optional[str] = None
        self.status: str = "Not Connected"
        self.identity: Optional[str] = None
        self.debug: bool = debug
        self._com_port_hint: Optional[str] = address
        self._baud_rate: int = baud_rate
        self._interactive: Optional[bool] = interactive

        if auto_connect:
            self.connect(address=address, baud_rate=baud_rate)

    def connect(self, address: Optional[str] = None, baud_rate: int = 9600, *,
                com_port: Optional[str] = None,
                interactive: Optional[bool] = None) -> None:
        """
        Establish connection to Fluke 45 multimeter.

        Args:
            address: Optional serial port (e.g., 'COM7', '/dev/ttyUSB0'). When
                omitted, ``FLUKE45_COM_PORT`` is consulted, then the operator is
                prompted if this process has a terminal.
            baud_rate: Serial baud rate (default: 9600)
            com_port: Deprecated alias for ``address``.
            interactive: Override the prompting decision for this call.

        Raises:
            ConnectionError: If device not found, connection fails, or a port is
                needed but this process cannot prompt for one.

        Returns:
            None

        Example:
            >>> dmm = FLUKE45(auto_connect=False)
            >>> dmm.connect(address="/dev/ttyUSB0")
        """
        address = _resolve_address(address, com_port) or self._com_port_hint
        explicit_port = select_port(
            "FLUKE45", port=address, env_var="FLUKE45_COM_PORT",
            interactive=self._interactive if interactive is None else interactive,
        )

        # 4) Open serial connection
        try:
            self.ser = serial.Serial(explicit_port, baud_rate, timeout=5)
            self.address = explicit_port
            
            # Verify device identity
            self.ser.write(str('*IDN?\n').encode('ascii'))
            time.sleep(_DELAY)
            self.ser.readline()  # Read first line
            identity_bytes = self.ser.readline()
            self.identity = identity_bytes.decode('ascii', errors='ignore').strip()
            
            if len(self.identity) < 5:
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
            >>> dmm.disconnect()
        """
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            finally:
                _log.info(f"Disconnected from FLUKE45 at {self.address}")
                self.ser = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.ser is None or not self.ser.is_open:
            raise ConnectionError("Not connected to FLUKE45")
    
    def measure_voltage(self) -> float:
        """
        Measure voltage from the Fluke 45.
        
        Returns:
            Voltage measurement in volts
            
        Raises:
            ConnectionError: If not connected to device
            ValueError: If measurement fails or returns invalid data

        Example:
            >>> voltage = dmm.measure_voltage()
        """
        self._chk()
        
        if self.debug:
            _log.info("MEAS?")
        
        command = 'MEAS?\n'
        
        try:
            self.ser.write(str(command).encode('ascii'))
            time.sleep(_DELAY)
            self.ser.readline()  # Read first line
            self.ser.readline()  # Read second line
            val_bytes = self.ser.readline()
            val_str = val_bytes.decode('ascii', errors='ignore').strip()
            
            if not val_str:
                raise ValueError("No response from device")
            
            return float(val_str)
        except ValueError as e:
            raise ValueError(f"Failed to parse measurement: {e}")
        except Exception as e:
            raise ConnectionError(f"Communication error during measurement: {e}")
    
    # Alias for backward compatibility
    def meas(self) -> float:
        """
        Deprecated: Use measure_voltage() instead.
        
        Returns:
            Voltage measurement in volts

        Example:
            >>> voltage = dmm.meas()
        """
        import warnings
        warnings.warn("meas() is deprecated, use measure_voltage()", DeprecationWarning, stacklevel=2)
        return self.measure_voltage()

    def calculate_statistics(self, n: int = 100) -> Tuple[float, float]:
        """
        Collect multiple voltage readings and calculate statistics.
        
        Args:
            n: Number of readings to collect (default: 100)
            
        Returns:
            Tuple of (mean, standard_deviation)
            
        Raises:
            ConnectionError: If not connected to device

        Example:
            >>> mean, stdev = dmm.calculate_statistics(50)
        """
        self._chk()
        
        val = numpy.zeros(n)
        for x in range(n):
            time.sleep(_DELAY)
            val[x] = self.measure_voltage()

        return (statistics.fmean(val), statistics.stdev(val))
    
    # Alias for backward compatibility
    def measure_avg(self, n: int) -> Tuple[float, float]:
        """
        Deprecated: Use calculate_statistics() instead.
        
        Args:
            n: Number of readings to collect
            
        Returns:
            Tuple of (mean, standard_deviation)

        Example:
            >>> mean, stdev = dmm.measure_avg(20)
        """
        import warnings
        warnings.warn("measure_avg() is deprecated, use calculate_statistics()", DeprecationWarning, stacklevel=2)
        return self.calculate_statistics(n)
    
    def get(self, item: str, channel: int = 1) -> float:
        """
        Retrieve measurement value by name.
        
        Args:
            item: Measurement item name (case-insensitive)
                  Valid values: 'voltage'
            channel: Optional channel number (for compatibility, not used)
            
        Returns:
            Measurement value
            
        Raises:
            ValueError: If invalid item requested
            ConnectionError: If not connected to device
            
        Example:
            >>> voltage = fluke.get('voltage')
        """
        self._chk()
        
        item_lower = item.strip().lower()
        
        if item_lower == 'voltage':
            return self.measure_voltage()
        
        raise ValueError(
            f"Invalid item '{item}'. "
            f"Valid items: voltage"
        )
