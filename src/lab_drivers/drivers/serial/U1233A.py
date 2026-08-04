
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
from lab_drivers.core.log import get_logger
from lab_drivers.core.ports import resolve_address as _resolve_address, select_port
from lab_drivers.core.progress import loading

_log = get_logger(__name__)

# Constants and global variables
_MAX_FILENAMES = 100
_VALUE_PADDING = 40
_DELAY = 0.05
_CONNECTION_TIMEOUT = 1

class U1233A:
    """Agilent U1233A handheld multimeter driver.

    Provides serial connection and measurement helpers used by data-logging
    workflows.

    Supported get() items:
        - "MEAS": single reading tuple `(value, error)`
        - "MEAS_AVG": averaged tuple `(mean, stdev)`
    """

    def __init__(self, auto_connect=True, baud_rate=9600, address=None, *,
                 com_port=None, interactive=None):
        """Initialize the driver and optionally connect.

        Args:
            auto_connect: Connect during initialization when True.
            baud_rate: Serial baud rate.
            address: Optional explicit serial port.
            com_port: Deprecated alias for ``address``.
            interactive: Whether a missing port may be resolved by prompting.
                ``None`` prompts only when stdin is a terminal.
        """
        address = _resolve_address(address, com_port)

        self.status = "Not Connected"
        self.ser = None
        self.identity = None
        self.loading = loading(interactive)

        self.com_port = address
        self._interactive = interactive

        if auto_connect:
            self.connect(baud_rate, address)

    def connect(self, baud_rate=9600, address=None, prompt_on_fail: bool = True, *,
                com_port=None, interactive=None):
        """Connect to the instrument over serial.

        Args:
            baud_rate: Serial baud rate.
            address: Optional explicit serial port. When omitted,
                ``U1233A_COM_PORT_ENV_VAR`` is consulted.
            prompt_on_fail: Offer manual port selection when the first attempt
                fails. Only takes effect where prompting is possible at all.
            com_port: Deprecated alias for ``address``.
            interactive: Override the prompting decision for this call.

        Returns:
            Active serial handle.

        Raises:
            ConnectionError: Connection failed, or a port was needed but this
                process cannot prompt for one.
        """
        address = _resolve_address(address, com_port) or self.com_port
        allow_prompt = self._interactive if interactive is None else interactive

        port = None
        try:
            # First attempt: whatever was supplied, without ever prompting.
            port = select_port("U1233A", port=address,
                               env_var="U1233A_COM_PORT_ENV_VAR", interactive=False)
            self.ser = serial.Serial(port, baud_rate, timeout=_CONNECTION_TIMEOUT)
            self.status = "Connected"
        except Exception:
            if not prompt_on_fail:
                raise ConnectionError(
                    f"Failed to connect to U1233A on COM port {port or address}.")
            # select_port raises rather than blocking when nobody can answer.
            port = select_port("U1233A", env_var="U1233A_COM_PORT_ENV_VAR",
                               interactive=allow_prompt)
            try:
                self.ser = serial.Serial(port, baud_rate, timeout=_CONNECTION_TIMEOUT)
                self.status = "Connected"
            except Exception as ex:
                raise ConnectionError(
                    f"Failed to connect to U1233A on COM port {port}.") from ex

        com_port = port
        self.ser.write(str('*IDN?\n').encode('ascii'))
        self.loading.delay_with_loading_indicator(_DELAY)
        self.identity = self.ser.readline().decode('ascii').strip()
        if len(self.identity) < 5:
            error_message = f"Failed to connect to U1233A on COM port {com_port}. Check that the device is connected and powered on."
            raise ConnectionError(error_message)
        _log.info(f"Connected to {self.identity} on COM port {com_port}.")
        return self.ser

    def get(self,item,channel=1):
        """Return a measurement by command token.

        Args:
            item: "MEAS" or "MEAS_AVG".
            channel: Unused placeholder kept for compatibility.
        """

        items = { "MEAS"    :self.measure,
                  "MEAS_AVG":self.measure_avg}

        result = items[item]()

        return result


    def measure(self):
        """Read one measurement from the active meter mode."""

        command = 'READ?\n'

        self.ser.write(str(command).encode('ascii'))
        self.loading.delay_with_loading_indicator(_DELAY)
        val = self.ser.readline()
        return (float(val),0)

    def measure_avg(self,n=10):
        """Return mean and standard deviation of repeated measurements."""

        val = numpy.zeros(n)
        for x in range(n):
            self.loading.display_loading_bar(x/n,loading_text="Averaging measurements from U1233A Multimeter")
            self.loading.delay_with_loading_indicator(_DELAY)
            temp = self.measure()
            val[x]=temp[0]

        return (statistics.fmean(val),statistics.stdev(val))

    def disconnect(self):
        """Close the serial connection."""
        if self.ser.isOpen():
            self.ser.close()
            _log.info("Disconnected from {self.identity} on COM port {self.com_port}.")

# Test code
if __name__ == "__main__":
    multimeter = U1233A()
    _log.info(f"Measurement: {multimeter.get('MEAS')}")
    _log.info(f"Average measurement: {multimeter.get('MEAS_AVG')}")
    multimeter.disconnect()
