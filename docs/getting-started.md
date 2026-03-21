# Getting Started

Learn the basic patterns for using Lab Drivers with any instrument.

## Connection Patterns

### Automatic Connection (Recommended)

Most drivers can automatically detect and connect to instruments with a single line:

```python
from lab_drivers.drivers.serial import RigolDP711

psu = RigolDP711()  # Auto-detects and connects
print(f"Connected to: {psu.identity}")
```

The library will scan available ports/VISA resources and connect to the first matching instrument.

### Explicit Connection

If you have multiple instruments or want to specify a specific address:

```python
# Serial device with explicit COM port
from lab_drivers.drivers.serial import RigolDP711
psu = RigolDP711(com_port="/dev/ttyUSB0")

# VISA device with explicit VISA address
from lab_drivers.drivers.visa import DL3021
load = DL3021(address="GPIB0::10::INSTR")

# VISA device with IP address
from lab_drivers.drivers.visa import RSA3030
spectrum = RSA3030(ip_address="192.168.1.100")
```

### Connection State Management

```python
# Check if connected
if not psu.ser or not psu.ser.is_open:
    psu.connect()

# Explicitly disconnect
psu.disconnect()

# Reconnect
psu.connect()
```

## Standard Interface

All Lab Drivers follow a consistent interface pattern:

### Connection Methods
```python
device.connect(address=None, **kwargs)  # Connect to device
device.disconnect()                      # Disconnect
```

### Measurement Methods
```python
# Direct measurement methods (available on most devices)
voltage = device.measure_voltage()
current = device.measure_current()
resistance = device.measure_resistance()

# Generic measurement interface
value = device.get("voltage")
value = device.get("current")
```

### Configuration Methods
```python
device.set_voltage(12.5)        # Set voltage
device.set_current(2.0)         # Set current limit
device.set_output_state(True)   # Enable/disable output
```

## Working with Measurements

### Single Measurements
```python
from lab_drivers.drivers.serial import KA3010P

psu = KA3010P()
psu.set_voltage(12.0)
psu.set_output_state(True)

# Single measurement
v = psu.measure_voltage()
i = psu.measure_current()
print(f"V: {v:.3f}V, I: {i:.3f}A")

psu.disconnect()
```

### Repeated Measurements
```python
import time

psu = KA3010P()
psu.set_voltage(12.0)
psu.set_output_state(True)

measurements = []
for _ in range(10):
    v = psu.measure_voltage()
    i = psu.measure_current()
    measurements.append((v, i))
    time.sleep(0.5)  # Wait 0.5 seconds between measurements

psu.disconnect()

# Analyze
import numpy as np
voltages = [m[0] for m in measurements]
currents = [m[1] for m in measurements]
print(f"Avg V: {np.mean(voltages):.3f}V")
print(f"Avg I: {np.mean(currents):.3f}A")
```

### Statistics (High-Precision Instruments)

Some instruments support statistical readback:

```python
from lab_drivers.drivers.visa import DL3021

load = DL3021()
load.set_mode("CC")
load.set_current(1.0)
load.set_output_state(True)

# Get statistics for current measurement
stats = load.get("statistics")
mean, std_dev, min_val, max_val = stats
print(f"Current: {mean:.6f}A ± {std_dev:.6f}A")
print(f"Range: {min_val:.6f}A - {max_val:.6f}A")

load.disconnect()
```

## Multi-Channel Devices

Devices with multiple channels use the `channel` parameter:

```python
from lab_drivers.drivers.visa import KS33500B

waveform = KS33500B()

# Configure channel 1
waveform.set_function("SIN", channel=1)
waveform.set_frequency(1000.0, channel=1)
waveform.set_amplitude(2.0, channel=1)
waveform.set_output_state(True, channel=1)

# Configure channel 2
waveform.set_function("SQU", channel=2)
waveform.set_frequency(500.0, channel=2)
waveform.set_amplitude(1.0, channel=2)
waveform.set_output_state(True, channel=2)

waveform.disconnect()
```

## Error Handling

### Connection Errors

```python
from lab_drivers.drivers.serial import FLUKE45

try:
    dmm = FLUKE45()
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print("Check that device is connected and powered on")
```

### Communication Errors

```python
from lab_drivers.drivers.visa import StanfordPS310

hvps = StanfordPS310()
try:
    hvps.set_voltage(-500.0)
    actual = hvps.measure_voltage()
except Exception as e:
    print(f"Communication error: {e}")
finally:
    hvps.disconnect()
```

### Safe Disconnection

```python
from lab_drivers.drivers.serial import RigolDP711

psu = RigolDP711()
try:
    psu.set_voltage(12.0)
    psu.turn_on()
    # ... do measurements ...
finally:
    psu.turn_off()
    psu.disconnect()  # Always clean up
```

## Context Managers (Best Practice)

Some drivers support context managers for automatic cleanup:

```python
from lab_drivers.drivers.serial import RigolDP711

with RigolDP711() as psu:
    psu.set_voltage(12.0)
    psu.turn_on()
    voltage = psu.measure_voltage()
    print(f"Voltage: {voltage:.2f}V")
    psu.turn_off()
# psu automatically disconnected here
```

## Logging and Debugging

### Enable Debug Output

Some instruments support debug logging via environment variables:

```bash
# StanfordPS310 debug logging levels
export PS310_DEBUG_LEVEL=2  # 0=silent, 1=errors, 2=all
python my_script.py
```

### Print Device Information

```python
from lab_drivers.drivers.serial import RigolDP711

psu = RigolDP711()
print(f"Model: {psu.identity}")
print(f"Address: {psu.address}")
print(f"Status: {psu.status}")
print(f"Connected: {psu.ser is not None and psu.ser.is_open}")
psu.disconnect()
```

## Type Hints

Lab Drivers uses type hints for IDE autocompletion:

```python
from lab_drivers.drivers.visa import DL3021

load: DL3021 = DL3021()

# IDE shows available methods and parameter types
load.set_mode("CC")      # Autocomplete on method names
load.set_current(1.0)    # Type checking on arguments

load.disconnect()
```

## Next Steps

- **[API Reference](api/index.md)** - Explore device-specific APIs and supported commands
- **[Examples](examples/quickstart.md)** - See practical code examples for different tasks
- **[Device Guides](examples/power-supplies.md)** - Task-specific guides for different device types
