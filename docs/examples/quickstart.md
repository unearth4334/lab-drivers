# Quick Start Examples

Common patterns for starting with Lab Drivers.

## Basic Power Supply Control

```python
from lab_drivers.drivers.serial import RigolDP711

psu = RigolDP711()
psu.set_voltage(12.0)
psu.set_current(2.0)
psu.turn_on()

print(f"V={psu.measure_voltage():.2f}V I={psu.measure_current():.3f}A")

psu.turn_off()
psu.disconnect()
```

## Basic Electronic Load Control

```python
from lab_drivers.drivers.visa import DL3021

load = DL3021()
load.set_mode("CC")
load.set_current(1.5)
load.set_output_state(True)

print(f"Power={load.measure_power():.2f}W")

load.set_output_state(False)
load.disconnect()
```

## Basic Measurement Loop

```python
import time
from lab_drivers.drivers.serial import FLUKE45

dmm = FLUKE45()
for _ in range(5):
    print(f"Voltage={dmm.measure_voltage():.4f}V")
    time.sleep(0.5)
dmm.disconnect()
```
