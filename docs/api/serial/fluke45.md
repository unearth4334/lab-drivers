# FLUKE45

Dual-Display Bench Multimeter with RS-232 serial connectivity.

## Device Specifications

| Parameter | Specification |
|-----------|---------------|
| Model | Fluke 45 Dual Display Multimeter |
| Resolution | 4.5 digits |
| Display | Dual (simultaneous measurements) |
| Interface | RS-232 serial |
| Functions | V (DC/AC), I (DC/AC), Ω, Frequency |
| Accuracy | Basic: ±(0.09% × reading + 1) |

## Overview

The FLUKE45 driver provides control of the Fluke 45 dual-display bench multimeter via RS-232 interface. This is a classic benchtop multimeter with exceptional AC/DC accuracy and dual display capability.

## Quick Start

```python
from lab_drivers.drivers.serial import FLUKE45

# Auto-connect to Fluke 45
dmm = FLUKE45()

# Measure DC voltage
voltage = dmm.measure_voltage()
print(f"DC Voltage: {voltage:.4f}V")

# Measure resistance
resistance = dmm.measure_resistance()
print(f"Resistance: {resistance:.2f}Ω")

# Measure current
current = dmm.measure_current()
print(f"Current: {current:.6f}A")

dmm.disconnect()
```

## Supported Commands

| Command | Function | Returns |
|---------|----------|---------|
| `measure_voltage()` | Measure DC voltage | float (V) |
| `measure_current()` | Measure DC current | float (A) |
| `measure_resistance()` | Measure resistance | float (Ω) |
| `measure_ac_voltage()` | Measure AC voltage | float (V) |
| `measure_ac_current()` | Measure AC current | float (A) |
| `measure_frequency()` | Measure frequency | float (Hz) |
| `measure_avg(n)` | Average n measurements | float |
| `get(item)` | Generic getter | float |

## API Reference

::: lab_drivers.drivers.serial.FLUKE45

## Connection Methods

### Auto-Detection
```python
dmm = FLUKE45()  # Auto-finds first available Fluke 45
```

### Explicit COM Port
```python
dmm = FLUKE45(com_port="/dev/ttyUSB0")  # Linux/macOS
dmm = FLUKE45(com_port="COM3")          # Windows
```

### Specify Baud Rate
```python
dmm = FLUKE45(baud_rate=9600)  # Default is 9600
```

## Measurement Functions

### DC Measurements
```python
dmm = FLUKE45()

# DC Voltage (0-1000V range)
voltage = dmm.measure_voltage()

# DC Current (0-10A range)
current = dmm.measure_current()

# Resistance (0-20MΩ range)
resistance = dmm.measure_resistance()

dmm.disconnect()
```

### AC Measurements
```python
dmm = FLUKE45()

# AC Voltage RMS
ac_voltage = dmm.measure_ac_voltage()

# AC Current RMS
ac_current = dmm.measure_ac_current()

# Frequency (for AC signals)
freq = dmm.measure_frequency()

dmm.disconnect()
```

### Averaging
```python
dmm = FLUKE45()

# Average 10 DC voltage measurements
avg_voltage = dmm.measure_avg(10)
print(f"Average: {avg_voltage:.4f}V")

dmm.disconnect()
```

## Usage Patterns

### Power Supply Characterization
```python
dmm = FLUKE45()

# Measure ripple at different loads
print("Voltage | Current | Stability")
for load_ohms in [100, 50, 10]:
    voltage = dmm.measure_avg(10)
    current = dmm.measure_avg(10)
    print(f"{voltage:.3f}V | {current:.3f}A | Check ripple")

dmm.disconnect()
```

### Component Testing
```python
dmm = FLUKE45()

# Test resistor tolerance
actual_resistance = dmm.measure_resistance()
expected_resistance = 10000  # 10kΩ nominal
tolerance = ((actual_resistance - expected_resistance) / expected_resistance) * 100
print(f"Measured: {actual_resistance:.1f}Ω")
print(f"Tolerance: {tolerance:+.1f}%")

dmm.disconnect()
```

### AC Circuit Analysis
```python
dmm = FLUKE45()

# Measure AC line voltage and frequency
ac_voltage = dmm.measure_ac_voltage()
frequency = dmm.measure_frequency()
print(f"Line Voltage: {ac_voltage:.1f}V @ {frequency:.1f}Hz")

dmm.disconnect()
```

## Specifications & Limits

**DC Voltage**
- Range: 100mV to 1000V
- Accuracy: ±(0.09% + 1 digit)
- Input Impedance: >10MΩ

**AC Voltage**
- Range: 100mV to 750V RMS
- Accuracy: ±(0.5% + 3 digits)
- Frequency: 45Hz to 1kHz

**DC Current**
- Range: 100μA to 10A
- Accuracy: ±(0.2% + 1 digit)
- Shunt: Built-in 0.1Ω (10A range)

**Resistance**
- Range: 100Ω to 20MΩ
- Accuracy: ±(0.1% + 2 digits)

**Frequency**
- Range: 45Hz to 5kHz
- Accuracy: ±0.1%

## Troubleshooting

### "No COM ports found"
- Verify RS-232 adapter is connected
- Check Device Manager for COM port
- Specify explicit COM port: `FLUKE45(com_port="COM3")`

### Erratic readings
- Wait 200-500ms between readings for stability
- Avoid switching ranges too quickly
- Use `measure_avg()` for noisy signals

### "Connection timeout"
- Verify baud rate is 9600
- Check cable connections
- Reset multimeter power cycle

## Classic Fluke45 Notes

- Dual display allows simultaneous measurement of two parameters
- Manual range selection (no auto-range) provides stable readings
- Excellent AC/DC accuracy (0.09% basic)
- Rugged construction suitable for industrial use

## Related

- [KA3010P](ka3010p.md) - Power supply with measurement
- [Examples](../../examples/measurement-devices.md) - More measurement examples
- [Getting Started](../../getting-started.md) - Basic patterns
