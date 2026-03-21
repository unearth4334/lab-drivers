# API Reference

Complete API documentation for all supported laboratory instruments.

## Serial Drivers (RS-232/USB)

| Driver | Device Type | Key Features |
|--------|-------------|--------------|
| [RigolDP711](serial/rigoldp711.md) | Programmable DC PSU | 0-30V / 0-5A, RS-232, type hints |
| [KA3010P](serial/ka3010p.md) | Programmable DC PSU | 0-30V / 0-10A, RS-232, full docstrings |
| [FLUKE45](serial/fluke45.md) | Bench Multimeter | 4.5-digit DMM, dual-display, type hints |

## VISA Drivers (USB/Ethernet/GPIB)

| Driver | Device Type | Key Features |
|--------|-------------|--------------|
| [RSA3030](visa/rsa3030.md) | Spectrum Analyzer | 100 kHz-3 GHz, link-local discovery, auto-detect |
| [DL3021](visa/dl3021.md) | Electronic Load | CC/CV/CR/CP modes, 150W, type hints |
| [StanfordPS310](visa/stanfordps310.md) | High Voltage PSU | ±1250V, GPIB, glitch filtering, debug logging |
| [KS33500B](visa/ks33500b.md) | Waveform Generator | Dual channel, 1μHz-30MHz, modulation support |

## Standard Interface

All drivers implement these standard methods:

### Connection
- `connect(**kwargs)` - Establish connection to device
- `disconnect()` - Close connection
- `__init__(auto_connect=True, **kwargs)` - Initialize and optionally auto-connect

### Measurement
- `measure_voltage()` - Measure voltage (device-specific return type)
- `measure_current()` - Measure current (device-specific return type)
- `measure_resistance()` - Measure resistance (if applicable)
- `get(item, **kwargs)` - Generic getter for any measurement/property

### Configuration
- `set_voltage(voltage, **kwargs)` - Set voltage output
- `set_current(current, **kwargs)` - Set current limit
- `set_output_state(state, **kwargs)` - Enable/disable output
- Device-specific methods (e.g., `set_frequency()`, `set_mode()`)

## Connection Methods

### Auto-Detection (Recommended)
```python
from lab_drivers.drivers.serial import RigolDP711
psu = RigolDP711()  # Auto-detects and connects
```

### Explicit Addressing
```python
# Serial port
psu = RigolDP711(com_port="/dev/ttyUSB0")

# VISA address
load = DL3021(address="GPIB0::10::INSTR")

# IP address
spectrum = RSA3030(ip_address="192.168.1.100")
```

## Supported Measurements

### Basic Measurements
All power supply drivers support:
- **Voltage** - `measure_voltage()` → float (V)
- **Current** - `measure_current()` → float (A)

### Multi-Channel Measurements
Multi-channel drivers (spectrum analyzer, waveform generator) support per-channel queries:
```python
# Example: Multi-channel oscilloscope
stats = device.get("statistics", channel=1)  # [mean, std, min, max]
```

### Statistical Data
High-precision instruments support statistical readback:
```python
stats = device.get("statistics")
mean, std_dev, minimum, maximum = stats
```

Format varies by instrument:
- **Multimeters/Load**: `[mean, std_dev, min, max]` (4-tuple)
- **Oscilloscopes**: `[mean, std_dev, min, max, peak_to_peak]` (5-tuple)

## Device Categories

### Power Supplies
- **RigolDP711** - 0-30V/0-5A, RS-232
- **KA3010P** - 0-30V/0-10A, RS-232
- **StanfordPS310** - ±1250V, GPIB (high voltage)

### Multimeters
- **FLUKE45** - 4.5-digit, dual-display, RS-232
- **KA3010P** - (Also supports current limiting)

### Measurement & Testing
- **RSA3030** - Spectrum analyzer, 100 kHz-3 GHz
- **DL3021** - Electronic load, CCCurrentValue/CV/CR/CP modes

### Signal Generation
- **KS33500B** - Dual-channel waveform generator, 1μHz-30MHz

## Next Steps

- **[Getting Started](../getting-started.md)** - Basic usage patterns
- **[Examples](../examples/quickstart.md)** - Code examples for common tasks
