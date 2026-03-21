# Lab Drivers: Laboratory Instrument Control API

Welcome to **Lab Drivers**, a comprehensive Python framework for controlling scientific instruments and laboratory equipment. This documentation provides complete API references and usage examples for all supported bench devices.

## What is Lab Drivers?

Lab Drivers is a device-agnostic Python package that provides standardized interfaces for controlling multiple laboratory instruments including:

- **Power Supplies** - Programmable DC power supplies with voltage and current control
- **Multimeters** - High-precision digital multimeters and bench meters
- **Oscilloscopes** - Mixed-signal and digital oscilloscopes
- **Electronic Loads** - Programmable DC electronic loads
- **Waveform Generators** - Function and arbitrary waveform generators
- **Spectrum Analyzers** - RF/microwave spectrum analysis

## Key Features

✅ **Standardized API** - Consistent interface across all drivers: `connect()`, `disconnect()`, `get()`, `measure_*()` methods  
✅ **Auto-Detection** - Automatically find instruments on VISA bus or serial ports  
✅ **Type Hints** - Full type annotations for IDE autocompletion and type checking  
✅ **Flexible Connectivity** - Serial (RS-232/USB), VISA (USB/Ethernet/GPIB)  
✅ **Multi-Channel Support** - Built-in support for multi-channel instruments  
✅ **Statistics** - High-precision instruments support statistical readback (mean, std dev, min, max)  
✅ **Production-Ready** - Comprehensive error handling and colorama-styled console output  

## Supported Devices

### Serial Drivers (RS-232 / USB)
| Device | Type | Specs |
|--------|------|-------|
| [RigolDP711](api/serial/rigoldp711.md) | Programmable DC PSU | 0-30V / 0-5A |
| [KA3010P](api/serial/ka3010p.md) | Programmable DC PSU | 0-30V / 0-10A |
| [FLUKE45](api/serial/fluke45.md) | Dual-Display Bench DMM | 4.5-digit, DC/AC, Resistance |

### VISA Drivers (USB / Ethernet / GPIB)
| Device | Type | Specs |
|--------|------|-------|
| [RSA3030](api/visa/rsa3030.md) | Spectrum Analyzer | 100 kHz - 3 GHz |
| [DL3021](api/visa/dl3021.md) | Electronic Load | CC/CV/CR/CP, 150W |
| [StanfordPS310](api/visa/stanfordps310.md) | High Voltage PSU | ±1250V, 5mA, GPIB |
| [KS33500B](api/visa/ks33500b.md) | Waveform Generator | Dual Channel, 1μHz - 30MHz |

## Quick Start

```python
from lab_drivers.drivers.serial import RigolDP711
from lab_drivers.drivers.visa import DL3021

# Programmable power supply
psu = RigolDP711()  # Auto-connects
psu.set_voltage(12.0)
psu.set_current(2.5)
psu.turn_on()

voltage = psu.measure_voltage()
current = psu.measure_current()
print(f"Output: {voltage:.2f}V @ {current:.3f}A")

psu.turn_off()
psu.disconnect()

# Electronic load
load = DL3021()
load.set_mode("CC")
load.set_current(1.0)
load.set_output_state(True)

# ... measurements ...

load.set_output_state(False)
load.disconnect()
```

## Installation

```bash
# Install with all drivers (serial + VISA)
pip install -e ".[all]"

# Install with specific drivers
pip install -e ".[serial]"    # Serial only
pip install -e ".[visa]"      # VISA only
```

See [Installation Guide](install.md) for detailed setup instructions including VISA driver installation.

## Getting Started

- **[Installation Guide](install.md)** - Complete setup instructions for macOS, Linux, Windows
- **[Getting Started](getting-started.md)** - Basic connection patterns and usage patterns
- **[API Reference](api/index.md)** - Detailed documentation for each driver
- **[Examples](examples/quickstart.md)** - Code examples for common tasks
- **[Architecture](architecture.md)** - Design principles and extension guide

## Key Concepts

### Connection Patterns
```python
# Auto-detection (recommended)
device = DeviceClass()  # Automatically finds instrument

# Explicit addressing
device = DeviceClass(address="USB0::...")  # VISA address
device = DeviceClass(com_port="COM3")      # Serial port
device = DeviceClass(ip_address="192.168.1.100")  # Ethernet
```

### Measurement Interface
```python
# Direct measurement methods
voltage = device.measure_voltage()
current = device.measure_current()

# Generic get() interface
value = device.get("voltage")
stats = device.get("statistics")  # [mean, std, min, max]
```

### Multi-Channel Support
```python
# Most multi-channel devices use channel parameter
device.set_voltage(12.0, channel=1)
device.set_voltage(5.0, channel=2)

voltage1 = device.measure_voltage(channel=1)
voltage2 = device.measure_voltage(channel=2)
```

## System Requirements

- **Python**: 3.9+
- **OS**: Windows, macOS, Linux
- **Dependencies**: colorama, numpy, (optional: pyvisa for VISA devices, pyserial for serial devices)

## Support & Documentation

- **Full API Reference**: See [API Documentation](api/index.md)
- **Code Examples**: See [Examples](examples/quickstart.md)
- **Architecture Guide**: See [Design & Architecture](architecture.md)
- **GitHub**: [lab-drivers repository](https://github.com/)

## License

Licensed under Apache License 2.0. See LICENSE file for details.

---

**Ready to get started?** See the [Installation Guide](install.md) and [Getting Started](getting-started.md) pages.
