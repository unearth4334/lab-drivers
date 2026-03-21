# Architecture & Design Principles

This document describes the design principles, architecture, and extension patterns for Lab Drivers.

## Core Design Principles

### 1. Standardized API Across Devices

All drivers implement a consistent interface regardless of transport (serial, VISA) or protocol (SCPI, vendor-specific):

```python
# Same pattern for all drivers
device.connect()
device.disconnect()
value = device.measure_voltage()
device.set_voltage(12.0)
device.set_output_state(True)
stats = device.get("statistics")
```

**Benefits:**
- Developers can switch between instruments without learning new APIs
- Code is portable across different device types
- Easier testing and mocking

### 2. Transport Independence

Device logic is separated from communication transport:

- **Serial Drivers**: Handle RS-232 communication via PySerial
- **VISA Drivers**: Use PyVISA for USB, GPIB, Ethernet

Device classes don't expose transport details—they only expose functional interfaces.

### 3. Auto-Detection with Fallback

All drivers support automatic connection:

```python
device = DeviceClass()  # Auto-detect
```

If auto-detection fails, explicit addressing provides fine-grained control:

```python
device = DeviceClass(address="GPIB0::10::INSTR")
device = DeviceClass(com_port="COM3")
device = DeviceClass(ip_address="192.168.1.100")
```

### 4. Type Safety

Modern Python drivers (RigolDP711, KA3010P, FLUKE45, RSA3030, DL3021, StanfordPS310, KS33500B) use full type hints:

```python
def set_voltage(self, voltage: float, channel: Optional[int] = None) -> None:
    """Set output voltage."""
    ...

def measure_current(self) -> float:
    """Measure output current in Amps."""
    return float(...)
```

**Benefits:**
- IDE autocompletion
- Type checking with mypy/pyright
- Self-documenting code

### 5. Backward Compatibility

Lab Drivers follows semantic versioning with guaranteed API stability within major versions:

- **0.x.y**: Beta phase, frequent API changes
- **1.x.y**: Stable API, backward-compatible within major version
- **2.0.0+**: New major version only for breaking changes

Deprecated features receive a deprecation warning before removal.

## Architecture Overview

```
lab-drivers/
├── src/lab_drivers/
│   ├── __init__.py                   # Public API exports
│   ├── core/                         # Core patterns (base classes, utilities)
│   │   ├── __init__.py
│   │   └── base.py                   # (future) Base device class
│   └── drivers/
│       ├── __init__.py               # Exports all drivers
│       ├── serial/                   # Serial (RS-232) drivers
│       │   ├── __init__.py           # Exports: RigolDP711, KA3010P, FLUKE45
│       │   ├── RigolDP711.py
│       │   ├── KA3010P.py
│       │   ├── FLUKE45.py
│       │   └── U1233A.py
│       └── visa/                     # VISA (USB/GPIB/Ethernet) drivers
│           ├── __init__.py           # Exports: 10 visa drivers
│           ├── RSA3030.py
│           ├── DL3021.py
│           ├── StanfordPS310.py
│           ├── KS33500B.py
│           └── ...
├── docs/                             # This documentation (MkDocs)
├── tests/                            # Test suite (pytest)
├── pyproject.toml                    # Build configuration
├── mkdocs.yml                        # Documentation config
└── README.md                         # Quick start guide
```

## Device Class Structure

### Minimal Device Driver

A minimal driver implements:

```python
from typing import Optional
from colorama import Fore, Style
import pyvisa

class MyDevice:
    """Description of device."""
    
    def __init__(self, auto_connect: bool = True, **kwargs):
        self.resource: Optional[pyvisa.Resource] = None
        self.address: Optional[str] = None
        
        if auto_connect:
            self.connect(**kwargs)
    
    def connect(self, address: Optional[str] = None) -> None:
        """Connect to device."""
        # Find and connect to device
        # Set self.address and self.resource
        pass
    
    def disconnect(self) -> None:
        """Disconnect from device."""
        if self.resource:
            self.resource.close()
            self.resource = None
    
    def get(self, item: str, **kwargs):
        """Generic getter for any measurement/property."""
        if item == "voltage":
            return self.measure_voltage(**kwargs)
        elif item == "identity":
            return self._query("*IDN?")
        else:
            raise ValueError(f"Unknown item: {item}")
    
    def measure_voltage(self) -> float:
        """Measure voltage in volts."""
        response = self._query("MEAS:VOLT?")
        return float(response)
    
    def set_voltage(self, voltage: float) -> None:
        """Set voltage in volts."""
        self._write(f"VOLT {voltage}")
    
    def _query(self, command: str) -> str:
        """Send SCPI query and read response."""
        return self.resource.query(command).strip()
    
    def _write(self, command: str) -> None:
        """Send SCPI command."""
        self.resource.write(command)
```

### Key Patterns

#### Connection Auto-Detection

Serial drivers scan available COM ports:

```python
import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
for port in ports:
    try:
        ser = serial.Serial(port.device, timeout=1)
        identity = ser.read_until(b'\n')
        if b'MYDEVICE' in identity:
            return port.device
    finally:
        ser.close()
```

VISA drivers scan VISA resources:

```python
import pyvisa

rm = pyvisa.ResourceManager()
resources = rm.list_resources()
for addr in resources:
    try:
        res = rm.open_default_resource(addr)
        identity = res.query("*IDN?")
        if "MYDEVICE" in identity:
            return addr
    finally:
        res.close()
```

#### Error Handling with Styling

Use colorama for styled console output:

```python
from colorama import Fore, Style, init
init(autoreset=True)

_ERROR_STYLE = Fore.RED + Style.BRIGHT + "Error! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "Warning! "

print(_ERROR_STYLE + "Connection failed")
print(_SUCCESS_STYLE + "Connected successfully")
print(_WARNING_STYLE + "Low voltage detected")
```

#### Multi-Channel Support

```python
def set_voltage(self, voltage: float, channel: Optional[int] = None) -> None:
    """Set voltage on specific channel."""
    if channel is None:
        # Default to channel 1 for single-channel devices
        channel = 1
    
    cmd = f"VOLT {voltage}"
    if channel is not None:
        cmd = f"VOLT{channel}:OUT {voltage}"
    
    self._write(cmd)
```

#### Statistics Support

High-precision instruments provide statistical readback:

```python
def get(self, item: str, **kwargs):
    if item == "statistics":
        avg = float(self._query("MEAS:VOLT:MEAN?"))
        std = float(self._query("MEAS:VOLT:STDEV?"))
        min_val = float(self._query("MEAS:VOLT:MIN?"))
        max_val = float(self._query("MEAS:VOLT:MAX?"))
        return [avg, std, min_val, max_val]
    else:
        ...
```

## Extension Points

### Adding a New Driver

1. **Create device class** in appropriate subdirectory:
   - Serial: `src/lab_drivers/drivers/serial/MyDevice.py`
   - VISA: `src/lab_drivers/drivers/visa/MyDevice.py`

2. **Implement standard interface**:
   - `__init__`, `connect()`, `disconnect()`
   - `measure_*()` methods for common measurements
   - `set_*()` methods for configuration
   - `get(item)` generic interface

3. **Add to exports** in `src/lab_drivers/drivers/{serial|visa}/__init__.py`:
   ```python
   from .MyDevice import MyDevice
   __all__ = [...existing..., "MyDevice"]
   ```

4. **Add documentation**:
   - Module docstring with Features, Basic Usage, Examples
   - Method docstrings with Args/Returns
   - Create `docs/api/serial/mydevice.md` (or visa/)

5. **Test**:
   - Create test file in `tests/test_mydevice.py`
   - Test with actual hardware if possible

### Deprecation Policy

To deprecate a feature:

1. Add deprecation warning in the code:
   ```python
   import warnings
   warnings.warn("foo() is deprecated, use bar() instead", DeprecationWarning, stacklevel=2)
   ```

2. Document in release notes
3. Keep deprecated feature working for at least 1 major version
4. Remove in next major version

## Design Patterns Used

### Factory Pattern
Auto-detection uses factory-like pattern to create appropriate device instances.

### Adapter Pattern
VISA and Serial drivers abstract underlying PyVISA and PySerial APIs.

### Composition over Inheritance
Current design uses composition (each driver owns resource/connection) rather than inheritance from base class (future enhancement).

### Dependency Injection
Optional dependencies (pyvisa, pyserial) are installed on-demand via extras.

## Performance Considerations

- **Connection Caching**: Some drivers cache the last successful VISA address for faster reconnection
- **Batch Operations**: For high-speed measurements, consider batching via device buffers
- **Timeout Management**: Drivers use reasonable timeouts for VISA operations (usually 1-5 seconds)

## Testing Strategy

Lab Drivers uses pytest with mock instruments for CI/CD:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lab_drivers

# Run tests for specific device
pytest tests/test_rigoldp711.py
```

## Future Enhancements

- [ ] Base device class for shared functionality
- [ ] Async/await support for high-speed measurements
- [ ] Caching of measurements for batch operations
- [ ] Integration with LabVIEW and MATLAB
- [ ] Web API for remote device access
- [ ] Data logging and analysis framework

## References

- [PyVISA Documentation](https://pyvisa.readthedocs.io)
- [PySerial Documentation](https://pyserial.readthedocs.io)
- [SCPI Standard](https://www.ivifoundation.org/specifications/default.aspx)
- [Python Typing Guide](https://docs.python.org/3/library/typing.html)
