#   @file RigolDS7034.py
#   @brief Establishes a connection to the Rigol DP832 Power Supply 
#       and provides methods for interacting with the device.
#   @date 22-May-2023
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
Rigol DP832 Triple-Output Power Supply Driver
==============================================

This module provides a driver for the Rigol DP832 programmable DC power supply,
a triple-output bench power supply with independent channel control.

Features
--------
- **Triple Output Channels**: Three independent power supplies in one unit
  - CH1: 30V / 3A
  - CH2: 30V / 3A  
  - CH3: 5V / 3A
- **Auto-Detection**: Automatically finds DP832 using 'DP8' identifier
- **Independent Control**: Set voltage and current for each channel separately
- **Output Enable/Disable**: Individual channel on/off control
- **Measurement Readback**: Read actual voltage and current per channel
- **Over-Current Protection**: Set current limits per channel

Basic Usage
-----------
```python
from libs.RigolDP832 import RigolDP832

# Auto-connect to DP832
psu = RigolDP832()

# Configure channel 1
psu.set_voltage(12.0, channel=1)
psu.set_current(0.5, channel=1)
psu.set_output_state(True, channel=1)

# Read measurements
voltage = psu.measure_voltage(channel=1)
current = psu.measure_current(channel=1)
print(f"CH1: {voltage:.3f}V, {current:.3f}A")

# Disable output
psu.set_output_state(False, channel=1)
psu.disconnect()
```

Multi-Channel Control
---------------------
```python
# Configure all three channels
psu.set_voltage(15.0, channel=1)
psu.set_voltage(5.0, channel=2)
psu.set_voltage(3.3, channel=3)

# Set current limits
psu.set_current(1.0, channel=1)
psu.set_current(2.0, channel=2)
psu.set_current(1.5, channel=3)

# Enable all channels
for ch in [1, 2, 3]:
    psu.set_output_state(True, channel=ch)

# Read all channels
for ch in [1, 2, 3]:
    v = psu.measure_voltage(channel=ch)
    i = psu.measure_current(channel=ch)
    print(f"CH{ch}: {v:.3f}V {i:.3f}A")
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("power_supply_data.txt")

psu = logger.connect("rigoldp832")

# Configure outputs
psu.set_voltage(12.0, channel=1)
psu.set_output_state(True, channel=1)

# Log voltage and current for multiple channels
logger.add(psu, "voltage", channel=1, label="PSU_CH1_V")
logger.add(psu, "current", channel=1, label="PSU_CH1_I")
logger.add(psu, "voltage", channel=2, label="PSU_CH2_V")
logger.add(psu, "current", channel=2, label="PSU_CH2_I")

# Collect data
for i in range(100):
    logger.get_data()
    
logger.close_file()
```

Channel Specifications
----------------------
```python
# Channel 1 and 2: 30V/3A
psu.set_voltage(30.0, channel=1)  # Max voltage
psu.set_current(3.0, channel=1)   # Max current

# Channel 3: 5V/3A (fixed voltage range)
psu.set_voltage(5.0, channel=3)   # Max voltage
psu.set_current(3.0, channel=3)   # Max current
```

Output State Control
--------------------
```python
# Enable single channel
psu.set_output_state(True, channel=1)

# Check if channel is enabled
state = psu.get_output_state(channel=1)
print(f"CH1 enabled: {state}")

# Disable all channels
for ch in [1, 2, 3]:
    psu.set_output_state(False, channel=ch)
```

Error Handling
--------------
```python
try:
    psu = RigolDP832()
except ConnectionError as e:
    print(f"Failed to connect: {e}")

try:
    psu.set_voltage(35.0, channel=1)  # Exceeds max
except ValueError as e:
    print(f"Invalid voltage: {e}")
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item, channel)` method:

- **"voltage"** - Measure actual output voltage in volts
- **"current"** - Measure actual output current in amperes
- **"power"** - Calculate power (voltage × current) in watts
- **"average_voltage"** - Average voltage over multiple measurements
- **"average_current"** - Average current over multiple measurements
- **"average_power"** - Average power over multiple measurements

Example:
```python
psu = logger.connect("rigoldp832")
voltage = psu.get("voltage", channel=1)
current = psu.get("current", channel=1)
power = psu.get("power", channel=1)
avg_v = psu.get("average_voltage", channel=2)
```

Available Methods
-----------------
Voltage Control:
- `set_voltage(voltage, channel)` - Set output voltage (V)
- `measure_voltage(channel)` - Read actual output voltage

Current Control:
- `set_current(current, channel)` - Set current limit (A)
- `measure_current(channel)` - Read actual output current

Output Control:
- `set_output_state(state, channel)` - Enable/disable output
- `get_output_state(channel)` - Check if output is enabled

Connection:
- `connect()` - Establish VISA connection
- `disconnect()` - Close connection

Generic Interface:
- `get(item, channel)` - Generic getter (voltage, current, power, average_*)

Technical Specifications
------------------------
- **Output Channels**: 3 independent outputs
- **CH1/CH2 Voltage**: 0-30V
- **CH1/CH2 Current**: 0-3A
- **CH3 Voltage**: 0-5V
- **CH3 Current**: 0-3A
- **Voltage Accuracy**: ±(0.03% + 10mV)
- **Current Accuracy**: ±(0.05% + 10mA)
- **Interface**: USB, LAN via PyVISA

See Also
--------
- DP832: Alternative DP832 driver (if exists)
- StanfordPS310: High voltage power supply
- data_logger: Main orchestrator class
"""

import pyvisa
import statistics
import numpy
from colorama import init, Fore, Back, Style
try:
    from .loading import *
except:
    from loading import *


# Constants and global variables
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT  + "\r"
_DELAY = 0.1 #seconds

"""
Establishes a connection to the Rigol DP832 Power Supply

Example usage:
"""
class RigolDP832:

    """
    Initializes an instance of the RigolDP832 class.
    """
    def __init__(self,auto_connect=True):

        init(autoreset=True)    

        self.rm = pyvisa.ResourceManager()
        self.address = None
        self.instrument = None
        self.loading = loading()
        self.voltage_has_been_configured = [False,False,False]
        self.current_has_been_configured = [False,False,False]

        self.status = "Not Connected"

        if auto_connect:
            self.connect()

    """
    Establishes a connection to the Rigol DP832 Power Supply.

    Raises:
        ConnectionError: If unable to connect to Rigol DP832 Power Supply.

    Example usage:
        power_supply.connect()
    """
    def connect(self):

        resources = self.rm.list_resources()
        for resource in resources:
            if 'DP8' in resource:
                self.address = resource
                break

        if self.address is None:
            error_message = "Rigol DP832 Power Supply not found."
            raise ConnectionError(_ERROR_STYLE + error_message)
            return None

        try:
            self.instrument = self.rm.open_resource(self.address)
            self.instrument.read_termination = '\n'
            self.status = "Connected"
            success_message = f"Connected to Rigol DP832 Power Supply at {self.address}"
            print(_SUCCESS_STYLE + success_message)

        except Exception as e:
            error_message = f"Failed to connect to Rigol DP832 Power Supply at {self.address}: {e}"
            raise ConnectionError(_ERROR_STYLE + error_message)
        
    """
    Disconnects from the Rigol DP832 Power Supply.

    Example usage:
        power_supply.disconnect()
    """
    def disconnect(self):
        if self.instrument is not None:
            self.instrument.close()
            print(f"\rDisconnected from Rigol DP832 Power Supply at {self.address}")
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
    def get(self, item, channel=1):

        item = item.lower()

        items = {
            "current": self.measure_current,
            "voltage": self.measure_voltage,
            "power": self.measure_power,
            "average_current": self.get_average,
            "average_voltage": self.get_average,
            "average_power": self.get_average
        }

        if item in items:
            # if item starts with average_, get the statistics
            if item.startswith("average_"):
                # get the statistics for the specified item
                # take "average_" off the front of the item name
                result = items[item](item[8:],channel)
                return result
            else:
                result = items[item](channel)
                return result
        else:
            error_message = f"Invalid item: {item} request to Keysight 34460A Multimeter"
            raise ValueError(_ERROR_STYLE + error_message)
        
    """
    Selects the active output channel of the Rigol DP832 Power Supply.

    Parameters:
        channel (int): The channel number to select (1, 2, or 3).

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        power_supply.select_channel(2)
    """
    def select_channel(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":INSTrument:NSELect {channel}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to select channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        

    """
    Gets the currently selected channel on the Rigol DP832 Power Supply.

    Returns:
        int: The channel number (1, 2, or 3) currently selected.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is received from the instrument.
    """
    def get_selected_channel(self):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        try:
            response = self.instrument.query(":INSTrument:NSELect?")
            self.loading.delay_with_loading_indicator(_DELAY)
            channel = int(response)
            if channel < 1 or channel > 3:
                raise ValueError(_ERROR_STYLE + "Invalid channel number received from the instrument.")
            return channel
        except Exception as e:
            error_message = f"Failed to get selected channel on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

        
    """
    Turns the output of the specified channel on or off.

    Parameters:
        channel (int): The channel number to control (1, 2, or 3).
        state (bool or str): The state to set for the channel.
            - True or "ON" to turn on the output.
            - False or "OFF" to turn off the output.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number or state is provided.

    Example usage:
        # Turn on channel 2
        power_supply.set_output_state(2, True)

        # Turn off channel 1
        power_supply.set_output_state(1, False)
    """
    def set_output_state(self, channel, state):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if state in [1,"ON",True]:
            if self.voltage_has_been_configured[channel-1] == False:
                warning_message = f"Output voltage has not been set for channel {channel}. The currently configured value is {self.get_output_voltage(channel)} V. Do you want to continue? (y/n): "
                print(_WARNING_STYLE + warning_message)
                if not self.loading.input_with_flashing('') == "y":
                    raise ValueError(_ERROR_STYLE + "User cancelled operation.")
            if self.current_has_been_configured[channel-1] == False:
                warning_message = f"Output current has not been set for channel {channel}. The currently configured value is {self.get_output_current(channel)} A. Do you want to continue? (y/n): "
                print(_WARNING_STYLE + warning_message)
                if not self.loading.input_with_flashing('') == "y":
                    raise ValueError(_ERROR_STYLE + "User cancelled operation.")
            print(f"\rRigol DP832 Power Supply Channel {channel}:\t{Back.GREEN} ON  {Back.BLUE} {Fore.WHITE} {self.get_output_voltage(channel)} V | {self.get_output_current(channel)} A   ")
            command = f":OUTP CH{channel},1"
        elif state in [0,"OFF",False]:
            # Rewritten more compactly
            print(f"\rRigol DP832 Power Supply Channel {channel}:\t{Back.RED} OFF ")
            command = f":OUTP CH{channel},0"
        else:
            raise ValueError(_ERROR_STYLE + "Invalid state type. Please provide either bool or str.")

        try:
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to set output state of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        
        

    """
    Sets the output voltage of the specified channel.

    Parameters:
        channel (int): The channel number to control (1, 2, or 3).
        voltage (float): The voltage value to set.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number or voltage value is provided.

    Example usage:
        # Set voltage of channel 1 to 5.0V
        power_supply.set_output_voltage(1, 5.0)

        # Set voltage of channel 2 to 3.3V
        power_supply.set_output_voltage(2, 3.3)
    """
    def set_output_voltage(self, channel, voltage):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if not isinstance(voltage, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid voltage value. Please provide a numeric value.")

        if channel in [1, 2] and (voltage < 0 or voltage > 30):
            raise ValueError(_ERROR_STYLE + f"Invalid voltage value \"{voltage}\". Channel 1 and 2 accept voltages between 0 and 30 V.")

        if channel == 3 and (voltage < 0 or voltage > 5):
            raise ValueError(_ERROR_STYLE + "Invalid voltage value \"{voltage}\". Channel 3 accepts voltages between 0 and 5 V.")

        try:
            currently_selected_channel = self.get_selected_channel()
            if not currently_selected_channel == channel:
                self.select_channel(channel)
            command = f":VOLT {voltage:.3f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            if not currently_selected_channel == channel:
                self.select_channel(currently_selected_channel) # Return to the previously selected channel
            self.voltage_has_been_configured[channel-1] = True
        except Exception as e:
            error_message = f"Failed to set output voltage of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        

    """
    Sets the output current of the specified channel.

    Parameters:
        channel (int): The channel number to control (1, 2, or 3).
        current (float): The current value to set.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number or current value is provided.

    Example usage:
        # Set current of channel 1 to 2.0A
        power_supply.set_output_current(1, 2.0)

        # Set current of channel 2 to 1.5A
        power_supply.set_output_current(2, 1.5)
    """
    def set_output_current(self, channel, current):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if not isinstance(current, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid current value. Please provide a numeric value.")

        if current < 0 or current > 3:
            raise ValueError(_ERROR_STYLE + "Invalid current value. The current must be between 0 and 3 A.")

        try:
            currently_selected_channel = self.get_selected_channel()
            if not currently_selected_channel == channel:
                self.select_channel(channel)
            command = f":CURR {current:.3f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            if not currently_selected_channel == channel:
                self.select_channel(currently_selected_channel) # Return to the previously selected channel
            self.current_has_been_configured[channel-1] = True
        except Exception as e:
            error_message = f"Failed to set output current of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

    
    """
    Get the currently configured voltage of the Rigol DP832 Power Supply.

    Parameters:
        channel (int): The channel number to retrieve the voltage from (1, 2, or 3).

    Returns:
        float: The currently configured voltage of the specified channel.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Get voltage of channel 1
        voltage = power_supply.get_output_voltage(1)

        # Get voltage of channel 2
        voltage = power_supply.get_output_voltage(2)
    """
    def get_output_voltage(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":SOURce{channel}:VOLTage:LEVel:IMMediate:AMPLitude?"
            response = self.instrument.query(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            voltage = float(response)
            return voltage
        except Exception as e:
            error_message = f"Failed to get output voltage of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

    """
    Get the currently configured output current of the Rigol DP832 Power Supply.

    Parameters:
        channel (int): The channel number to retrieve the current from (1, 2, or 3).

    Returns:
        float: The currently configured output current of the specified channel.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Get current of channel 1
        current = power_supply.get_output_current(1)

        # Get current of channel 2
        current = power_supply.get_output_current(2)
    """
    def get_output_current(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":SOURce{channel}:CURRent:LEVel:IMMediate:AMPLitude?"
            response = self.instrument.query(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            current = float(response)
            return current
        except Exception as e:
            error_message = f"Failed to get output current of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)


    """
    Retrieves the voltage measurement result of the specified channel.

    Parameters:
        channel (int): The channel number to retrieve the voltage measurement from (1, 2, or 3).

    Returns:
        float: The voltage measurement result of the specified channel.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Get voltage measurement of channel 1
        voltage_measurement = power_supply.measure_voltage(1)

        # Get voltage measurement of channel 2
        voltage_measurement = power_supply.measure_voltage(2)
    """
    def measure_voltage(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":MEAS:VOLT? CH{channel}"
            response = self.instrument.query(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            voltage_measurement = float(response)
            return voltage_measurement
        except Exception as e:
            error_message = f"Failed to get voltage measurement of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
    
    """
    Retrieves the current measurement result of the specified channel.

    Parameters:
        channel (int): The channel number to retrieve the current measurement from (1, 2, or 3).

    Returns:
        float: The current measurement result of the specified channel.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Get current measurement of channel 1
        current_measurement = power_supply.measure_current(1)

        # Get current measurement of channel 2
        current_measurement = power_supply.measure_current(2)
    """
    def measure_current(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":MEAS:CURR? CH{channel}"
            response = self.instrument.query(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            current_measurement = float(response)
            return current_measurement
        except Exception as e:
            error_message = f"Failed to get current measurement of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
    
    """
    Retrieves the power measurement result of the specified channel.

    Parameters:
        channel (int): The channel number to retrieve the power measurement from (1, 2, or 3).

    Returns:
        float: The power measurement result of the specified channel.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Get power measurement of channel 1
        power_measurement = power_supply.get_power_measurement(1)

        # Get power measurement of channel 2
        power_measurement = power_supply.get_power_measurement(2)
    """
    def measure_power(self, channel):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        try:
            command = f":MEAS:POWE? CH{channel}"
            response = self.instrument.query(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            power_measurement = float(response)
            return power_measurement
        except Exception as e:
            error_message = f"Failed to get power measurement of channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        
    def get_average(self, item, channel = 1, samples = 10):
        # measure_function should be either measure_voltage, measure_current, or measure_power
        # samples should be an integer and greater than 0
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if type(samples) != int or samples <= 0:
            raise ValueError(_ERROR_STYLE + "Number of samples must be an integer greater than 0.")
        
        # channel must be either 1, 2, or 3
        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")
        
        items = {
            "current": self.measure_current,
            "voltage": self.measure_voltage,
            "power": self.measure_power,
        }

        if item in items:
            measure_function = items[item]
        else:
            raise ValueError(_ERROR_STYLE + "Invalid item. Please provide either 'voltage', 'current', or 'power'.")
        
        try:
            val = numpy.zeros(samples)
            for i in range(samples):
                val[i] = measure_function(channel)
                self.loading.display_loading_bar(i/samples,loading_text="Averaging measurements from DP832 Power Supply")
            average = statistics.fmean(val)
            stdev = statistics.stdev(val)
            return [average, stdev]
        except Exception as e:
            error_message = f"Failed to get average measurement: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
    
    """
    Set the overcurrent protection threshold of the specified channel.

    Parameters:
        channel (int): The channel number to set the overcurrent protection threshold for (1, 2, or 3).
        threshold (float): The overcurrent protection threshold to set, in amps.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided or the threshold value is out of range.

    Example usage:
        # Set overcurrent protection threshold for channel 1 to 2.5A
        power_supply.set_current_limit(1, 2.5)

        # Set overcurrent protection threshold for channel 2 to 3A
        power_supply.set_current_limit(2, 3.0)
    """
    def set_current_limit(self, channel, current):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if current < 0 or current > 3.0:
            raise ValueError(_ERROR_STYLE + "Invalid overcurrent protection threshold. Please provide a value between 0 and 3.0.")

        try:
            command = f":SOURce{channel}:CURRent:PROTection:LEVel {current:.3f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to set overcurrent protection threshold for channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

    """
    Set the overvoltage protection threshold of the specified channel.

    Parameters:
        channel (int): The channel number to set the overvoltage protection threshold for (1, 2, or 3).
        threshold (float): The overvoltage protection threshold to set, in volts.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided or the threshold value is out of range.

    Example usage:
        # Set overvoltage protection threshold for channel 1 to 25V
        power_supply.set_voltage_limit(1, 25.0)

        # Set overvoltage protection threshold for channel 2 to 28V
        power_supply.set_voltage_limit(2, 28.0)
    """
    def set_voltage_limit(self, channel, voltage):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if channel in [1, 2] and (voltage < 0 or voltage > 30.0):
            raise ValueError(_ERROR_STYLE + "Invalid overvoltage protection threshold. Please provide a value between 0 and 30.0 for channels 1 and 2.")

        if channel == 3 and (voltage < 0 or voltage > 5.0):
            raise ValueError(_ERROR_STYLE + "Invalid overvoltage protection threshold. Please provide a value between 0 and 5.0 for channel 3.")

        try:
            command = f":SOURce{channel}:VOLTage:PROTection:LEVel {voltage:.3f}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to set overvoltage protection threshold for channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

    """
    Turn the overcurrent protection of the specified channel on or off.

    Parameters:
        channel (int): The channel number to turn the overcurrent protection for (1, 2, or 3).
        enable (bool): True to enable overcurrent protection, False to disable.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Enable overcurrent protection for channel 1
        power_supply.set_overcurrent_protection_state(1, True)

        # Disable overcurrent protection for channel 2
        power_supply.set_overcurrent_protection_state(2, False)
    """
    def set_overcurrent_protection_state(self, channel, state):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if state in [1,"ON",True]:
            state = "ON"

        elif state in [0,"OFF",False]:
            state = "OFF"
        else:
            raise ValueError(_ERROR_STYLE + "Invalid state type. Please provide either bool or str.")


        try:
            command = f":OUTPut{channel}:PROTection:CURRent {state}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to turn overcurrent protection {state} for channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)

    """
    Turn the overvoltage protection of the specified channel on or off.

    Parameters:
        channel (int): The channel number to turn the overvoltage protection for (1, 2, or 3).
        enable (bool): True to enable overvoltage protection, False to disable.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number is provided.

    Example usage:
        # Enable overvoltage protection for channel 1
        power_supply.set_overvoltage_protection_state(1, True)

        # Disable overvoltage protection for channel 2
        power_supply.set_overvoltage_protection_state(2, False)
    """
    def set_overvoltage_protection_state(self, channel, state):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if state in [1,"ON",True]:
            state = "ON"

        elif state in [0,"OFF",False]:
            state = "OFF"
        else:
            raise ValueError(_ERROR_STYLE + "Invalid state type. Please provide either bool or str.")

        try:
            command = f":OUTPut{channel}:PROTection:VOLTage {state}"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
        except Exception as e:
            error_message = f"Failed to turn overvoltage protection {state} for channel {channel} on Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        

    """
    Increments the configured output voltage on a given channel by a given step size.

    Parameters:
        channel (int): The channel number to increment the voltage (1, 2, or 3).
        step_size (float): The step size by which to increment the voltage.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.
        ValueError: If an invalid channel number or step size is provided.

    Example usage:
        power_supply = RigolDP832()
        power_supply.connect()
        
        # Set the output voltage of channel 1 to 5.0V
        power_supply.set_output_voltage(1, 5.0)
        
        # Set the output current of channel 2 to 1.5A
        power_supply.set_output_current(2, 1.5)
        
        # Turn on channel 1
        power_supply.set_output_state(1, True)
        
        # Get the voltage of channel 2
        voltage = power_supply.get_output_voltage(2)
        print(f"Voltage of channel 2: {voltage} V")
        
        # Increment the voltage of channel 3 by 0.1V
        power_supply.increment_output_voltage(3, 0.1)
        
        # Disconnect from the power supply
        power_supply.disconnect()
    """
    def increment_output_voltage(self, channel, step_size):
        
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        if channel < 1 or channel > 3:
            raise ValueError(_ERROR_STYLE + "Invalid channel number. Please provide a number between 1 and 3.")

        if not isinstance(step_size, (int, float)):
            raise ValueError(_ERROR_STYLE + "Invalid step size. Please provide a numeric value.")

        current_voltage = self.get_output_voltage(channel)
        new_voltage = current_voltage + step_size
        self.set_output_voltage(channel, new_voltage)

    """
    Reset the Rigol DP832 Power Supply.

    Raises:
        ConnectionError: If not connected to the Rigol DP832 Power Supply.

    Example usage:
        power_supply.reset()
    """
    def reset(self):
        if not self.status == "Connected":
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP832 Power Supply.")

        try:
            command = "*RST"
            self.instrument.write(command)
            self.loading.delay_with_loading_indicator(_DELAY)
            self.voltage_has_been_configured = [False, False, False]
            self.current_has_been_configured = [False, False, False]
        except Exception as e:
            error_message = f"Failed to reset Rigol DP832 Power Supply: {e}"
            raise ValueError(_ERROR_STYLE + error_message)
        
    def error_handler(self, exception_type, exception, traceback):
        # Custom error handling logic
        print(_ERROR_STYLE + "An error occurred:", exception)

        # Attempt to turn off all output channels
        try:
            for channel in range(1, 4):
                self.set_output_state(channel, False)
        except Exception as e:
            print(_ERROR_STYLE + "Failed to turn off output channels:", e)

# Test code
if __name__ == "__main__":
    test_loading = loading()
    power_supply = RigolDP832()
    average_voltage = power_supply.get_average("voltage")
    print(f"Average current: {average_voltage} V")
    power_supply.disconnect()

