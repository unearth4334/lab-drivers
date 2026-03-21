# Measurement Device Examples

## FLUKE45: Averaged DC Measurement

```python
from lab_drivers.drivers.serial import FLUKE45

dmm = FLUKE45()
print(f"Avg voltage: {dmm.measure_avg(10):.4f}V")
dmm.disconnect()
```

## DL3021: Load Sweep

```python
from lab_drivers.drivers.visa import DL3021

load = DL3021()
load.set_mode("CC")
load.set_output_state(True)

for current in [0.5, 1.0, 2.0, 3.0]:
    load.set_current(current)
    print(f"{current:.1f}A -> {load.measure_voltage():.2f}V")

load.set_output_state(False)
load.disconnect()
```
