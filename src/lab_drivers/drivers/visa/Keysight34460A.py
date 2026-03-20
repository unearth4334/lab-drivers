#   @file Keysight34460A.py 
#   @brief Establishes a connection to the Keysight 34460A Multimeter
#       and provides methods for interfacing with the device.
#   @date 18-May-2023
#   @author Stefan Damkjar
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

# Imports

"""
Keysight 34460A 6.5-Digit Multimeter Driver
============================================

This module provides a driver for the Keysight (Agilent) 34460A digital multimeter,
a high-precision 6.5-digit benchtop DMM with VISA connectivity.

Features
--------
- **Auto-Detection**: Automatically finds 34460A using 'MY59' identifier
- **Standard Measurements**: DC/AC voltage, DC/AC current, 2-wire/4-wire resistance
- **High Precision**: 6.5-digit resolution for accurate measurements
- **VISA Interface**: Uses PyVISA for USB, LAN, or GPIB connectivity
- **Simple API**: Straightforward measurement methods with automatic configuration

Basic Usage
-----------
```python
from libs.Keysight34460A import Keysight34460A

# Auto-connect to 34460A
dmm = Keysight34460A()

# Take voltage measurement
voltage = dmm.measure_voltage()
print(f"Voltage: {voltage:.6f} V")

# Clean up
dmm.disconnect()
```

Manual Connection
-----------------
```python
# Connect manually without auto-connect
dmm = Keysight34460A(auto_connect=False)
dmm.connect()
```

Measurement Examples
--------------------
```python
# DC voltage measurement
voltage = dmm.measure_voltage()

# DC current measurement  
current = dmm.measure_current()

# 2-wire resistance
resistance = dmm.measure_resistance()

# 4-wire resistance (more accurate)
resistance_4w = dmm.measure_resistance_4wire()

# AC voltage
ac_voltage = dmm.measure_ac_voltage()

# AC current
ac_current = dmm.measure_ac_current()
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("measurements.txt")

# Connect via data_logger
dmm = logger.connect("keysight34460a")

# Add measurements to log
logger.add(dmm, "voltage", label="Input_Voltage")
logger.add(dmm, "current", label="Load_Current")

# Collect data
for i in range(100):
    logger.get_data()
    
logger.close_file()
```

Direct SCPI Commands
--------------------
```python
# Query instrument identification
idn = dmm.instrument.query("*IDN?")
print(f"Connected to: {idn}")

# Configure measurement manually
dmm.instrument.write("CONF:VOLT:DC 10,0.001")

# Read configured measurement
reading = float(dmm.instrument.query("READ?"))
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"voltage"** - DC voltage measurement in volts
- **"current"** - DC current measurement in amperes
- **"statistics"** - Returns [mean, std_dev, min, max] for multiple readings

Example:
```python
dmm = logger.connect("keysight34460a")
voltage = dmm.get("voltage")
current = dmm.get("current")
stats = dmm.get("statistics")  # Returns: [mean, std_dev, min, max]
```

Connection Details
------------------
The driver searches for VISA resources containing 'MY59' in the address string:
- USB: `USB0::0x2A8D::0x0101::MY5xxxxxxx::INSTR`
- LAN: `TCPIP0::192.168.1.100::inst0::INSTR`
- GPIB: `GPIB0::22::INSTR`

Error Handling
--------------
```python
try:
    dmm = Keysight34460A()
except ConnectionError as e:
    print(f"Failed to connect to 34460A: {e}")

try:
    voltage = dmm.measure_voltage()
except Exception as e:
    print(f"Measurement error: {e}")
```

Available Methods
-----------------
Measurement Methods:
- `measure_voltage()` - DC voltage measurement
- `measure_current()` - DC current measurement
- `measure_resistance()` - 2-wire resistance
- `measure_resistance_4wire()` - 4-wire resistance
- `measure_ac_voltage()` - AC voltage measurement
- `measure_ac_current()` - AC current measurement
- `get(item)` - Generic getter (voltage, current, resistance)

Connection Methods:
- `connect()` - Establish VISA connection
- `disconnect()` - Close connection and free resources

Technical Specifications
------------------------
- **Resolution**: 6.5 digits
- **DC Voltage**: 100 mV to 1000 V ranges
- **DC Current**: 100 μA to 10 A ranges
- **Resistance**: 100 Ω to 100 MΩ ranges
- **Accuracy**: Up to 0.0035% basic DC voltage accuracy
- **Interface**: VISA (USB, LAN, GPIB)

Comparison with DMM6500
------------------------
Both are 6.5-digit multimeters, but:
- **Keysight34460A**: Simpler API, standard measurements, MY59 detection
- **DMM6500**: Advanced features, digitizing mode, statistics, type hints

See Also
--------
- DMM6500: Alternative high-speed DMM with digitizing
- data_logger: Main orchestrator class
- Device driver standard: docs/DEVICE_DRIVER_STANDARD.md
"""

import pyvisa
from colorama import init, Fore, Style
try:
    from .loading import *
except:
    from loading import *


# Constants and global variables
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT  + "\r"
_DELAY = 0.1

"""
Establishes a connection to the Keysight 34460A Multimeter and provides methods for interfacing.

Example usage:
    multimeter = Keysight34460A()
    voltage = multimeter.measure_voltage()
    print(f"Measured voltage: {voltage} V")
"""
class Keysight34460A:

    """
    Initializes an instance of the Keysight34460A class.
    """
    def __init__(self, auto_connect=True):
        
        init(autoreset=True)

        self.rm = pyvisa.ResourceManager()
        self.address = None
        self.instrument = None
        self.loading = loading()

        self.status = "Not Connected"
        
        if auto_connect:
            self.connect()
        
    """
    Establishes a connection to the Keysight 34460A Multimeter.

    Raises:
        ConnectionError: If unable to connect to Keysight 34460A Multimeter.
    
    Example usage:
        multimeter.connect()
    """
    def connect(self):
        
        resources = self.rm.list_resources()
        for resource in resources:
            if 'MY59' in resource:
                self.address = resource
                break
        
        if self.address is None:
            error_message = "Keysight 34460A Multimeter not found."
            raise ConnectionError(_ERROR_STYLE + error_message)
        
        try:
            self.instrument = self.rm.open_resource(self.address)
            self.instrument.read_termination = '\n'
            self.status = "Connected"
            success_message = f"Connected to Keysight 34460A Multimeter at {self.address}"
            print(_SUCCESS_STYLE + success_message)

        except:
            error_message = f"Failed to connect to Keysight 34460A Multimeter at {self.address}: {e}"
            raise ConnectionError(_ERROR_STYLE + error_message)

    """
    Disconnects from the Keysight 34460A Multimeter.
    
    Example usage:
        multimeter.disconnect()
    """
    def disconnect(self):
        
        if self.instrument is not None:
            self.instrument.close()
            print(f"\rDisconnected from Keysight 34460A Multimeter at {self.address}")
            self.status = "Not Connected"

    """
    Retrieves the specified value.
    
    Args:
        item (str): The measurement item to retrieve. Valid values are "STAT", "CURR", or "VOLT".
    
    Returns:
        The measurement result corresponding to the specified item and channel.

    Raises:
        ValueError: If an invalid item is requested.
    
    Example usage:
        voltage = multimeter.get("VOLT")
        print(f"Voltage: {voltage} V")
    """
    def get(self, item):
    
        items = {
            "statistics": self.calculate_statistics,
            "current": self.measure_current,
            "voltage": self.measure_voltage
        }

        if item in items:
            result = items[item]()
            return result
        else:
            error_message = f"Invalid item: {item} request to Keysight 34460A Multimeter"
            raise ValueError(_ERROR_STYLE + error_message)
        
    """
    Reads and returns the voltage measurement.
    
    Returns:
        float: The measured voltage value.

    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
    
    Example usage:
        voltage = multimeter.measure_voltage()
        print(f"Voltage: {voltage} V")
    """
    def measure_voltage(self):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)


        self.instrument.write("MEASURE:VOLTAGE:DC?")
        self.loading.delay_with_loading_indicator(_DELAY)
        voltage = self.instrument.read()
        return float(voltage)


    """
    Reads and returns the current measurement.
    
    Returns:
        float: The measured current value.

    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
    
    Example usage:
        current = multimeter.measure_current()
        print(f"Current: {current} A")
    """
    def measure_current(self):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)

        self.instrument.write("MEASURE:CURRENT:DC?")
        self.loading.delay_with_loading_indicator(_DELAY)
        current = self.instrument.read()
        return float(current)
        
    """
    Retrieves the currently set function on the multimeter.

    Returns:
        str: The current function set on the multimeter.

    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
    """
    def get_current_function(self):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)

        self.instrument.write("FUNCtion?")
        self.loading.delay_with_loading_indicator(_DELAY)
        response = self.instrument.read().strip()
        return response.replace('"', '')  # Remove the quotation marks from the response

        
    """
    Disables the autorange feature for the specified function, if specified (current function by default).
    
    Args:
        function (str, optional): The function to disable autorange for. Defaults to the current function.

    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
    
    Example usage:
        multimeter.disable_autorange()
    """
    def disable_autorange(self, function = None):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)
        
        if function is None:
            function = self.get_current_function()

        self.instrument.write(f"{function}:RANGE:AUTO OFF")
        self.loading.delay_with_loading_indicator(_DELAY)
        print(f"\rAutorange disabled for {function} function")


    """
    Configures the measurement settings.
    
    Args:
        measurement_type (str): The type of measurement to configure, e.g., "VOLTAGE:DC", "CURRENT:DC".
            +--------------------+-----------------+
            |    Function        |     Command     |
            +--------------------+-----------------+
            |  DC Voltage        |   VOLTAGE:DC    |
            |  AC Voltage        |   VOLTAGE:AC    |
            |  DC Current        |   CURRENT:DC    |
            |  AC Current        |   CURRENT:AC    |
            |  2-Wire Resistance |   RESISTANCE    |
            |  Frequency         |   FREQUENCY     |
            |  Period            |   PERIOD        |
            |  Capacitance       |   CAPACITANCE   |
            |  Diode Test        |   DIODE         |
            |  Temperature       |   TEMPERATURE   |
            +--------------------+-----------------+
        range_val (float): The desired range value for the measurement type, specified in the measurement's units (V, A, Hz, Ohms, etc).
        resolution_val (float): The desired resolution value for the measurement type, specified in the measurement's units (V, A, Hz, Ohms, etc).
    
    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.

    Note:
        The range and resolution values are dependent on the specific capabilities of the Keysight 34460A Multimeter.
    
    Example usage:
        # Configure DC voltage measurement with a range of 10V and a resolution of 0.001V. 
        multimeter.configure("VOLTAGE:DC", 10.0, 0.001) 
    
        # Configure DC current measurement with a range of 1A and a resolution of 0.0001A.
        multimeter.configure("CURRENT:DC", 1.0, 0.0001)
    """
    def configure(self, measurement_type, range_val, resolution_val):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)

        command = f"CONFIGURE:{measurement_type} {range_val},{resolution_val}"
        self.instrument.write(command)
        self.loading.delay_with_loading_indicator(_DELAY)
        print(f"\rConfiguration set for {measurement_type}: Range={range_val}, Resolution={resolution_val} on Keysight 34460A Multimeter.")


    """
    Starts a measurement of n readings by enabling statistics, setting the number of readings, and initiating the measurement.
    
    Args:
        n (int): The number of readings to be performed.

    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
    
    Example usage:
        multimeter.start_measurement(100)
    """
    def start_measurement(self, n):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)


        # Enable statistics
        self.instrument.write("CALCulate:AVERage:STAT ON")
        self.loading.delay_with_loading_indicator(_DELAY)
        # Set the number of readings
        self.instrument.write(f"SAMPle:COUNt {n}")
        self.loading.delay_with_loading_indicator(_DELAY)
        # Initiate the measurement
        self.instrument.write("INIT")
        self.loading.delay_with_loading_indicator(_DELAY)
        print(f"\rMeasurement of {n} readings started on Keysight 34460A Multimeter.")


    """
    Performs the CALCulate:AVERage:ALL command and returns the result as a list average, standard deviation, minimum, and maximum values.
    
    Returns:
        list: A list containing the average, standard deviation, minimum, and maximum values of the measurement.
    
    Raises:
        ConnectionError: If not connected to Keysight 34460A Multimeter.
        
    Example usage:
        result = multimeter.calculate_average_all()
        print(f"Average: {result.Average}, Std Deviation: {result.StdDev}, Min: {result.Min}, Max: {result.Max}")
    """
    def calculate_statistics(self):

        if not self.status == "Connected":
            error_message = "Not connected to Keysight 34460A Multimeter."
            raise ConnectionError(_ERROR_STYLE + error_message)

        self.instrument.write("CALCulate:AVERage:ALL?")
        self.loading.delay_with_loading_indicator(_DELAY)
        response = self.instrument.read()
        self.loading.delay_with_loading_indicator(_DELAY)
        values = response.split(',')

        result = [float(values[0]), float(values[1]), float(values[2]), float(values[3])]

        return result

        


