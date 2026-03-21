# Power Supply Examples

## RigolDP711: Set and Verify Output

```python
from lab_drivers.drivers.serial import RigolDP711

psu = RigolDP711()
psu.set_voltage(24.0)
psu.set_current(1.0)
psu.turn_on()

for _ in range(3):
    v = psu.measure_voltage()
    i = psu.measure_current()
    print(f"{v:.2f}V, {i:.3f}A")

psu.turn_off()
psu.disconnect()
```

## KA3010P: Current Limit Behavior

```python
from lab_drivers.drivers.serial import KA3010P

psu = KA3010P()
psu.set_voltage(12.0)
psu.set_current(0.5)
psu.set_output_state(True)

print(f"Measured current: {psu.measure_current():.3f}A")

psu.set_output_state(False)
psu.disconnect()
```

## StanfordPS310: Safe High-Voltage Sequence

```python
from lab_drivers.drivers.visa import StanfordPS310

hv = StanfordPS310()
hv.set_voltage(-200.0)
hv.set_output_state(True)
print(hv.measure_voltage())
hv.set_voltage(0.0)
hv.set_output_state(False)
hv.disconnect()
```
