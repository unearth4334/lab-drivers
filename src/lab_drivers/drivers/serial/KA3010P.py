#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file KA3010P.py
#   @brief Driver for Korad KA3010P Power Supply
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
Korad KA3010P Programmable DC Power Supply Driver
==================================================

This module provides a driver for the Korad KA3010P single-output programmable
DC power supply with RS-232 serial interface.

Features
--------
- **Single Channel**: 0-30V, 0-10A output
- **Serial Interface**: RS-232 communication
- **Programmable**: Set voltage and current limits
- **Readback**: Measure actual output voltage and current
- **Compact**: Benchtop power supply

Basic Usage
-----------
```python
from libs.KA3010P import KA3010P

# Connect to power supply
psu = KA3010P(com_port="COM4")

# Set output voltage and current
psu.set_voltage(12.0)  # 12V
psu.set_current(2.0)   # 2A limit

# Enable output
psu.set_output_state(True)

# Read measurements
voltage = psu.measure_voltage()
current = psu.measure_current()
print(f"V: {voltage:.3f}V, I: {current:.3f}A")

# Disable output
psu.set_output_state(False)
psu.disconnect()
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("ka3010p_data.txt")

psu = logger.connect("ka3010p")

psu.set_voltage(15.0)
psu.set_output_state(True)

logger.add(psu, "voltage", label="KA3010P_V")
logger.add(psu, "current", label="KA3010P_I")

for i in range(100):
    logger.get_data()
    
psu.set_output_state(False)
logger.close_file()
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"VOLT"** - Measure actual output voltage in volts
- **"CURR"** - Measure actual output current in amperes

Example:
```python
psu = logger.connect("ka3010p")
voltage = psu.get("VOLT")
current = psu.get("CURR")
```

Available Methods
-----------------
- `set_voltage(voltage)` - Set output voltage (0-30V)
- `set_current(current)` - Set current limit (0-10A)
- `set_output_state(state)` - Enable/disable output
- `measure_voltage()` - Read actual voltage
- `measure_current()` - Read actual current
- `get(item)` - Generic getter (VOLT, CURR)
- `connect(com_port)` - Establish serial connection
- `disconnect()` - Close connection

Technical Specifications
------------------------
- **Voltage Range**: 0-30V
- **Current Range**: 0-10A
- **Power Rating**: 300W
- **Voltage Resolution**: 10mV
- **Current Resolution**: 10mA
- **Interface**: RS-232 serial

See Also
--------
- RigolDP832: Triple-output power supply
- data_logger: Main orchestrator class
"""

from __future__ import annotations

import os
import time
from typing import Optional

import serial
import serial.tools.list_ports
from colorama import init, Fore, Style


# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.2  # in seconds

class KA3010P:
    """
    Driver for Korad KA3010P Programmable DC Power Supply.
    
    This class provides methods for connecting to and controlling a
    KA3010P power supply via RS-232 serial interface.
    
    Attributes:
        ser: Serial connection object
        address: COM port address
        status: Connection status ("Connected" or "Not Connected")
        identity: Device identification string
        
    Example:
        >>> ps = KA3010P()
        >>> ps.set_voltage(5.0)
        >>> ps.set_current(1.0)
        >>> ps.turn_on()
        >>> voltage = ps.measure_voltage()
        >>> ps.turn_off()
        >>> ps.disconnect()
    """
    
    def __init__(self, auto_connect: bool = True, com_port: Optional[str] = None, baud_rate: int = 9600):
        """
        Initialize KA3010P driver.
        
        Args:
            auto_connect: Automatically connect to device on initialization
            com_port: Optional explicit COM port (e.g., 'COM19', '/dev/ttyUSB0')
            baud_rate: Serial baud rate (default: 9600)
        """
        init(autoreset=True)
        
        self.ser: Optional[serial.Serial] = None
        self.address: Optional[str] = None
        self.status: str = "Not Connected"
        self.identity: Optional[str] = None
        self._com_port_hint: Optional[str] = com_port
        self._baud_rate: int = baud_rate

        if auto_connect:
            self.connect(com_port=com_port, baud_rate=baud_rate)
    
    def connect(self, com_port: Optional[str] = None, baud_rate: int = 9600) -> None:
        """
        Establish connection to KA3010P power supply.
        
        Args:
            com_port: Optional COM port (e.g., 'COM19', '/dev/ttyUSB0'). If None, prompt user.
            baud_rate: Serial baud rate (default: 9600)
            
        Raises:
            ConnectionError: If device not found or connection fails.
        """
        # 1) Try explicit COM port first
        explicit_port = com_port or self._com_port_hint
        
        # 2) Try environment variable
        if explicit_port is None:
            try:
                explicit_port = os.environ.get('KA3010P_COM_PORT')
            except Exception:
                pass
        
        # 3) Prompt user to select COM port
        if explicit_port is None:
            ports = serial.tools.list_ports.comports()
            if not ports:
                raise ConnectionError(_ERROR_STYLE + "No COM ports found")
            
            print("\nAvailable COM ports:")
            for i, port in enumerate(ports, start=1):
                print(f"  {i}. {port.device} - {port.description}")
            
            while True:
                try:
                    selection = int(input("Select COM port for KA3010P (1, 2, ...): "))
                    if 1 <= selection <= len(ports):
                        explicit_port = ports[selection - 1].device
                        os.environ['KA3010P_COM_PORT'] = explicit_port
                        break
                    print(_ERROR_STYLE + "Invalid selection")
                except ValueError:
                    print(_ERROR_STYLE + "Invalid input. Enter a number.")
        
        # 4) Open serial connection
        try:
            self.ser = serial.Serial(explicit_port, baud_rate, timeout=5)
            self.address = explicit_port
            
            # Verify device identity
            self.ser.write(str('*IDN?\n').encode('ascii'))
            time.sleep(_DELAY)
            identity_bytes = self.ser.readline()
            self.identity = identity_bytes.decode('ascii', errors='ignore').strip()
            
            if len(self.identity) < 5:
                raise ConnectionError(_ERROR_STYLE + "Device not responding with valid identity")
            
            self.status = "Connected"
            print(_SUCCESS_STYLE + f"Connected to {self.identity}")
            
        except serial.SerialException as e:
            raise ConnectionError(_ERROR_STYLE + f"Failed to connect to {explicit_port}: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Unexpected error connecting to {explicit_port}: {e}")

    
    def disconnect(self) -> None:
        """Close the serial connection to the device."""
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            finally:
                print(f"\rDisconnected from KA3010P at {self.address}")
                self.ser = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.ser is None or not self.ser.is_open:
            raise ConnectionError(_ERROR_STYLE + "Not connected to KA3010P")
    
    def get(self, item: str, channel: int = 1) -> float:
        """
        Retrieve measurement value by name.
        
        Args:
            item: Measurement item name (case-insensitive)
                  Valid values: 'CURR', 'VOLT'
            channel: Optional channel number (for compatibility, not used)
            
        Returns:
            Measurement value
            
        Raises:
            ValueError: If invalid item requested
            ConnectionError: If not connected to device
            
        Example:
            >>> voltage = ps.get('VOLT')
            >>> current = ps.get('CURR')
        """
        self._chk()

        item_upper = item.strip().upper()
        
        items = {
            "CURR": self.measure_current,
            "VOLT": self.measure_voltage
        }
        
        if item_upper not in items:
            raise ValueError(
                _ERROR_STYLE + f"Invalid item '{item}'. "
                f"Valid items: {', '.join(items.keys())}"
            )

        return items[item_upper]()

    def set_voltage(self, val: float) -> None:
        """
        Set the output voltage.
        
        Args:
            val: Voltage value to set
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        time.sleep(_DELAY)
        command = f'VSET1:{val}'
        self.ser.write(str(command).encode('ascii'))

    def set_current(self, val: float) -> None:
        """
        Set the output current limit.
        
        Args:
            val: Current value to set
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        time.sleep(_DELAY)
        command = f'ISET1:{val}'
        self.ser.write(str(command).encode('ascii'))

    def get_voltage(self) -> float:
        """
        Get the configured voltage setpoint.
        
        Returns:
            Configured voltage value
            
        Raises:
            ConnectionError: If not connected to device
            ValueError: If response cannot be parsed
        """
        self._chk()
        command = 'VSET1?'
        
        try:
            self.ser.write(str(command).encode('ascii'))
            time.sleep(_DELAY)
            val = self.ser.read(self.ser.in_waiting)
            val_str = val.decode('ascii', errors='ignore').strip()
            return float(val_str)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse voltage: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Communication error: {e}")

    def get_current(self) -> float:
        """
        Get the configured current limit setpoint.
        
        Returns:
            Configured current value
            
        Raises:
            ConnectionError: If not connected to device
            ValueError: If response cannot be parsed
        """
        self._chk()
        command = 'ISET1?'
        
        try:
            self.ser.write(str(command).encode('ascii'))
            time.sleep(_DELAY)
            val = self.ser.read(self.ser.in_waiting)
            val_str = val.decode('ascii', errors='ignore').strip()
            return float(val_str)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse current: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Communication error: {e}")
    
    def measure_voltage(self) -> float:
        """
        Measure the actual output voltage.
        
        Returns:
            Measured voltage value
            
        Raises:
            ConnectionError: If not connected to device
            ValueError: If response cannot be parsed
        """
        self._chk()
        command = 'VOUT1?'
        
        try:
            self.ser.write(str(command).encode('ascii'))
            time.sleep(_DELAY)
            val = self.ser.read(self.ser.in_waiting)
            val_str = val.decode('ascii', errors='ignore').strip()
            return float(val_str)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse voltage measurement: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Communication error: {e}")

    def measure_current(self) -> float:
        """
        Measure the actual output current.
        
        Returns:
            Measured current value
            
        Raises:
            ConnectionError: If not connected to device
            ValueError: If response cannot be parsed
        """
        self._chk()
        command = 'IOUT1?'
        
        try:
            self.ser.write(str(command).encode('ascii'))
            time.sleep(_DELAY)
            val = self.ser.read(self.ser.in_waiting)
            val_str = val.decode('ascii', errors='ignore').strip()
            return float(val_str)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse current measurement: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Communication error: {e}")

    def turn_on(self) -> None:
        """
        Turn on the power supply output.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        time.sleep(_DELAY)
        command = 'OUT1'
        self.ser.write(str(command).encode('ascii'))

    def turn_off(self) -> None:
        """
        Turn off the power supply output.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        time.sleep(_DELAY)
        command = 'OUT0'
        self.ser.write(str(command).encode('ascii'))
        
