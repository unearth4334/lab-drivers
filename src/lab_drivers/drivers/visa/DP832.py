#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file DP832.py
#   @brief Driver for Rigol DP832 Power Supply
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
Rigol DP832 Triple-Output Power Supply Driver
==============================================

This module provides an alternative driver implementation for the Rigol DP832
programmable DC power supply with VISA interface.

Note: This is an alternative implementation to RigolDP832.py. Both drivers
support the same hardware but may have different features or API styles.

Features
--------
- **Triple Output Channels**: Three independent power supplies
  - CH1: 30V / 3A
  - CH2: 30V / 3A
  - CH3: 5V / 3A
- **VISA Interface**: USB/LAN connectivity
- **Independent Control**: Per-channel voltage and current settings
- **Output Enable/Disable**: Individual channel control
- **Measurement Readback**: Real-time voltage and current monitoring

Basic Usage
-----------
```python
from libs.DP832 import DP832

# Connect to power supply
psu = DP832()

# Configure channel 1
psu.set_voltage(12.0, channel=1)
psu.set_current(1.5, channel=1)
psu.set_output_state(True, channel=1)

# Read measurements
voltage = psu.measure_voltage(channel=1)
current = psu.measure_current(channel=1)
print(f"CH1: {voltage:.3f}V, {current:.3f}A")

# Disable output
psu.set_output_state(False, channel=1)
psu.disconnect()
```

Multi-Channel Power Distribution
---------------------------------
```python
# Configure all three channels for different loads
channels_config = [
    {"ch": 1, "voltage": 12.0, "current": 2.0},
    {"ch": 2, "voltage": 5.0, "current": 1.0},
    {"ch": 3, "voltage": 3.3, "current": 0.5}
]

for cfg in channels_config:
    psu.set_voltage(cfg["voltage"], channel=cfg["ch"])
    psu.set_current(cfg["current"], channel=cfg["ch"])
    psu.set_output_state(True, channel=cfg["ch"])

# Monitor all channels
for ch in [1, 2, 3]:
    v = psu.measure_voltage(channel=ch)
    i = psu.measure_current(channel=ch)
    print(f"CH{ch}: {v:.3f}V {i:.3f}A ({v*i:.3f}W)")
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("power_measurements.txt")

psu = logger.connect("dp832")

# Set up power supply
psu.set_voltage(15.0, channel=1)
psu.set_output_state(True, channel=1)

# Log measurements
logger.add(psu, "voltage", channel=1, label="DP832_CH1_V")
logger.add(psu, "current", channel=1, label="DP832_CH1_I")

for i in range(100):
    logger.get_data()
    
psu.set_output_state(False, channel=1)
logger.close_file()
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item, channel)` method:

- **"VOLT"** - Measure actual output voltage in volts
- **"CURR"** - Measure actual output current in amperes

Example:
```python
psu = logger.connect("dp832")
voltage = psu.get("VOLT", channel=1)
current = psu.get("CURR", channel=2)
```

Available Methods
-----------------
Voltage/Current Control:
- `set_voltage(voltage, channel)` - Set output voltage (V)
- `set_current(current, channel)` - Set current limit (A)
- `measure_voltage(channel)` - Read actual voltage
- `measure_current(channel)` - Read actual current

Output Control:
- `set_output_state(state, channel)` - Enable/disable channel
- `get_output_state(channel)` - Check output state

Connection:
- `connect()` - Establish VISA connection
- `disconnect()` - Close connection

Generic Interface:
- `get(item, channel)` - Generic getter (VOLT, CURR)

Technical Specifications
------------------------
- **Output Channels**: 3 independent outputs
- **CH1/CH2 Voltage**: 0-30V
- **CH1/CH2 Current**: 0-3A
- **CH3 Voltage**: 0-5V
- **CH3 Current**: 0-3A
- **Total Power**: 195W maximum
- **Interface**: USB, LAN via PyVISA

Comparison with RigolDP832
--------------------------
- **DP832.py**: This module (alternative implementation)
- **RigolDP832.py**: Original driver in libs/

Both support the same hardware. Choose based on API preference or specific
features required for your application.

See Also
--------
- RigolDP832: Original DP832 driver implementation
- StanfordPS310: High voltage power supply
- data_logger: Main orchestrator class
"""

from __future__ import annotations

import time
from typing import Optional, Union

import pyvisa
from colorama import init, Fore, Back, Style


# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.01  # in seconds

class DP832:
    """
    Driver for Rigol DP832 Triple-Output Power Supply.
    
    This class provides methods for connecting to and controlling a
    Rigol DP832 programmable DC power supply via VISA interface.
    
    Attributes:
        rm: PyVISA ResourceManager instance
        address: Device VISA address
        instrument: Active connection handle
        status: Connection status ("Connected" or "Not Connected")
        
    Example:
        >>> ps = DP832()
        >>> ps.set_voltage(1, 5.0)
        >>> ps.set_current(1, 1.0)
        >>> ps.toggle_output(1, 'ON')
        >>> voltage = ps.measure_voltage(1)
        >>> ps.toggle_output(1, 'OFF')
        >>> ps.disconnect()
    """
    
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None):
        """
        Initialize DP832 driver.
        
        Args:
            auto_connect: Automatically connect to device on initialization
            address: Optional explicit VISA address (e.g., 'USB0::0x1AB1::0x0E11::DP8C...::INSTR')
        """
        init(autoreset=True)
        
        self.rm: Optional[pyvisa.ResourceManager] = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status: str = "Not Connected"
        self._address_hint: Optional[str] = address

        if auto_connect:
            self.connect(address=address)
    
    def connect(self, address: Optional[str] = None) -> None:
        """
        Establish connection to DP832 power supply.
        
        Args:
            address: Optional explicit VISA resource string. If None, auto-detect.
            
        Raises:
            ConnectionError: If device not found or connection fails.
        """
        # 1) Try explicit address first
        explicit = address or self._address_hint
        if explicit:
            try:
                inst = self.rm.open_resource(explicit)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000
                
                # Verify device identity
                idn = inst.query("*IDN?").strip()
                if "DP832" not in idn and "DP8" not in idn:
                    inst.close()
                    raise ConnectionError(
                        _ERROR_STYLE + f"Device at '{explicit}' is not a DP832 (IDN='{idn}')."
                    )
                
                self.instrument = inst
                self.address = explicit
            except pyvisa.VisaIOError as e:
                raise ConnectionError(_ERROR_STYLE + f"Failed to connect to '{explicit}': {e}")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE + f"Unexpected error connecting to '{explicit}': {e}")
        
        # 2) Auto-detect by scanning resources
        if self.instrument is None:
            try:
                resources = self.rm.list_resources()
            except pyvisa.VisaIOError as e:
                raise ConnectionError(_ERROR_STYLE + f"PyVISA is not able to find any devices: {e}")
            
            # Look for DP8 in resource name
            dp8_resources = [elem for elem in resources if 'DP8' in elem]
            
            if len(dp8_resources) == 0:
                raise ConnectionError(_ERROR_STYLE + "DP832 not found")
            
            try:
                self.address = dp8_resources[0]
                inst = self.rm.open_resource(self.address)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000
                self.instrument = inst
            except pyvisa.VisaIOError as e:
                raise ConnectionError(_ERROR_STYLE + f"Failed to connect to auto-detected device: {e}")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE + f"Unexpected error during auto-detection: {e}")
        
        # 3) Initialize device
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Failed to establish connection to DP832")
        
        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to {self.address}")
    
    def disconnect(self) -> None:
        """Close the connection to the device."""
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from DP832 at {self.address}")
                self.instrument = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to DP832")
    
    def get(self, item: str, channel: int = 1) -> float:
        """
        Retrieve measurement value by name.
        
        Args:
            item: Measurement item name (case-insensitive)
                  Valid values: 'VOLT', 'CURR'
            channel: Channel number (1, 2, or 3)
            
        Returns:
            Measurement value
            
        Raises:
            ValueError: If invalid item requested
            ConnectionError: If not connected to device
            
        Example:
            >>> voltage = ps.get('VOLT', channel=1)
            >>> current = ps.get('CURR', channel=2)
        """
        self._chk()

        item_upper = item.strip().upper()
        
        items = {
            "VOLT": lambda: self.measure_voltage(channel),
            "CURR": lambda: self.measure_current(channel)
        }
        
        if item_upper not in items:
            raise ValueError(
                _ERROR_STYLE + f"Invalid item '{item}'. "
                f"Valid items: {', '.join(items.keys())}"
            )

        return items[item_upper]()

    def select_output(self, chan: int) -> None:
        """
        Select output channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def toggle_output(self, chan: int, state: Union[int, str]) -> None:
        """
        Turn channel output on or off.
        
        Args:
            chan: Channel number (1, 2, or 3)
            state: 1/'ON' to turn on, 0/'OFF' to turn off
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        
        if state == 1 or state == 'ON':
            print('\r' + Back.WHITE + Fore.BLACK + f'Rigol DP832 Power Supply Channel {chan}:\t'
                  + Back.GREEN + ' ON ' + Back.BLUE + Fore.WHITE 
                  + f"  {self.get_voltage(chan):.2f} V | {self.get_current(chan):.2f} A   ")
            command = f':OUTP CH{chan},1'
        else:
            print('\r' + Back.WHITE + Fore.BLACK + f'Rigol DP832 Power Supply Channel {chan}:\t'
                  + Back.RED + ' OFF ')
            command = f':OUTP CH{chan},0'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def set_voltage(self, chan: int, val: float) -> None:
        """
        Set channel voltage.
        
        Args:
            chan: Channel number (1, 2, or 3)
            val: Voltage value to set
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        time.sleep(_DELAY)
        command = f':VOLT {val}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def set_current(self, chan: int, val: float) -> None:
        """
        Set channel current limit.
        
        Args:
            chan: Channel number (1, 2, or 3)
            val: Current value to set
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        time.sleep(_DELAY)
        command = f':CURR {val}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def get_voltage(self, chan: int) -> float:
        """
        Get the configured voltage setpoint for a channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Returns:
            Configured voltage value
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        command = ':VOLT?'
        value = self.instrument.query(command)
        time.sleep(_DELAY)
        return float(value)

    def get_current(self, chan: int) -> float:
        """
        Get the configured current limit setpoint for a channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Returns:
            Configured current value
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        command = ':CURR?'
        value = self.instrument.query(command)
        time.sleep(_DELAY)
        return float(value)

    def set_ovp(self, chan: int, val: float) -> None:
        """
        Set over-voltage protection level.
        
        Args:
            chan: Channel number (1, 2, or 3)
            val: Protection voltage level
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        time.sleep(_DELAY)
        command = f':VOLT:PROT {val}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def toggle_ovp(self, state: str) -> None:
        """
        Enable or disable over-voltage protection.
        
        Args:
            state: 'ON' or 'OFF'
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':VOLT:PROT:STAT {state}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def set_ocp(self, chan: int, val: float) -> None:
        """
        Set over-current protection level.
        
        Args:
            chan: Channel number (1, 2, or 3)
            val: Protection current level
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':INST:NSEL {chan}'
        self.instrument.write(command)
        time.sleep(_DELAY)
        command = f':CURR:PROT {val}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def toggle_ocp(self, state: str) -> None:
        """
        Enable or disable over-current protection.
        
        Args:
            state: 'ON' or 'OFF'
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':CURR:PROT:STAT {state}'
        self.instrument.write(command)
        time.sleep(_DELAY)

    def measure_voltage(self, chan: int = 1) -> float:
        """
        Measure actual output voltage on a channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Returns:
            Measured voltage value
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':MEAS:VOLT? CH{chan}'
        volt = self.instrument.query(command)
        volt = float(volt)
        time.sleep(_DELAY)
        return volt

    def measure_current(self, chan: int = 1) -> float:
        """
        Measure actual output current on a channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Returns:
            Measured current value
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':MEAS:CURR? CH{chan}'
        curr = self.instrument.query(command)
        curr = float(curr)
        time.sleep(_DELAY)
        return curr

    def measure_power(self, chan: int = 1) -> float:
        """
        Measure actual output power on a channel.
        
        Args:
            chan: Channel number (1, 2, or 3)
            
        Returns:
            Measured power value (watts)
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':MEAS:POWE? CH{chan}'
        power = self.instrument.query(command)
        power = float(power)
        time.sleep(_DELAY)
        return power

    def reset(self) -> None:
        """
        Reset the device to default state.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        self.instrument.write("*RST")

