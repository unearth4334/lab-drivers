# Installation Guide

Complete step-by-step instructions for installing Lab Drivers on macOS, Linux, and Windows.

## Prerequisites

- **Python 3.9+** (check with `python --version`)
- **pip** (check with `pip --version`)
- **git** (optional, for cloning the repository)

## Installation Options

### Option A: Install from Source (Recommended for Development)

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-org/lab-drivers.git
cd lab-drivers
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

### Option B: Install from PyPI

```bash
pip install lab-drivers[all]
```

### Option C: Selective Installation

Install only the transport layers you need:

```bash
# Serial devices only (RigolDP711, KA3010P, FLUKE45)
pip install -e ".[serial]"

# VISA devices only (RSA3030, DL3021, StanfordPS310, KS33500B)
pip install -e ".[visa]"

# Minimal install (core only, no instruments)
pip install -e "."
```

## Platform-Specific Setup

### macOS

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install lab-drivers with all drivers
pip install -e ".[all]"

# 3. For VISA devices, install NI-VISA (optional)
#    Download from: https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html
```

**Common Issues:**
- If PyVISA fails to find instruments, ensure NI-VISA is installed
- For serial devices, USB adapters should appear as `/dev/ttyUSB*` or `/dev/ttyACM*`

### Linux (Ubuntu/Debian)

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install python3-venv python3-dev libusb-1.0-0-dev

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install lab-drivers
pip install -e ".[all]"

# 4. Install VISA drivers (optional)
#    For PyVISA with Linux USB, install libusb:
sudo apt-get install libusb-1.0-0

# 5. Configure USB permissions for serial devices (optional)
# Add your user to dialout group to access /dev/ttyUSB* without sudo
sudo usermod -a -G dialout $USER
# You may need to log out and log back in
```

**Common Issues:**
- Permission denied on `/dev/ttyUSB*`: Add yourself to dialout group (see above)
- PyVISA can't find Ethernet instruments: Ensure network connectivity and check IP configuration

### Windows

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install lab-drivers
pip install -e ".[all]"

# 3. Install NI-VISA (recommended for VISA devices)
#    Download from: https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html
```

**Common Issues:**
- COM port not found: Open Device Manager and check the COM port number
- USB driver issues: Install the USB driver from the instrument manufacturer's website
- VISA not found: Install NI-VISA or download `visa64.dll` from National Instruments

## Verifying Installation

### Test Serial Device Connection

```python
from lab_drivers.drivers.serial import RigolDP711

try:
    psu = RigolDP711()
    print(f"Connected: {psu.identity}")
    psu.disconnect()
except Exception as e:
    print(f"Error: {e}")
```

### Test VISA Device Connection

```python
from lab_drivers.drivers.visa import DL3021

try:
    load = DL3021()
    print(f"Connected: {load.identity}")
    load.disconnect()
except Exception as e:
    print(f"Error: {e}")
```

### List Available VISA Resources (for VISA devices)

```python
import pyvisa

rm = pyvisa.ResourceManager()
print(rm.list_resources())
```

## Environment Variables

### Serial Port Configuration

Some drivers look for environment variables to auto-detect serial ports:

```bash
# Set COM port for RigolDP711
export DP711_COM_PORT=/dev/ttyUSB0  # Linux/macOS
set DP711_COM_PORT=COM3              # Windows
```

### VISA Address Caching

Some VISA drivers cache the last successful address for faster reconnection:

```bash
# Disable caching (forces re-scan on next connection)
export VISA_ADDRESS_CACHE=0
```

## Upgrading

```bash
# Upgrade to latest version
pip install --upgrade lab-drivers[all]

# Upgrade specific version
pip install lab-drivers[all]==0.2.0
```

## Uninstalling

```bash
pip uninstall lab-drivers
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pyvisa'"

**Solution:** Install VISA support:
```bash
pip install "lab-drivers[visa]"
```

### "ModuleNotFoundError: No module named 'serial'"

**Solution:** Install serial support:
```bash
pip install "lab-drivers[serial]"
```

### "No instrument found"

**Solution:** 
1. Check physical connections (USB cable, network, GPIB adapter)
2. Test manually with `ResourceManager` or serial port monitor
3. Try explicit addressing instead of auto-detection
4. Check that the correct drivers are installed for your OS

### "Permission denied" (Linux/macOS)

**Solution:**
```bash
# For serial ports (Linux)
sudo usermod -a -G dialout $USER

# For USB devices, you may need udev rules
# Contact your system administrator for help
```

### "VISA library not found"

**Solution:**
1. Ensure NI-VISA is installed and PATH is updated
2. Restart your terminal after installing NI-VISA
3. On Linux, ensure `libusb-1.0` is installed: `sudo apt-get install libusb-1.0-0`

## Next Steps

- **[Getting Started](getting-started.md)** - Learn basic connection patterns
- **[API Reference](api/index.md)** - Explore device-specific APIs
- **[Examples](examples/quickstart.md)** - See code examples for common tasks
