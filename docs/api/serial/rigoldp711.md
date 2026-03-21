# RigolDP711

Programmable DC Power Supply with serial RS-232 connectivity.

## Device Specifications

| Parameter | Specification |
|-----------|---------------|
| Model | Rigol DP711 |
| Voltage Range | 0-30V |
| Current Range | 0-5A |
| Interface | RS-232 (USB adapter) |
| Specs | Low-noise, isolated output |

## Overview

The RigolDP711 driver provides comprehensive control of the Rigol DP711 programmable DC power supply via USB-to-RS232 adapter.

## Quick Start

```python
from lab_drivers.drivers.serial import RigolDP711

# Auto-connect to DP711
psu = RigolDP711()

# Set voltage and current
psu.set_voltage(12.0)
psu.set_current(2.5)
psu.turn_on()

# Measure
voltage = psu.measure_voltage()
current = psu.measure_current()
print(f"Output: {voltage:.2f}V @ {current:.3f}A")

# Cleanup
psu.turn_off()
psu.disconnect()
```

## Supported Commands

| Command | Function | Returns |
|---------|----------|---------|
| `set_voltage(v)` | Set output voltage (V) | - |
| `set_current(i)` | Set current limit (A) | - |
| `measure_voltage()` | Read actual voltage | float (V) |
| `measure_current()` | Read actual current | float (A) |
| `turn_on()` / `turn_off()` | Enable/disable output | - |
| `set_output_state(state)` | Set output on/off | - |
| `get("voltage")` | Generic voltage getter | float (V) |
| `get("current")` | Generic current getter | float (A) |

## API Reference

::: lab_drivers.drivers.serial.RigolDP711

## Connection Methods

### Auto-Detection
```python
psu = RigolDP711()  # Auto-finds first available DP711
```

### Explicit COM Port
```python
psu = RigolDP711(com_port="/dev/ttyUSB0")  # Linux
psu = RigolDP711(com_port="COM3")          # Windows
```

### Environment Variable
```bash
export DP711_COM_PORT=/dev/ttyUSB0
```

Then:
```python
psu = RigolDP711()  # Uses environment variable
```

## Usage Patterns

### Voltage/Current Sweep
```python
psu = RigolDP711()
psu.turn_on()

voltages = [5, 10, 15, 20, 25, 30]
for v in voltages:
    psu.set_voltage(v)
    i = psu.measure_current()
    print(f"{v}V: {i:.3f}A")

psu.turn_off()
psu.disconnect()
```

### Load Testing
```python
psu = RigolDP711()
psu.set_voltage(12.0)
psu.set_current(5.0)
psu.turn_on()

# Monitor for 1 minute
import time
start = time.time()
while time.time() - start < 60:
    v = psu.measure_voltage()
    i = psu.measure_current()
    p = v * i
    print(f"V:{v:.2f}V I:{i:.3f}A P:{p:.2f}W")
    time.sleep(1)

psu.turn_off()
psu.disconnect()
```

## Troubleshooting

### "No COM ports found"
- Verify USB adapter is connected
- Check device manager for COM port
- Specify explicit COM port: `RigolDP711(com_port="COM3")`

### Connection drops
- Try longer inter-command delays: `psu.ser.timeout = 3`
- Check USB cable quality
- Restart the power supply

### Incorrect readings
- Ensure power supply is stable (wait 10-30 seconds after power-on)
- Check for voltage divider/adapter cables
- Verify with manual measurement on device

## Related

- [KA3010P](ka3010p.md) - Alternative 0-30V/0-10A power supply
- [Getting Started](../../getting-started.md) - Basic patterns
- [Examples](../../examples/power-supplies.md) - More power supply examples
