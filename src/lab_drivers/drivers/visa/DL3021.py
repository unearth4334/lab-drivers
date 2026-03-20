#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file DL3021.py
#   @brief Driver for DL3021 Electronic Load
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
DL3021 Programmable DC Electronic Load Driver
==============================================

This module provides a driver for the DL3021 programmable electronic load
with VISA connectivity for power supply testing and battery characterization.

Features
--------
- **Multiple Load Modes**: Constant current (CC), constant voltage (CV), 
  constant resistance (CR), constant power (CP)
- **Auto-Detection**: Automatically finds DL3021 on VISA bus
- **High Power**: Up to 150W load capacity
- **Precision Control**: Accurate current, voltage, and power settings
- **Measurement Capability**: Real-time voltage, current, and power monitoring

Basic Usage
-----------
```python
from libs.DL3021 import DL3021

# Auto-connect to electronic load
load = DL3021()

# Set constant current mode
load.set_mode("CC")
load.set_current(2.0)  # 2A load

# Enable load
load.set_output_state(True)

# Measure input voltage and current
voltage = load.measure_voltage()
current = load.measure_current()
power = load.measure_power()
print(f"V: {voltage:.3f}V, I: {current:.3f}A, P: {power:.3f}W")

# Disable load
load.set_output_state(False)
load.disconnect()
```

Load Modes
----------
```python
# Constant Current (CC) mode
load.set_mode("CC")
load.set_current(1.5)  # 1.5A

# Constant Voltage (CV) mode
load.set_mode("CV")
load.set_voltage(12.0)  # 12V

# Constant Resistance (CR) mode
load.set_mode("CR")
load.set_resistance(10.0)  # 10Ω

# Constant Power (CP) mode
load.set_mode("CP")
load.set_power(50.0)  # 50W
```

Battery Discharge Test
----------------------
```python
import time

# Configure for battery test
load.set_mode("CC")
load.set_current(1.0)  # 1A discharge
load.set_output_state(True)

# Monitor battery voltage during discharge
start_time = time.time()
while True:
    voltage = load.measure_voltage()
    elapsed = time.time() - start_time
    print(f"t={elapsed:.0f}s, V={voltage:.3f}V")
    
    if voltage < 10.5:  # Cutoff voltage
        break
    time.sleep(10)

load.set_output_state(False)
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("load_test.txt")

load = logger.connect("dl3021")

# Configure electronic load
load.set_mode("CC")
load.set_current(2.5)
load.set_output_state(True)

# Log measurements
logger.add(load, "voltage", label="Load_Voltage")
logger.add(load, "current", label="Load_Current")
logger.add(load, "power", label="Load_Power")

for i in range(100):
    logger.get_data()
    time.sleep(1)
    
load.set_output_state(False)
logger.close_file()
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"VOLT"** - Measure input voltage in volts
- **"CURR"** - Measure load current in amperes
- **"VOLT_AVG"** - Average voltage measurement (returns mean and stdev)
- **"CURR_AVG"** - Average current measurement (returns mean and stdev)

Example:
```python
load = logger.connect("dl3021")
voltage = load.get("VOLT")
current = load.get("CURR")
mean_v, stdev_v = load.get("VOLT_AVG")  # Returns tuple
```

Available Methods
-----------------
Load Control:
- `set_mode(mode)` - Set load mode (CC, CV, CR, CP)
- `set_current(current)` - Set current in CC mode (A)
- `set_voltage(voltage)` - Set voltage in CV mode (V)
- `set_resistance(resistance)` - Set resistance in CR mode (Ω)
- `set_power(power)` - Set power in CP mode (W)
- `set_output_state(state)` - Enable/disable load

Measurement:
- `measure_voltage()` - Read input voltage
- `measure_current()` - Read load current
- `measure_power()` - Read power dissipation
- `get(item)` - Generic getter (VOLT, CURR, VOLT_AVG, CURR_AVG)

Connection:
- `connect()` - Establish VISA connection
- `disconnect()` - Close connection

Technical Specifications
------------------------
- **Voltage Range**: 0-150V
- **Current Range**: 0-30A
- **Power Rating**: 150W (with cooling)
- **Current Resolution**: 0.1mA
- **Voltage Resolution**: 1mV
- **Interface**: USB, RS232 via PyVISA

See Also
--------
- RigolDP832: Programmable power supply
- data_logger: Main orchestrator class
- Device driver standard: docs/DEVICE_DRIVER_STANDARD.md
"""

from __future__ import annotations

import statistics
import time
from typing import Optional, Tuple, Union

import numpy
import pyvisa
from colorama import init, Fore, Back, Style


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
            def display_loading_bar(self, progress: float, loading_text: str = "") -> None:
                pass

# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.05

class DL3021:
    """
    Driver for DL3021 Programmable Electronic Load.
    
    This class provides methods for connecting to and controlling a
    DL3021 electronic load via VISA interface.
    
    Supports multiple operating modes:
    - CC (Constant Current)
    - CV (Constant Voltage)
    - CR (Constant Resistance)
    - CP (Constant Power)
    
    Attributes:
        rm: PyVISA ResourceManager instance
        address: Device VISA address
        instrument: Active connection handle
        status: Connection status ("Connected" or "Not Connected")
        loading: Loading indicator helper
        
    Example:
        >>> load = DL3021()
        >>> load.select_mode('CURR')
        >>> load.set_cc_current(1.0)
        >>> load.enable()
        >>> voltage = load.measure_voltage()
        >>> load.disable()
        >>> load.disconnect()
    """
    
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None):
        """
        Initialize DL3021 driver.
        
        Args:
            auto_connect: Automatically connect to device on initialization
            address: Optional explicit VISA address
        """
        init(autoreset=True)
        
        self.rm: Optional[pyvisa.ResourceManager] = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.status: str = "Not Connected"
        self.loading = loading()
        self._address_hint: Optional[str] = address

        if auto_connect:
            self.connect(address=address)

    
    def connect(self, address: Optional[str] = None) -> None:
        """
        Establish connection to DL3021 electronic load.
        
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
                if "DL3021" not in idn and "DL3" not in idn:
                    inst.close()
                    raise ConnectionError(
                        _ERROR_STYLE + f"Device at '{explicit}' is not a DL3021 (IDN='{idn}')."
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
            
            # Look for DL3 in resource name
            dl3_resources = [elem for elem in resources if 'DL3' in elem]
            
            if len(dl3_resources) == 0:
                raise ConnectionError(_ERROR_STYLE + "DL3021 not found")
            
            try:
                self.address = dl3_resources[0]
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
            raise ConnectionError(_ERROR_STYLE + "Failed to establish connection to DL3021")
        
        self.status = "Connected"
        print(_SUCCESS_STYLE + f"Connected to {self.address}")
    
    def disconnect(self) -> None:
        """Close the connection to the device."""
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from DL3021 at {self.address}")
                self.instrument = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to DL3021")
    
    def get(self, item: str, channel: int = 1) -> Union[float, Tuple[float, float]]:
        """
        Retrieve measurement value by name.
        
        Args:
            item: Measurement item name (case-insensitive)
                  Valid values: 'VOLT', 'CURR', 'VOLT_AVG', 'CURR_AVG'
            channel: Optional channel number (for compatibility, not used)
            
        Returns:
            Single float for instant measurements (VOLT, CURR)
            Tuple of (mean, stdev) for averaged measurements (VOLT_AVG, CURR_AVG)
            
        Raises:
            ValueError: If invalid item requested
            ConnectionError: If not connected to device
            
        Example:
            >>> voltage = load.get('VOLT')
            >>> mean, stdev = load.get('VOLT_AVG')
        """
        self._chk()

        item_upper = item.strip().upper()
        
        items = {
            "VOLT": self.measure_voltage,
            "CURR": self.measure_current,
            "VOLT_AVG": self.measure_volt_avg,
            "CURR_AVG": self.measure_current_avg
        }
        
        if item_upper not in items:
            raise ValueError(
                _ERROR_STYLE + f"Invalid item '{item}'. "
                f"Valid items: {', '.join(items.keys())}"
            )

        result = items[item_upper]()
        
        # Return statistics tuple for _AVG items, single float otherwise
        if '_AVG' in item_upper:
            return result  # Already a tuple (mean, stdev)
        else:
            return result  # Single float value
        

    def measure_voltage(self) -> float:
        """
        Measure voltage across the load.
        
        Returns:
            Voltage in volts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':MEAS:VOLT?'
        volt = self.instrument.query(command)
        volt = float(volt)
        self.loading.delay_with_loading_indicator(_DELAY)
        return volt

    def measure_current(self) -> float:
        """
        Measure current through the load.
        
        Returns:
            Current in amperes
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':MEAS:CURR?'
        curr = self.instrument.query(command)
        curr = float(curr)
        self.loading.delay_with_loading_indicator(_DELAY)
        return curr

    def measure_power(self) -> float:
        """
        Measure power dissipated by the load.
        
        Returns:
            Power in watts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':MEAS:POW?'
        power = self.instrument.query(command)
        power = float(power)
        self.loading.delay_with_loading_indicator(_DELAY)
        return power

    def measure_resistance(self) -> float:
        """
        Measure resistance of the load.
        
        Returns:
            Resistance in ohms
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':MEAS:RES?'
        res = self.instrument.query(command)
        res = float(res)
        self.loading.delay_with_loading_indicator(_DELAY)
        return res

    def set_slew_rate(self, val: float) -> None:
        """
        Set current slew rate.
        
        Args:
            val: Slew rate value
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:CURRENT:SLEW {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def is_enabled(self) -> str:
        """
        Check if load input is enabled.
        
        Returns:
            Status string
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:INPUT:STAT?'
        enabled = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return enabled

    def enable(self) -> None:
        """
        Enable the load input.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        mode = self.query_mode()
        if mode == 'CC':
            modeString = f' {mode} MODE | {self.get_cc_current():.2f} A   '
        elif mode == 'CR':
            modeString = f' {mode} MODE | {self.get_cr_resistance():.2f} OHM '
        elif mode == 'CV':
            modeString = f' {mode} MODE | {self.get_cv_voltage():.2f} V   '
        elif mode == 'CP':
            modeString = f' {mode} MODE | {self.get_cp_power():.2f} W   '
        else:
            modeString = f' {mode} MODE '
            
        print(Back.WHITE + Fore.BLACK + '\rProgrammable Load (DL3021):\t'
             + Back.GREEN + ' ON ' + Back.BLUE + Fore.WHITE + f"{modeString}")
        command = ':SOURCE:INPUT:STAT ON'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def disable(self) -> None:
        """
        Disable the load input.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        print(Back.WHITE + Fore.BLACK + '\rProgrammable Load (DL3021):\t' + Back.RED + ' OFF ')
        command = ':SOURCE:INPUT:STAT OFF'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def input_status(self) -> str:
        """
        Query and display the input status.
        
        Returns:
            Status string
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:INPUT:STAT?'
        result = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        mode = self.query_mode()

        print(Back.WHITE + Fore.BLACK + '\rProgrammable Load (DL3021):\t', end='')
        if result == 0:
            print(Back.RED + ' OFF ', end='')
        else:
            print(Back.GREEN + ' ON ', end='')
        if mode == 'CC':
            modeString = f' {mode} MODE | {self.get_cc_current():.2f} A   '
        elif mode == 'CR':
            modeString = f' {mode} MODE | {self.get_cr_resistance():.2f} OHM '
        elif mode == 'CV':
            modeString = f' {mode} MODE | {self.get_cv_voltage():.2f} V   '
        elif mode == 'CP':
            modeString = f' {mode} MODE | {self.get_cp_power():.2f} W   '
        else:
            modeString = f' {mode} MODE '
        print(Back.BLUE + Fore.WHITE + f"{modeString}")
        
        return result[0:(len(result) - 1)]

    def select_mode(self, mode: str) -> None:
        """
        Select operating mode.
        
        Args:
            mode: Operating mode ('CURR', 'RES', 'VOLT', 'POW')
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:FUNCTION {mode}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def query_mode(self) -> str:
        """
        Query current operating mode.
        
        Returns:
            Mode string ('CC', 'CR', 'CV', 'CP')
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:FUNCTION?'
        mode = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return mode[0:(len(mode) - 1)]

    def set_cc_current(self, val: float) -> None:
        """
        Set constant current mode value.
        
        Args:
            val: Current in amperes
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:CURRENT:LEV:IMM {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_cr_resistance(self, val: float) -> None:
        """
        Set constant resistance mode value.
        
        Args:
            val: Resistance in ohms
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:RES:LEV:IMM {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_cp_power(self, val: float) -> None:
        """
        Set constant power mode value.
        
        Args:
            val: Power in watts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:POWER:LEV:IMM {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_cv_voltage(self, val: float) -> None:
        """
        Set constant voltage mode value.
        
        Args:
            val: Voltage in volts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:VOLT:LEV:IMM {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def set_cp_ilim(self, val: float) -> None:
        """
        Set constant power mode current limit.
        
        Args:
            val: Current limit in amperes
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = f':SOURCE:POWER:ILIM {val}'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def get_cc_current(self) -> float:
        """
        Get constant current mode setpoint.
        
        Returns:
            Current in amperes
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:CURRENT:LEV:IMM?'
        value = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return float(value)
    
    def get_cr_resistance(self) -> float:
        """
        Get constant resistance mode setpoint.
        
        Returns:
            Resistance in ohms
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:RES:LEV:IMM?'
        value = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return float(value)

    def get_cp_power(self) -> float:
        """
        Get constant power mode setpoint.
        
        Returns:
            Power in watts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:POWER:LEV:IMM?'
        value = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return float(value)

    def get_cv_voltage(self) -> float:
        """
        Get constant voltage mode setpoint.
        
        Returns:
            Voltage in volts
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        command = ':SOURCE:VOLT:LEV:IMM?'
        value = self.instrument.query(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        return float(value)

    def measure_current_avg(self, n: int = 50) -> Tuple[float, float]:
        """
        Measure average current with statistics.
        
        Args:
            n: Number of readings to average (default: 50)
            
        Returns:
            Tuple of (mean, standard_deviation)
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        
        val = numpy.zeros(n)
        for x in range(n):
            self.loading.display_loading_bar(x / n, loading_text="Averaging measurements from DL3021 Load")
            self.loading.delay_with_loading_indicator(_DELAY)
            val[x] = self.measure_current()

        return (statistics.fmean(val), statistics.stdev(val))

    def measure_volt_avg(self, n: int = 10) -> Tuple[float, float]:
        """
        Measure average voltage with statistics.
        
        Args:
            n: Number of readings to average (default: 10)
            
        Returns:
            Tuple of (mean, standard_deviation)
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        
        val = numpy.zeros(n)
        for x in range(n):
            self.loading.display_loading_bar(x / n, loading_text="Averaging measurements from DL3021 Load")
            self.loading.delay_with_loading_indicator(_DELAY)
            val[x] = self.measure_voltage()

        return (statistics.fmean(val), statistics.stdev(val))
    
    def configure_output_sense(self, val: bool = True) -> None:
        """
        Configure output sense (4-wire sensing).
        
        Args:
            val: True to enable sense, False to disable
            
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        if val == True:
            command = ':OUTP:SENS ON'
        elif val == False:
            command = ':OUTP:SENS OFF'
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)

    def reset(self) -> None:
        """
        Reset the device to default state.
        
        Raises:
            ConnectionError: If not connected to device
        """
        self._chk()
        self.instrument.write("*RST")

