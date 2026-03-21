# StanfordPS310

Stanford Research Systems PS310 High Voltage Power Supply with GPIB control.

## Device Specifications

| Parameter | Specification |
|-----------|---------------|
| Model | Stanford Research Systems PS310 |
| Voltage Range | 0 to ±1250V (model dependent) |
| Current Range | 0 to ±5 mA |
| Output Power | Up to 6.25W |
| Interface | GPIB (via NI GPIB-USB-HS adapter) |
| Stability | < 10 ppm/°C |
| Ripple | < 3 mV RMS |

## Overview

The StanfordPS310 driver provides comprehensive control of high voltage power supplies with advanced features including glitch filtering, debug logging, and environment-based configuration.

## Quick Start

```python
from lab_drivers.drivers.visa import StanfordPS310

# Auto-connect to PS310
hvps = StanfordPS310()

# Set target voltage (note: negative for some models)
hvps.set_voltage(-500.0)  # -500V

# Enable output
hvps.set_output_state(True)

# Measure voltage and current
voltage = hvps.measure_voltage()
current = hvps.measure_current()
print(f"Output: {voltage:.2f}V @ {current*1e6:.2f}μA")

# Disable output
hvps.set_output_state(False)
hvps.disconnect()
```

## Supported Commands

| Command | Function | Returns |
|---------|----------|---------|
| `set_voltage(v)` | Set target voltage (V) | - |
| `measure_voltage()` | Read actual voltage | float (V) |
| `measure_current()` | Read actual current | float (A) |
| `set_output_state(state)` | Enable/disable output | - |
| `get(item)` | Generic getter | varies |
| `_query(cmd)` | Send GPIB query | str |
| `_write(cmd)` | Send GPIB command | - |

## API Reference

::: lab_drivers.drivers.visa.StanfordPS310

## Connection Methods

### Auto-Detection (USB via GPIB Adapter)
```python
# Requires NI GPIB-USB-HS adapter
hvps = StanfordPS310()  # Auto-finds PS310 on GPIB bus
```

### Explicit GPIB Address
```python
hvps = StanfordPS310(address="GPIB0::5::INSTR")  # GPIB address 5
```

### Ethernet Connection (if available)
```python
hvps = StanfordPS310(address="TCPIP0::192.168.1.100::INSTR")
```

## Advanced Features

### Glitch Filtering

The driver includes automatic filtering of transient readings:

```python
hvps = StanfordPS310()
hvps.set_voltage(-500.0)
hvps.set_output_state(True)

# Automatic filtering configured via environment variables:
# PS310_GLITCH_THRESHOLD: Voltage deviation threshold (1.0% default)
# PS310_GLITCH_RETRIES: Number of read attempts (3 default)

voltage = hvps.measure_voltage()  # Returns filtered result
current = hvps.measure_current()

hvps.disconnect()
```

### Debug Logging

Enable verbose debug output:

```bash
export PS310_DEBUG_LEVEL=2   # 0=silent, 1=errors, 2=all
python your_script.py
```

## Usage Patterns

### High Voltage Ramp-Down Safety
```python
hvps = StanfordPS310()
hvps.set_voltage(-500.0)
hvps.set_output_state(True)

# Slow ramp-down for safety
target = 0.0
while hvps.measure_voltage() > target + 10:
    current_v = hvps.measure_voltage()
    step = min(-10, target - current_v)  # 10V steps maximum
    hvps.set_voltage(current_v + step)
    time.sleep(0.5)  # Wait between steps

# Final ramp to exact zero
hvps.set_voltage(target)
hvps.set_output_state(False)
hvps.disconnect()
```

### Voltage Stability Monitoring
```python
hvps = StanfordPS310()
hvps.set_voltage(-250.0)
hvps.set_output_state(True)

readings = []
print("Monitoring voltage stability for 60 seconds...")

for _ in range(60):
    voltage = hvps.measure_voltage()
    readings.append(voltage)
    time.sleep(1)

import statistics
mean = statistics.mean(readings)
stdev = statistics.stdev(readings)
ripple = max(readings) - min(readings)

print(f"Mean: {mean:.3f}V")
print(f"Std Dev: {stdev:.6f}V")
print(f"Ripple (P-P): {ripple:.6f}V")

hvps.disconnect()
```

### Proportional Load Testing
```python
hvps = StanfordPS310()

# Test at different voltage setpoints
voltages = [-250, -500, -750, -1000]
for target_v in voltages:
    hvps.set_voltage(target_v)
    hvps.set_output_state(True)
    time.sleep(2)  # Settle time
    
    v = hvps.measure_voltage()
    i = hvps.measure_current()
    p = abs(v * i)
    
    print(f"Set: {target_v:6.0f}V | Actual: {v:8.2f}V | I: {i*1e6:6.1f}μA | P: {p*1e6:6.2f}μW")
    
    hvps.set_output_state(False)
    time.sleep(1)

hvps.disconnect()
```

## Specifications & Limits

**Voltage Setting Resolution**: 0.1V
**Current Setting**: Automatic, typically < 100μA unloaded
**Overvoltage Protection**: Yes (typically ±10% over setpoint)
**Slew Rate**: ~100V/second (typical)
**Warm-up Time**: ~15-30 minutes recommended for full stability
**Temperature Coefficient**: < 10 ppm/°C

## Environmental Configuration

Set via environment variables before running:

```bash
# Glitch filtering threshold (default: 1.0)
export PS310_GLITCH_THRESHOLD=0.5

# Number of retry samples for glitch filtering (default: 3)
export PS310_GLITCH_RETRIES=5

# Debug level: 0=silent, 1=errors, 2=all commands (default: 0)
export PS310_DEBUG_LEVEL=2
```

## Troubleshooting

### "No PS310 found"
- Verify GPIB-USB adapter is connected
- Check GPIB cable connections
- Verify PS310 is powered on and in GPIB address mode
- List GPIB devices: Use NI GPIB Configuration or similar utility

### Voltage fluctuates
- Allow 30 seconds warm-up time after power-on
- Check for grounding issues
- Verify capacitive load is stable
- Enable glitch filtering by setting `PS310_GLITCH_RETRIES=5`

### "Connection timed out"
- Verify GPIB address (check device display or manual)
- Try explicit address: `StanfordPS310(address="GPIB0::5::INSTR")`
- Check GPIB cable and adapter power

### High current reading
- Verify output is disconnected from load
- Check for electrical shorts
- Reload firmware if stuck

## Safety Instructions

⚠️ **HIGH VOLTAGE HAZARD** ⚠️

- **Always discharge** loading capacitance before disconnecting
- **Ramp slowly** when changing high voltages
- **Use proper insulation** on all connections
- **Supervise operation** during testing
- **Disable output** immediately if abnormal behavior observed
- **Ground yourself** before touching circuits

## Related

- [Getting Started](../../getting-started.md) - Basic patterns
- [Architecture](../../architecture.md) - Design principles
- [Examples](../../examples/power-supplies.md) - More power supply examples
