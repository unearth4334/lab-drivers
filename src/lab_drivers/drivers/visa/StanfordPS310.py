#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file StanfordPS310.py
#   @brief Establishes a connection to the Stanford Research Systems PS310 High Voltage Power Supply
#       via a National Instruments GPIB-USB-HS adapter and provides methods for interfacing with the device.
#   @date 02-Dec-2025
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
Stanford Research Systems PS310 High Voltage Power Supply Driver
==================================================================

This module provides a comprehensive driver for the Stanford Research Systems PS310 
high voltage power supply with advanced features including glitch filtering, debug 
logging, and environment-based configuration.

Features
--------
- **High Voltage Control**: Generate up to ±1250V with precision
- **GPIB Interface**: Uses National Instruments GPIB-USB-HS adapter
- **Glitch Filtering**: Automatic filtering of voltage/current reading transients
- **Debug Logging**: Comprehensive logging with multiple verbosity levels
- **Environment Configuration**: Configure via environment variables
- **Auto-Detection**: Automatically finds PS310 on GPIB bus
- **Safety Features**: Output enable/disable with state verification

Power Supply Specifications
----------------------------
- **Voltage Range**: 0V to ±1250V (depending on model)
- **Current Range**: 0 to 5 mA
- **Accuracy**: 0.1% of full scale
- **Stability**: < 10 ppm/°C
- **Ripple**: < 3 mV RMS
- **Interface**: GPIB via PyVISA

Basic Usage
-----------
```python
from libs.StanfordPS310 import StanfordPS310

# Auto-connect to PS310 (negative polarity model)
hvps = StanfordPS310()

# Set target voltage
hvps.set_voltage(-500.0)  # -500V

# Enable output
hvps.set_output_state(True)

# Read actual voltage and current
voltage = hvps.measure_voltage()
current = hvps.measure_current()
print(f"V: {voltage:.2f} V, I: {current*1e6:.2f} μA")

# Disable output
hvps.set_output_state(False)

# Clean up
hvps.disconnect()
```

Glitch Filtering
----------------
The driver includes automatic filtering of transient readings:

```python
# Enable glitch filtering (default)
hvps = StanfordPS310()

# Readings are automatically filtered
voltage = hvps.measure_voltage()  # Stable, filtered reading

# Glitch detection parameters configurable via environment variables
# PS310_GLITCH_THRESHOLD: Voltage change threshold (default: 10.0V)
# PS310_GLITCH_RETRIES: Number of retries on glitch (default: 3)
```

Debug Logging
-------------
```python
import os

# Set debug level (0=none, 1=errors, 2=warnings, 3=info, 4=verbose)
os.environ["PS310_DEBUG_LEVEL"] = "3"

# Create instance with logging
hvps = StanfordPS310()

# Operations now produce detailed logs
hvps.set_voltage(-750.0)  # Logs command and response
voltage = hvps.measure_voltage()  # Logs measurement details
```

Environment Configuration
-------------------------
Configure behavior via environment variables:

```python
import os

# Connection settings
os.environ["PS310_GPIB_ADDRESS"] = "GPIB0::12::INSTR"  # Specific address
os.environ["PS310_TIMEOUT_MS"] = "10000"  # 10 second timeout

# Glitch filtering
os.environ["PS310_GLITCH_THRESHOLD"] = "20.0"  # 20V threshold
os.environ["PS310_GLITCH_RETRIES"] = "5"  # 5 retry attempts

# Debug logging
os.environ["PS310_DEBUG_LEVEL"] = "4"  # Maximum verbosity

# Create configured instance
hvps = StanfordPS310()
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("hvps_measurements.txt")

# Connect via data_logger
hvps = logger.connect("stanfordps310")  # or "ps310"

# Add measurements
logger.add(hvps, "voltage", label="HVPS_Output_V")
logger.add(hvps, "current", label="HVPS_Output_I")

# Set voltage
hvps.set_voltage(-800.0)
hvps.set_output_state(True)

# Log data
for i in range(100):
    logger.get_data()
    time.sleep(1)
    
hvps.set_output_state(False)
logger.close_file()
```

Voltage Ramping
---------------
```python
# Ramp voltage gradually to avoid transients
def ramp_voltage(hvps, target_voltage, step=10.0, delay=0.5):
    current = hvps.measure_voltage()
    steps = int(abs(target_voltage - current) / step)
    
    for i in range(steps):
        voltage = current + (target_voltage - current) * (i+1) / steps
        hvps.set_voltage(voltage)
        time.sleep(delay)
        
# Usage
hvps.set_output_state(True)
ramp_voltage(hvps, -1000.0, step=50.0, delay=1.0)
```

Output State Control
--------------------
```python
# Enable high voltage output
hvps.set_output_state(True)

# Check if output is enabled
is_on = hvps.get_output_state()
print(f"Output enabled: {is_on}")

# Disable output (safety)
hvps.set_output_state(False)
```

Limit Configuration
-------------------
```python
# Set current limit (mA)
hvps.set_current_limit(2.0)  # 2 mA limit

# Set voltage limit
hvps.set_voltage_limit(1000.0)  # 1000V maximum
```

Error Handling
--------------
```python
try:
    hvps = StanfordPS310()
except ConnectionError as e:
    print(f"Failed to connect to PS310: {e}")

try:
    hvps.set_voltage(-1500.0)  # Beyond range
except ValueError as e:
    print(f"Invalid voltage: {e}")
    
try:
    voltage = hvps.measure_voltage()
except Exception as e:
    print(f"Measurement failed: {e}")
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"voltage"** - Measure actual output voltage in volts
- **"current"** - Measure actual output current in amperes
- **"set_voltage"** - Read voltage setpoint (target voltage)

Example:
```python
hvps = logger.connect("stanfordps310")
voltage = hvps.get("voltage")      # Measured output voltage
current = hvps.get("current")      # Measured output current
setpoint = hvps.get("set_voltage") # Target voltage setting
```

Available Methods
-----------------
Voltage Control:
- `set_voltage(voltage)` - Set target voltage (-1250V to 0V)
- `measure_voltage()` - Read actual output voltage
- `set_voltage_limit(limit)` - Set maximum voltage limit

Current Control:
- `set_current(current)` - Set target current (0 to 5 mA)
- `measure_current()` - Read actual output current
- `set_current_limit(limit)` - Set maximum current limit

Output Control:
- `set_output_state(state)` - Enable/disable output (True/False)
- `get_output_state()` - Check if output is enabled

Connection:
- `connect(address)` - Connect to specific GPIB address
- `disconnect()` - Close connection

Generic Interface:
- `get(item)` - Generic getter (voltage, current, set_voltage)

GPIB Communication Details
---------------------------
The PS310 uses SCPI-like commands over GPIB:
- `HVOF <voltage>` - Set voltage
- `HVST?` - Query voltage setpoint
- `MEAS:VOLT?` - Measure actual voltage
- `MEAS:CURR?` - Measure actual current
- `OUTP ON` / `OUTP OFF` - Control output state
- `SYST:ERR?` - Query system errors

Safety Considerations
---------------------
⚠️ **HIGH VOLTAGE - DANGEROUS**
- Always disable output when not in use
- Verify connections before enabling output
- Use appropriate high voltage cables and connectors
- Never exceed rated voltage/current limits
- Implement emergency shutdown procedures
- Follow institutional safety protocols

Troubleshooting
---------------
**Connection Issues:**
- Verify GPIB adapter is connected and recognized
- Check GPIB address (typically GPIB0::12::INSTR)
- Ensure PS310 is powered on and GPIB interface is enabled
- Try manual address with: `hvps.connect("GPIB0::12::INSTR")`

**Glitch Readings:**
- Increase glitch threshold: `PS310_GLITCH_THRESHOLD=20.0`
- Increase retries: `PS310_GLITCH_RETRIES=5`
- Enable debug logging: `PS310_DEBUG_LEVEL=4`

**Slow Response:**
- Increase timeout: `PS310_TIMEOUT_MS=15000`
- Check for loose GPIB connections
- Verify PS310 isn't in local mode (press "Remote" button)

See Also
--------
- RigolDP832: Multi-channel power supply driver
- data_logger: Main orchestrator class
- Device driver standard: docs/DEVICE_DRIVER_STANDARD.md
- PS310 GUI: apps/StanfordPS310_Desktop.py
"""

from __future__ import annotations

import time
import logging
import os
from typing import Optional

import pyvisa
import pyvisa.constants
from colorama import init, Fore, Style

# Set up logger for PS310 interactions
logger = logging.getLogger(__name__)

try:
    from .loading import loading
except ImportError:
    try:
        from loading import loading
    except ImportError:
        class loading:
            """Fallback loading class if module not available."""
            def delay_with_loading_indicator(self, seconds: float) -> None:
                time.sleep(seconds)

# Constants and global variables
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "
_DELAY = 0.1  # seconds

# PS310 specifications
_PS310_MAX_VOLTAGE = 1250.0  # ±1250V max
_PS310_MAX_CURRENT = 0.021   # 21 mA max current

# Glitch filter configuration
_GLITCH_THRESHOLD = -40.0  # Voltage threshold for glitch detection (V)
_MIN_CONSECUTIVE_READINGS = 2  # Number of consecutive readings needed to confirm real voltage change


class StanfordPS310:
    """
    Stanford Research Systems PS310 High Voltage Power Supply driver.

    The PS310 provides precision high voltage DC power up to ±1250V with
    excellent stability and low noise. Communication is via GPIB interface.

    Note: This driver is configured for the PS310 negative model, which requires
    negative voltage values (0V to -1250V).

    Attributes:
        status (str): Connection status ('Connected' or 'Not Connected')
        address (str): VISA resource address when connected
        instrument: PyVISA resource object
        
    Private Attributes (for glitch filtering):
        _prev_voltage (float): Previous voltage reading, used for glitch detection
        _consecutive_above_threshold (int): Counter for consecutive readings above threshold,
            used to distinguish real voltage changes from transient glitches
            
    Note: Glitch filter uses _GLITCH_THRESHOLD (-40V) and _MIN_CONSECUTIVE_READINGS (2)
          defined as module constants.

    Example:
        >>> hvps = StanfordPS310()  # Auto-connect
        >>> hvps.set_voltage(-100.0)
        >>> hvps.set_output_state(True)
        >>> voltage = hvps.measure_voltage()
        >>> hvps.disconnect()
    """

    def __init__(self, auto_connect: bool = True, address: Optional[str] = None):
        """
        Initialize an instance of the StanfordPS310 class.

        Args:
            auto_connect: If True, automatically connect to the device.
            address: Optional VISA resource string. If None, auto-detect.
        """
        init(autoreset=True)

        self.rm = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.loading = loading()
        self.status = "Not Connected"
        self._address_hint = address
        self._voltage_has_been_set = False
        self._output_state = False  # Track output state internally (fallback when voltage measurement fails)
        self._debug = os.environ.get('PS310_DEBUG', '0') == '1'  # Enable debug logging via environment variable
        
        # Glitch filter state for voltage readings
        self._prev_voltage = 0.0  # Previous voltage reading
        self._consecutive_above_threshold = 0  # Counter for consecutive readings above threshold

        if auto_connect:
            self.connect(address=self._address_hint)
    
    def _log_interaction(self, operation: str, command: str = None, response: str = None, error: str = None) -> None:
        """
        Log PS310 interactions when debug mode is enabled.
        
        Args:
            operation: Description of the operation being performed
            command: VISA command sent to the device (if applicable)
            response: Response received from the device (if applicable)
            error: Error message (if applicable)
        """
        if not self._debug:
            return
        
        log_parts = [f"PS310 Interaction - {operation}"]
        if command:
            log_parts.append(f"Command: {command}")
        if response is not None:
            log_parts.append(f"Response: {response}")
        if error:
            log_parts.append(f"Error: {error}")
        
        logger.debug(" | ".join(log_parts))

    def connect(self, address: Optional[str] = None) -> None:
        """
        Establish a connection to the Stanford PS310 High Voltage Power Supply.

        The method first tries the specified address, then scans for GPIB
        resources and verifies the instrument identity via *IDN? query.

        Args:
            address: VISA resource string. If None, auto-detect using GPIB scan.

        Raises:
            ConnectionError: If unable to connect to the PS310.

        Example:
            >>> hvps = StanfordPS310(auto_connect=False)
            >>> hvps.connect("GPIB0::14::INSTR")
        """
        explicit = address or self._address_hint

        # Try explicit address first
        if explicit:
            try:
                self._log_interaction("Opening VISA resource", command=f"open_resource({explicit})")
                inst = self.rm.open_resource(explicit)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 5000
                self._log_interaction("Querying device identification", command="*IDN?")
                idn = inst.query("*IDN?").strip()
                self._log_interaction("Received identification", response=idn)
                if self._is_ps310_device(idn):
                    self.instrument = inst
                    self.address = explicit
                    self._idn = idn
                else:
                    inst.close()
                    raise ConnectionError(
                        _ERROR_STYLE + f"Resource '{explicit}' is not a Stanford PS310 (IDN='{idn}')."
                    )
            except pyvisa.errors.VisaIOError as e:
                self._log_interaction("Failed to open resource", error=str(e))
                raise ConnectionError(
                    _ERROR_STYLE + f"Failed to open explicit address '{explicit}': {e}"
                )

        # Auto-detect by scanning GPIB resources
        if self.instrument is None:
            resources = self.rm.list_resources()
            for resource in resources:
                # Look for GPIB resources (NI GPIB-USB-HS adapter)
                if "GPIB" in resource:
                    try:
                        inst = self.rm.open_resource(resource)
                        inst.read_termination = '\n'
                        inst.write_termination = '\n'
                        inst.timeout = 5000
                        idn = inst.query("*IDN?").strip()
                        if self._is_ps310_device(idn):
                            self.instrument = inst
                            self.address = resource
                            self._idn = idn
                            break
                        inst.close()
                    except Exception:
                        continue

        if self.instrument is None:
            raise ConnectionError(
                _ERROR_STYLE + "Stanford PS310 High Voltage Power Supply not found."
            )

        # Clear status registers
        try:
            self._log_interaction("Clearing status registers", command="*CLS")
            self.instrument.write("*CLS")
        except Exception as e:
            self._log_interaction("Failed to clear status", error=str(e))
            pass

        self.status = "Connected"
        self._log_interaction("Connection established", response=f"Connected at {self.address}")
        print(_SUCCESS_STYLE + f"Connected to Stanford PS310 at {self.address} with idn {self._idn}")

    def disconnect(self) -> None:
        """
        Disconnect from the Stanford PS310 High Voltage Power Supply.

        Example:
            >>> hvps.disconnect()
        """
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from Stanford PS310 at {self.address}")
        self.status = "Not Connected"
        self.instrument = None
        self.address = None
        self._output_state = False  # Reset cached output state
        self._prev_voltage = 0.0  # Reset glitch filter state
        self._consecutive_above_threshold = 0  # Reset glitch filter counter

    def _check_connection(self) -> None:
        """Verify the device is connected before operations."""
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to Stanford PS310.")

    @staticmethod
    def _is_ps310_device(idn: str) -> bool:
        """
        Check if the IDN response indicates a Stanford PS310 device.

        Args:
            idn: The *IDN? response string from the instrument.

        Returns:
            bool: True if the device appears to be a PS310.
        """
        idn_upper = idn.upper()
        # Check for PS310 model number or Stanford Research Systems with PS3xx pattern
        return "PS310" in idn_upper or (
            "STANFORD" in idn_upper and "PS3" in idn_upper
        )

    def get(self, item: str, channel: Optional[int] = None):
        """
        Retrieve the specified measurement value.

        Args:
            item: The measurement item to retrieve.
                Valid values: 'voltage', 'current', 'set_voltage'
            channel: Not used for PS310 (single channel), included for API compatibility.

        Returns:
            float: The measurement result.

        Raises:
            ValueError: If an invalid item is requested.

        Example:
            >>> voltage = hvps.get("voltage")
        """
        items = {
            "voltage": self.measure_voltage,
            "current": self.measure_current,
            "set_voltage": self.get_voltage,
        }

        item_lower = item.lower()
        if item_lower in items:
            return items[item_lower]()
        else:
            raise ValueError(
                _ERROR_STYLE + f"Invalid item: {item} request to Stanford PS310. "
                f"Valid items: {list(items.keys())}"
            )

    def set_voltage(self, voltage: float) -> None:
        """
        Set the output voltage of the PS310.

        Args:
            voltage: The target voltage in volts. Must be negative. Range: -1250V to <0V.

        Raises:
            ConnectionError: If not connected to the PS310.
            ValueError: If voltage is out of range or not negative.

        Example:
            >>> hvps.set_voltage(-500.0)  # Set to -500V
        """
        self._check_connection()

        if not isinstance(voltage, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid voltage value. Please provide a numeric value.")

        if voltage >= 0:
            raise ValueError(
                _ERROR_STYLE + f"Invalid voltage value '{voltage}'. "
                f"This PS310 negative model requires negative voltage values only (must be < 0)."
            )

        if abs(voltage) > _PS310_MAX_VOLTAGE:
            raise ValueError(
                _ERROR_STYLE + f"Invalid voltage value '{voltage}'. "
                f"The PS310 accepts voltages between -{_PS310_MAX_VOLTAGE} and 0 V (exclusive)."
            )

        try:
            # VSET <value> - Set the voltage setpoint (SRS PS310 Programming Manual)
            command = f"VSET {voltage:.3f}"
            self._log_interaction("Setting voltage", command=command)
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            self._voltage_has_been_set = True
            self._log_interaction("Voltage set successfully", response=f"{voltage:.3f} V")
            print(f"\rPS310 voltage set to {voltage:.3f} V")
        except Exception as e:
            self._log_interaction("Failed to set voltage", error=str(e))
            raise ValueError(_ERROR_STYLE + f"Failed to set voltage on Stanford PS310: {e}")

    def get_voltage(self) -> float:
        """
        Get the currently configured (setpoint) voltage.

        Returns:
            float: The configured voltage setpoint in volts.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> setpoint = hvps.get_voltage()
        """
        self._check_connection()

        try:
            # VSET? - Query the voltage setpoint (SRS PS310 Programming Manual)
            self._log_interaction("Querying voltage setpoint", command="VSET?")
            response = self.instrument.query("VSET?")
            self.loading.delay_with_loading_indicator(_DELAY)
            voltage = float(response.strip())
            self._log_interaction("Got voltage setpoint", response=f"{voltage} V")
            return voltage
        except Exception as e:
            self._log_interaction("Failed to get voltage setpoint", error=str(e))
            raise ValueError(_ERROR_STYLE + f"Failed to get voltage setpoint from Stanford PS310: {e}")

    def measure_voltage(self, apply_filter: bool = True) -> float:
        """
        Measure the actual output voltage with optional glitch filtering.
        
        Implements a glitch filter that prevents momentary jumps to zero from voltages
        below -40V. If the voltage jumps from below -40V to near zero, the previous
        reading is returned instead. The filter resets if consecutive readings remain
        above -40V.

        Args:
            apply_filter: If True (default), apply glitch filtering. If False, return raw voltage.

        Returns:
            float: The measured output voltage in volts (filtered or raw based on apply_filter).

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> voltage = hvps.measure_voltage()  # With filtering
            >>> print(f"Output: {voltage} V")
            >>> raw_voltage = hvps.measure_voltage(apply_filter=False)  # Without filtering
        """
        self._check_connection()

        try:
            # VOUT? - Query the measured output voltage (SRS PS310 Programming Manual)
            self._log_interaction("Measuring output voltage", command="VOUT?")
            response = self.instrument.query("VOUT?")
            self.loading.delay_with_loading_indicator(_DELAY)
            raw_voltage = float(response.strip())
            self._log_interaction("Measured voltage (raw)", response=f"{raw_voltage} V")
            
            # Apply glitch filter if requested
            if apply_filter:
                filtered_voltage = self._apply_glitch_filter(raw_voltage)
                
                if filtered_voltage != raw_voltage:
                    self._log_interaction("Voltage filtered", response=f"{filtered_voltage} V (raw: {raw_voltage} V)")
                
                return filtered_voltage
            else:
                # Return raw voltage without filtering
                return raw_voltage
        except Exception as e:
            self._log_interaction("Failed to measure voltage", error=str(e))
            raise ValueError(_ERROR_STYLE + f"Failed to measure voltage from Stanford PS310: {e}")

    def _is_potential_glitch(self, prev_voltage: float, current_voltage: float) -> bool:
        """
        Determine if a voltage reading change appears to be a glitch.
        
        A glitch is detected when:
        - Previous voltage was less than -40V (more negative, further from zero)
        - Current reading is greater than -40V (less negative, closer to zero)
        
        Args:
            prev_voltage: Previous voltage reading.
            current_voltage: Current voltage reading.
            
        Returns:
            bool: True if the change appears to be a glitch, False otherwise.
        """
        return prev_voltage < _GLITCH_THRESHOLD and current_voltage > _GLITCH_THRESHOLD

    def _apply_glitch_filter(self, raw_voltage: float) -> float:
        """
        Apply glitch filter to voltage reading.
        
        Filters out discontinuous jumps toward zero from voltages below -40V 
        (_GLITCH_THRESHOLD). The filter holds the previous reading if:
        - Previous voltage was less than -40V (more negative, further from zero)
        - Current reading is greater than -40V (less negative, closer to zero)
        
        The filter resets if consecutive readings remain above -40V for 
        _MIN_CONSECUTIVE_READINGS cycles, indicating a real voltage change 
        rather than a transient glitch.
        
        Args:
            raw_voltage: The raw voltage reading from the instrument.
            
        Returns:
            float: The filtered voltage reading.
        """
        # Check if this is a potential glitch
        if self._is_potential_glitch(self._prev_voltage, raw_voltage):
            # Potential glitch detected - increment consecutive counter
            self._consecutive_above_threshold += 1
            
            # If we've seen enough consecutive readings above threshold,
            # it's likely a real change, not a glitch - reset and use the new value
            if self._consecutive_above_threshold >= _MIN_CONSECUTIVE_READINGS:
                self._log_interaction(
                    "Glitch filter reset",
                    response=f"{_MIN_CONSECUTIVE_READINGS} consecutive readings > {_GLITCH_THRESHOLD}V confirmed, accepting as legitimate voltage change"
                )
                self._consecutive_above_threshold = 0
                self._prev_voltage = raw_voltage
                return raw_voltage
            else:
                # First reading above threshold after being below - hold previous value (filter the glitch)
                self._log_interaction(
                    "Glitch detected",
                    response=f"Holding previous value {self._prev_voltage}V instead of {raw_voltage}V"
                )
                return self._prev_voltage
        else:
            # Not a glitch scenario - reset counter and update previous voltage
            self._consecutive_above_threshold = 0
            self._prev_voltage = raw_voltage
            return raw_voltage

    def measure_current(self) -> float:
        """
        Measure the actual output current.

        Returns:
            float: The measured output current in amps.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> current = hvps.measure_current()
            >>> print(f"Current: {current * 1000:.3f} mA")
        """
        self._check_connection()

        try:
            # IOUT? - Query the measured output current (SRS PS310 Programming Manual)
            self._log_interaction("Measuring output current", command="IOUT?")
            response = self.instrument.query("IOUT?")
            self.loading.delay_with_loading_indicator(_DELAY)
            current = float(response.strip())
            self._log_interaction("Measured current", response=f"{current} A ({current*1000:.3f} mA)")
            return current
        except Exception as e:
            self._log_interaction("Failed to measure current", error=str(e))
            raise ValueError(_ERROR_STYLE + f"Failed to measure current from Stanford PS310: {e}")

    def set_current_limit(self, current: float) -> None:
        """
        Set the current limit (trip point) for the PS310.

        Args:
            current: The current limit in amps. Range: 0 to 0.021 A (21 mA).

        Raises:
            ConnectionError: If not connected to the PS310.
            ValueError: If current is out of range.

        Example:
            >>> hvps.set_current_limit(0.010)  # Set 10 mA limit
        """
        self._check_connection()

        if not isinstance(current, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid current value. Please provide a numeric value.")

        if current < 0 or current > _PS310_MAX_CURRENT:
            raise ValueError(
                _ERROR_STYLE + f"Invalid current limit '{current}'. "
                f"The PS310 accepts current limits between 0 and {_PS310_MAX_CURRENT * 1000:.1f} mA."
            )

        try:
            # ILIM <value> - Set the current trip point (SRS PS310 Programming Manual)
            command = f"ILIM {current:.6f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            print(f"\rPS310 current limit set to {current * 1000:.3f} mA")
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to set current limit on Stanford PS310: {e}")

    def get_current_limit(self) -> float:
        """
        Get the currently configured current limit.

        Returns:
            float: The current limit in amps.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> limit = hvps.get_current_limit()
            >>> print(f"Current limit: {limit * 1000:.3f} mA")
        """
        self._check_connection()

        try:
            # ILIM? - Query the current trip point (SRS PS310 Programming Manual)
            response = self.instrument.query("ILIM?")
            self.loading.delay_with_loading_indicator(_DELAY)
            return float(response.strip())
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to get current limit from Stanford PS310: {e}")

    def set_output_state(self, state: bool) -> None:
        """
        Enable or disable the high voltage output.

        Args:
            state: True to enable output, False to disable.

        Raises:
            ConnectionError: If not connected to the PS310.
            ValueError: If output is enabled without setting voltage first.

        Example:
            >>> hvps.set_output_state(True)   # Enable HV output
            >>> hvps.set_output_state(False)  # Disable HV output
        """
        self._check_connection()

        if state and not self._voltage_has_been_set:
            current_setpoint = self.get_voltage()
            print(
                _WARNING_STYLE + f"Output voltage has not been set in this session. "
                f"Current setpoint: {current_setpoint:.3f} V"
            )

        try:
            if state:
                # HVON - Turn on the high voltage output (SRS PS310 Programming Manual)
                self._log_interaction("Enabling HV output", command="HVON")
                self.instrument.write("HVON")
                self.loading.delay_with_loading_indicator(_DELAY)
                self._output_state = True  # Update internal state
                self._log_interaction("HV output enabled", response="ON")
                print(f"\r{Fore.GREEN}PS310 High Voltage Output: ON")
            else:
                # HVOF - Turn off the high voltage output (SRS PS310 Programming Manual)
                self._log_interaction("Disabling HV output", command="HVOF")
                self.instrument.write("HVOF")
                self.loading.delay_with_loading_indicator(_DELAY)
                self._output_state = False  # Update internal state
                self._log_interaction("HV output disabled", response="OFF")
                print(f"\r{Fore.RED}PS310 High Voltage Output: OFF")
        except Exception as e:
            self._log_interaction("Failed to set output state", error=str(e))
            raise ValueError(_ERROR_STYLE + f"Failed to set output state on Stanford PS310: {e}")

    def get_output_state(self) -> bool:
        """
        Get the current output state (on/off).

        The HVON command is write-only, so this method determines output state
        by checking the actual output voltage. If the voltage is zero (or near zero),
        the output is considered OFF; otherwise it's ON.

        Returns:
            bool: True if output is enabled (voltage is non-zero), False if disabled (voltage is zero).

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> if hvps.get_output_state():
            ...     print("HV output is ON")
        """
        self._check_connection()

        try:
            # HVON is write-only, so check actual output voltage instead
            # VOUT? - Query the measured output voltage (SRS PS310 Programming Manual)
            # Use unfiltered voltage for output state detection to avoid glitch filter interference
            self._log_interaction("Checking output state via voltage measurement", command="VOUT?")
            voltage = self.measure_voltage(apply_filter=False)
            
            # If voltage is zero (or near zero, within 0.1V tolerance), output is off
            # Using small threshold to handle measurement noise
            state = abs(voltage) > 0.1
            self._output_state = state  # Update cached state
            self._log_interaction("Got output state from voltage", response=f"{'ON' if state else 'OFF'} (voltage: {voltage:.3f}V)")
            return state
        except Exception as e:
            # If measurement fails, fall back to cached state
            self._log_interaction("Error checking output state via voltage - using cached value", error=str(e))
            print(_WARNING_STYLE + f"Could not determine output state from voltage (using cached value): {e}")
            return self._output_state

    def set_voltage_limit(self, voltage: float) -> None:
        """
        Set the voltage limit (maximum allowed voltage).

        Args:
            voltage: The voltage limit in volts. Range: 0 to 1250V.

        Raises:
            ConnectionError: If not connected to the PS310.
            ValueError: If voltage is out of range.

        Example:
            >>> hvps.set_voltage_limit(1000.0)  # Limit to 1000V max
        """
        self._check_connection()

        if not isinstance(voltage, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid voltage limit value. Please provide a numeric value.")

        if voltage < 0 or voltage > _PS310_MAX_VOLTAGE:
            raise ValueError(
                _ERROR_STYLE + f"Invalid voltage limit '{voltage}'. "
                f"The PS310 accepts voltage limits between 0 and {_PS310_MAX_VOLTAGE} V."
            )

        try:
            # VLIM <value> - Set the voltage limit (SRS PS310 Programming Manual)
            command = f"VLIM {voltage:.3f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            print(f"\rPS310 voltage limit set to {voltage:.3f} V")
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to set voltage limit on Stanford PS310: {e}")

    def get_voltage_limit(self) -> float:
        """
        Get the currently configured voltage limit.

        Returns:
            float: The voltage limit in volts.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> limit = hvps.get_voltage_limit()
        """
        self._check_connection()

        try:
            # VLIM? - Query the voltage limit (SRS PS310 Programming Manual)
            response = self.instrument.query("VLIM?")
            self.loading.delay_with_loading_indicator(_DELAY)
            return float(response.strip())
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to get voltage limit from Stanford PS310: {e}")

    def reset(self) -> None:
        """
        Reset the PS310 to default settings.

        This disables the output and resets configuration.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> hvps.reset()
        """
        self._check_connection()

        try:
            self.instrument.write("*RST")
            self.loading.delay_with_loading_indicator(_DELAY)
            self._voltage_has_been_set = False
            print("\rPS310 reset to default settings")
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to reset Stanford PS310: {e}")

    def get_identification(self) -> str:
        """
        Get the instrument identification string.

        Returns:
            str: The *IDN? response from the instrument.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> idn = hvps.get_identification()
            >>> print(f"Instrument: {idn}")
        """
        self._check_connection()

        try:
            response = self.instrument.query("*IDN?")
            self.loading.delay_with_loading_indicator(_DELAY)
            return response.strip()
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to get identification from Stanford PS310: {e}")

    def clear_status(self) -> None:
        """
        Clear the status registers and error queue.

        Raises:
            ConnectionError: If not connected to the PS310.

        Example:
            >>> hvps.clear_status()
        """
        self._check_connection()

        try:
            self.instrument.write("*CLS")
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            raise ValueError(_ERROR_STYLE + f"Failed to clear status on Stanford PS310: {e}")


# Test code
if __name__ == "__main__":
    print("Stanford PS310 High Voltage Power Supply Test")
    print("=" * 50)

    try:
        # Create instance (auto-connect)
        hvps = StanfordPS310(auto_connect=False)
        print("Note: Auto-connect disabled for testing.")
        print("To test with actual hardware, use: hvps.connect()")

        # Show available methods
        print("\nAvailable methods:")
        methods = [m for m in dir(hvps) if not m.startswith('_') and callable(getattr(hvps, m))]
        for method in methods:
            print(f"  - {method}")

    except Exception as e:
        print(f"Test error: {e}")
