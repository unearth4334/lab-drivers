
"""
Agilent U1233A Handheld Digital Multimeter Driver
==================================================

This module provides a driver for the Agilent U1233A handheld digital multimeter
with USB/serial connectivity.

Features
--------
- **Serial Communication**: RS-232 interface via USB
- **Auto-Detection**: Scans available COM ports
- **Standard Measurements**: DC/AC voltage, DC/AC current, resistance, continuity
- **Portable**: Battery-powered handheld DMM
- **Data Logging**: Integration with data_logger framework

Basic Usage
-----------
```python
from libs.U1233A import U1233A

# Auto-connect (will prompt for COM port if needed)
dmm = U1233A()

# Measure voltage
voltage = dmm.measure_voltage()
print(f"Voltage: {voltage:.3f} V")

# Measure current
current = dmm.measure_current()
print(f"Current: {current:.6f} A")

# Clean up
dmm.disconnect()
```

Manual COM Port Selection
-------------------------
```python
# Specify COM port explicitly
dmm = U1233A(auto_connect=False, com_port="COM3")

# Or set baud rate
dmm = U1233A(baud_rate=9600, com_port="COM5")
```

Integration with data_logger
-----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("handheld_dmm_data.txt")

dmm = logger.connect("u1233a")

logger.add(dmm, "voltage", label="Portable_DMM_V")
logger.add(dmm, "current", label="Portable_DMM_I")

for i in range(100):
    logger.get_data()
    
logger.close_file()
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"MEAS"** - Single measurement reading (voltage, current, or resistance depending on mode)
- **"MEAS_AVG"** - Average of multiple measurements (returns mean and stdev)

Example:
```python
dmm = logger.connect("u1233a")
value, error = dmm.get("MEAS")           # Single reading
mean, stdev = dmm.get("MEAS_AVG")        # Averaged reading
```

Available Methods
-----------------
- `measure_voltage()` - Measure voltage
- `measure_current()` - Measure current
- `measure_resistance()` - Measure resistance
- `get(item)` - Generic getter (MEAS, MEAS_AVG)
- `connect(baud_rate, com_port)` - Establish serial connection
- `disconnect()` - Close serial connection

See Also
--------
- DMM6500: Benchtop high-precision multimeter
- Keysight34460A: Benchtop 6.5-digit multimeter
- data_logger: Main orchestrator class
"""

import serial
import statistics
import numpy
import serial.tools.list_ports
import os
try:
    from .loading import *
except:
    from loading import *

from colorama import init, Fore, Back, Style



# Constants and global variables
_MAX_FILENAMES = 100
_VALUE_PADDING = 40
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "
_DELAY = 0.05
_CONNECTION_TIMEOUT = 1

class U1233A:
    def __init__(self,auto_connect=True, baud_rate=9600,com_port=None):

        init(autoreset=True)
        self.status = "Not Connected"
        self.ser = None
        self.identity = None
        self.loading = loading()

        self.com_port = com_port

        if auto_connect:
            self.connect(baud_rate, com_port)
        
    def connect(self,baud_rate=9600,com_port=None, prompt_on_fail: bool = True):

        try:
            if com_port is None:
                com_port = os.environ['U1233A_COM_PORT_ENV_VAR']
            self.ser = serial.Serial(com_port,baud_rate,timeout=_CONNECTION_TIMEOUT)
            self.status = "Connected"
        except Exception:
            if not prompt_on_fail:
                error_message = f"Failed to connect to U1233A on COM port {com_port}."
                raise ConnectionError(_ERROR_STYLE + error_message)
            ports = serial.tools.list_ports.comports()
            if not ports:
                error_message = "No COM ports found."
                raise ConnectionError(_ERROR_STYLE + error_message)

            print("Available COM ports:")
            for i, port in enumerate(ports, start=1):
                print(f"{i}. {port.device} - {port.description}")

            while True:
                try:
                    selection = int(self.loading.input_with_flashing("Select a COM port (1, 2, ...): "))
                    
                    if 1 <= selection <= len(ports):
                        com_port = ports[selection - 1].device
                        os.environ['U1233A_COM_PORT_ENV_VAR']= str(com_port)
                        break
                    else:
                        print(_ERROR_STYLE + "Error! Invalid selection.")
                except ValueError:
                    error_message = "Invalid input. Please enter a number."
                    print(_ERROR_STYLE + error_message)

            try:
                self.ser = serial.Serial(com_port,baud_rate,timeout=_CONNECTION_TIMEOUT)
                self.status = "Connected"
            except:
                error_message = f"Failed to connect to U1233A on COM port {com_port}."
                raise ConnectionError(_ERROR_STYLE + error_message)
            
        self.ser.write(str('*IDN?\n').encode('ascii'))
        self.loading.delay_with_loading_indicator(_DELAY)
        self.identity = self.ser.readline().decode('ascii').strip()
        if len(self.identity) < 5:
            error_message = f"Failed to connect to U1233A on COM port {com_port}. Check that the device is connected and powered on."
            raise ConnectionError(_ERROR_STYLE + error_message)
        print(_SUCCESS_STYLE + f"Connected to {self.identity} on COM port {com_port}.")
        return self.ser

    def get(self,item,channel=1):

        items = { "MEAS"    :self.measure,
                  "MEAS_AVG":self.measure_avg}

        result = items[item]()

        return result


    def measure(self):

        command = 'READ?\n'

        self.ser.write(str(command).encode('ascii'))
        self.loading.delay_with_loading_indicator(_DELAY)
        val = self.ser.readline()
        return (float(val),0)

    def measure_avg(self,n=10):

        val = numpy.zeros(n)
        for x in range(n):
            self.loading.display_loading_bar(x/n,loading_text="Averaging measurements from U1233A Multimeter")
            self.loading.delay_with_loading_indicator(_DELAY)
            temp = self.measure()
            val[x]=temp[0]

        return (statistics.fmean(val),statistics.stdev(val))

    def disconnect(self):
        if self.ser.isOpen():
            self.ser.close()
            print("Disconnected from {self.identity} on COM port {self.com_port}.")

# Test code
if __name__ == "__main__":
    multimeter = U1233A()
    print(f"Measurement: {multimeter.get('MEAS')}")
    print(f"Average measurement: {multimeter.get('MEAS_AVG')}")
    multimeter.disconnect()
