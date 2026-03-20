#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   @file RSA3030.py
#   @brief Driver for Rigol RSA3030-TG Spectrum Analyzer using SCPI commands.
#   @date 12-Feb-2026

"""
Rigol RSA3030-TG Spectrum Analyzer Driver
=========================================

This module provides a SCPI-based driver for the Rigol RSA3030-TG spectrum analyzer
with support for auto-detection, USB, and Ethernet connectivity.

Features
--------
- **Auto-Detection**: Automatically finds RSA3030 on the VISA bus (USB or Ethernet)
- **Connection Caching**: Remembers last successful address for faster reconnection
- **Link-Local Discovery**: Probes common link-local IPs (169.254.x.x) if VISA scan fails
- **Ethernet Support**: Connect via IP address or TCPIP VISA resource string
- **USB Support**: Traditional USB connection via PyVISA
- **Full SCPI Control**: Direct low-level SCPI commands via query/write methods
- **Identity Query**: Retrieve instrument identification information
- **Type Hints**: Full type annotations for improved IDE support

Basic Usage
-----------
```python
from libs.RSA3030 import RSA3030

# Auto-connect (scans VISA resources + link-local IPs)
rsa = RSA3030()

# Get instrument identification
identity = rsa.get_identity()
print(f"Connected to: {identity}")

# Clean up
rsa.disconnect()
```

Explicit Addressing
-------------------
```python
# Connect to specific USB VISA address
rsa = RSA3030(auto_connect=False)
rsa.connect(address="USB0::0x1AB1::0x0960::RSA3XXXXXXXX::INSTR")

# Connect via Ethernet using IP address
rsa = RSA3030(auto_connect=False)
rsa.connect(ip_address="192.168.1.100")

# Or provide IP address at initialization
rsa = RSA3030(ip_address="192.168.1.100")

# Connect to specific TCPIP VISA address
rsa = RSA3030(auto_connect=False)
rsa.connect(address="TCPIP0::192.168.1.100::INSTR")
```

Identity Query
--------------
```python
# Get instrument identification
identity = rsa.get_identity()
print(f"Instrument: {identity}")

# Using the generic get() method
identity = rsa.get("identity")
print(f"Instrument: {identity}")
```

Spectrum Capture
----------------
```python
# Configure spectrum analyzer
rsa.configure_spectrum(
    center_freq=1e9,    # 1 GHz center
    span=100e6,         # 100 MHz span
    rbw=10e3,           # 10 kHz RBW
    vbw=10e3            # 10 kHz VBW
)

# Capture spectrogram (single sweep)
data = rsa.capture_spectrogram(filename="spectrum.csv")
print(f"Captured {data['points']} points")
print(f"Center: {data['center_freq']/1e9:.3f} GHz")
print(f"Span: {data['span']/1e6:.1f} MHz")

# Or just get trace data without saving
freqs, amps = rsa.capture_trace(trace_number=1)
print(f"Peak: {max(amps):.2f} dBm at {freqs[amps.index(max(amps))]/1e9:.3f} GHz")
```

Integration with data_logger
----------------------------
```python
from data_logger import data_logger

logger = data_logger()
logger.new_file("rsa3030_measurements.txt")

rsa = logger.connect("rsa3030")
logger.add(rsa, "identity", label="Instrument_ID")

# Collect measurements
logger.get_data()
    
logger.close_file()
```

Advanced Configuration
----------------------
```python
# Direct SCPI query
idn = rsa.instrument.query("*IDN?")
print(f"Connected to: {idn}")

# Direct SCPI command
rsa.instrument.write(":SYSTem:PRESet")
```

Supported Measurement Commands (for use with data_logger)
----------------------------------------------------------
The following commands are supported by the `get(item)` method:

- **"identity"** - Returns instrument identification string (*IDN? response)

Example:
```python
rsa = logger.connect("rsa3030")
identity = rsa.get("identity")
```

Measurement Functions
---------------------
- `get_identity()` - Retrieve instrument identification
- `capture_trace(trace_number)` - Capture trace data (frequencies and amplitudes)
- `capture_spectrogram(trace_number, filename)` - Capture spectrogram with metadata
- `get(item)` - Generic measurement getter (identity)

Configuration Functions
-----------------------
- `connect(address, ip_address)` - Establish connection
- `disconnect()` - Close connection
- `configure_spectrum(center_freq, span, rbw, vbw)` - Configure spectrum analyzer parameters

Error Handling
--------------
```python
try:
    rsa = RSA3030(address="WRONG::ADDRESS")
except ConnectionError as e:
    print(f"Connection failed: {e}")

try:
    identity = rsa.get_identity()
except Exception as e:
    print(f"Query failed: {e}")
```

SCPI Command Reference
-----------------------
The RSA3030 uses standard SCPI commands:
- `*IDN?` - Query instrument identification
- `*RST` - Reset instrument to default state
- `*CLS` - Clear status registers

Technical Specifications
------------------------
- **Frequency Range**: 9 kHz to 3 GHz
- **Interface**: USB, Ethernet/LAN via PyVISA
- **Ethernet**: Supports TCPIP connections via IP address (e.g., 192.168.1.100)
- **USB**: Supports standard USB VISA connections (e.g., USB0::0x1AB1::0x0960::...::INSTR)
- **Manufacturer**: Rigol Technologies
- **Model**: RSA3030-TG

Network Configuration
---------------------
**Finding the RSA3030 IP Address:**

1. On the RSA3030 front panel, press **System** or **Menu**
2. Navigate to: **Interface > LAN**
3. Note the displayed IP address

**Configuring Network Settings:**

1. Access the LAN settings menu
2. Configure network mode (DHCP or Static)
3. If using static IP, configure:
   - IP Address
   - Subnet Mask
   - Gateway
4. Apply settings and restart if necessary

**Network Requirements:**
- RSA3030 must be connected via Ethernet cable
- Computer and RSA3030 should be on the same network
- Firewall should allow VISA/LXI communication (typically port 5025)

Testing the Driver
------------------
Use the provided test script to verify connectivity:

```bash
# Auto-connect test
python test_rsa3030.py

# Connect via IP address
python test_rsa3030.py --ip 192.168.1.100

# Connect via explicit VISA address
python test_rsa3030.py --address "TCPIP0::192.168.1.100::INSTR"

# Interactive mode
python test_rsa3030.py --interactive

# Debug mode (shows detailed connection process)
python test_rsa3030.py --debug
```

Troubleshooting
---------------
**Connection Issues:**

1. **Find the actual IP address on the device:**
   - Check System > Interface > LAN settings
   - Verify network connectivity with ping

2. **Test network connectivity:**
   ```bash
   ping 192.168.1.100  # Replace with your RSA3030 IP
   ```

3. **Verify VISA resources are visible:**
   ```bash
   python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm.list_resources())"
   ```

4. **Check USB connection:**
   - Ensure USB cable is connected
   - Verify VISA drivers are installed (NI-VISA or similar)

See Also
--------
- DMM6500: Similar connection pattern implementation
- data_logger: Main orchestrator class
- Device driver standard: docs/DEVICE_DRIVER_STANDARD.md
"""

from __future__ import annotations

import time
import os
import json
from typing import Optional, List

import pyvisa
from colorama import init, Fore, Style

# Optional "loading" helper
try:
    from loading import loading
except Exception:
    class loading:
        def delay_with_loading_indicator(self, seconds: float) -> None:
            time.sleep(seconds)

# --- Console styles to match DMM6500 ---
_ERROR_STYLE   = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\r"
_DELAY         = 0.1

# Cache file for storing last successful connection
_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".lab_data_logging")
_CACHE_FILE = os.path.join(_CACHE_DIR, "rsa3030_last_address.json")


class RSA3030:
    """
    SCPI wrapper for Rigol RSA3030-TG Spectrum Analyzer.

    Example:
        rsa = RSA3030()                           # auto-detect
        identity = rsa.get_identity()
        print("Instrument:", identity)
        rsa.disconnect()
    """

    # -----------------------------
    # Init / Connect / Disconnect
    # -----------------------------
    def __init__(self, auto_connect: bool = True, address: Optional[str] = None, 
                 ip_address: Optional[str] = None, debug: bool = False):
        """
        Initialize RSA3030 driver.

        Args:
            auto_connect: If True, automatically connect during initialization.
            address: Explicit VISA resource string (e.g., "USB0::0x1AB1::0x0960::...::INSTR").
            ip_address: IP address for Ethernet connection (e.g., "192.168.1.100").
            debug: Enable debug output showing resource scanning details.
        """
        init(autoreset=True)

        self.rm = pyvisa.ResourceManager()
        self.address: Optional[str] = None
        self.instrument: Optional[pyvisa.resources.MessageBasedResource] = None
        self.loading = loading()
        self.status = "Not Connected"
        self._idn: Optional[str] = None
        self._address_hint = address
        self._ip_address = ip_address
        self.debug = debug

        if auto_connect:
            self.connect(address=self._address_hint, ip_address=self._ip_address)

    def connect(self, address: Optional[str] = None, ip_address: Optional[str] = None):
        """
        Establish a connection via USB or Ethernet.

        Args:
            address: Explicit VISA resource string. If None, auto-detect by scanning
                    USB resources containing 'RSA' or 'RSA3030' and all TCPIP resources,
                    then probing common link-local IPs (169.254.x.x) if needed.
                    Verify with *IDN? query.
            ip_address: IP address for Ethernet/LAN connection (e.g., "192.168.1.100").
                       If provided, constructs TCPIP resource string automatically.
        """
        # 1) Try IP address connection if provided
        ip = ip_address or self._ip_address
        if ip and not address and not self._address_hint:
            # Construct TCPIP resource string from IP address
            tcpip_address = f"TCPIP0::{ip}::INSTR"
            try:
                inst = self.rm.open_resource(tcpip_address)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000
                idn = inst.query("*IDN?").strip()
                if "RSA" in idn.upper() or "RIGOL" in idn.upper():
                    self.instrument = inst
                    self.address = tcpip_address
                    self._idn = idn
                    self.status = "Connected"
                    print(_SUCCESS_STYLE + f"Connected to RSA3030 via Ethernet at {ip} [{self._idn}]")
                    # Save successful address to cache
                    self._save_last_address(tcpip_address)
                    return
                else:
                    inst.close()
                    raise ConnectionError(_ERROR_STYLE +
                        f"Device at '{ip}' is not an RSA3030 (IDN='{idn}').")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE +
                    f"Failed to connect to RSA3030 at IP '{ip}': {e}")
        
        # 2) Try explicit address first (argument beats ctor hint)
        explicit = address or self._address_hint
        if explicit:
            try:
                inst = self.rm.open_resource(explicit)
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                inst.timeout = 20000
                idn = inst.query("*IDN?").strip()
                if "RSA" in idn.upper() or "RIGOL" in idn.upper():
                    self.instrument = inst
                    self.address = explicit
                    self._idn = idn
                    self.status = "Connected"
                    print(_SUCCESS_STYLE + f"Connected to RSA3030 at {explicit} [{self._idn}]")
                    # Save successful address to cache
                    self._save_last_address(explicit)
                    return
                else:
                    inst.close()
                    raise ConnectionError(_ERROR_STYLE +
                        f"Resource '{explicit}' is not an RSA3030 (IDN='{idn}').")
            except Exception as e:
                raise ConnectionError(_ERROR_STYLE +
                    f"Failed to open explicit address '{explicit}': {e}")

        # 2.5) Try cached address from previous successful connection
        if self.instrument is None:
            cached_address = self._load_last_address()
            if cached_address:
                if self.debug:
                    print(f"[DEBUG] Trying cached address: {cached_address}")
                try:
                    inst = self.rm.open_resource(cached_address)
                    inst.read_termination = '\n'
                    inst.write_termination = '\n'
                    inst.timeout = 5000  # Shorter timeout for cached attempt
                    idn = inst.query("*IDN?").strip()
                    if "RSA" in idn.upper() or "RIGOL" in idn.upper():
                        self.instrument = inst
                        self.address = cached_address
                        self._idn = idn
                        self.status = "Connected"
                        if self.debug:
                            print(f"[DEBUG]   - ✓ Connected via cached address!")
                        print(_SUCCESS_STYLE + f"Connected to RSA3030 at {self.address} [{self._idn}]")
                        return
                    else:
                        inst.close()
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG]   - Cached address failed: {e}")
                    # Continue to full scan if cached address doesn't work
                    pass

        # 3) Otherwise scan for resources with 'RSA' in the name (USB) or TCPIP resources
        # Note: Scans all TCPIP resources for maximum compatibility. Each resource is
        # verified with *IDN? query to confirm it's an RSA3030. For faster connection,
        # use explicit address or ip_address parameters.
        if self.instrument is None:
            resources = self.rm.list_resources()
            if self.debug:
                print(f"\n[DEBUG] Found {len(resources)} VISA resources:")
                for r in resources:
                    print(f"[DEBUG]   - {r}")
                print()
            
            for resource in resources:
                # Check TCPIP resources or USB resources containing 'RSA' or Rigol vendor ID
                if resource.startswith("TCPIP") or "RSA" in resource.upper() or "0x1AB1" in resource.upper():
                    if self.debug:
                        print(f"[DEBUG] Trying resource: {resource}")
                    try:
                        inst = self.rm.open_resource(resource)
                        inst.read_termination = '\n'
                        inst.write_termination = '\n'
                        inst.timeout = 20000
                        if self.debug:
                            print(f"[DEBUG]   - Opened connection, querying *IDN?...")
                        idn = inst.query("*IDN?").strip()
                        if self.debug:
                            print(f"[DEBUG]   - Response: {idn}")
                        if "RSA" in idn.upper() or "RIGOL" in idn.upper():
                            self.instrument = inst
                            self.address = resource
                            self._idn = idn
                            self.status = "Connected"
                            if self.debug:
                                print(f"[DEBUG]   - ✓ Match! Connected to RSA3030")
                            print(_SUCCESS_STYLE + f"Connected to RSA3030 at {self.address} [{self._idn}]")
                            # Save successful address to cache
                            self._save_last_address(resource)
                            return
                        else:
                            if self.debug:
                                print(f"[DEBUG]   - Not an RSA3030, closing connection")
                        inst.close()
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG]   - Error: {e}")
                        continue
                else:
                    if self.debug:
                        print(f"[DEBUG] Skipping resource (doesn't match filter): {resource}")

        # 4) If still not found, try probing link-local addresses (169.254.x.x)
        # This helps with devices that don't appear in VISA resource list
        if self.instrument is None:
            if self.debug:
                print(f"\n[DEBUG] No TCPIP resources found. Attempting link-local discovery...")
            
            link_local_ips = self._probe_link_local_ips()
            for ip in link_local_ips:
                if self.debug:
                    print(f"[DEBUG] Probing {ip}...")
                try:
                    tcpip_address = f"TCPIP0::{ip}::INSTR"
                    inst = self.rm.open_resource(tcpip_address)
                    inst.read_termination = '\n'
                    inst.write_termination = '\n'
                    inst.timeout = 5000  # Shorter timeout for scanning
                    idn = inst.query("*IDN?").strip()
                    if "RSA" in idn.upper() or "RIGOL" in idn.upper():
                        self.instrument = inst
                        self.address = tcpip_address
                        self._idn = idn
                        self.status = "Connected"
                        if self.debug:
                            print(f"[DEBUG]   - ✓ Found RSA3030 at {ip}!")
                        print(_SUCCESS_STYLE + f"Connected to RSA3030 at {self.address} [{self._idn}]")
                        # Save successful address to cache
                        self._save_last_address(tcpip_address)
                        return
                    else:
                        inst.close()
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG]   - No response: {e}")
                    continue
        
        if self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Rigol RSA3030 not found. Ensure device is connected and powered on.")

        # Clear status and cache ID
        try:
            self.instrument.write("*CLS")
        except Exception:
            pass

    def _probe_link_local_ips(self) -> List[str]:
        """
        Probe link-local IP addresses (169.254.x.x) to find RSA3030 devices.
        
        Returns a list of candidate IP addresses to try, prioritizing:
        1. Common link-local addresses used by Rigol devices
        2. Recently used addresses (if any network interface has 169.254.x.x)
        
        Returns:
            List of IP addresses to probe.
        """
        import socket
        
        candidates = []
        
        # Try to get local link-local addresses on the system
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                addr = info[4][0]
                if addr.startswith("169.254."):
                    # If we have a link-local address, probe nearby IPs
                    parts = addr.split('.')
                    base = f"{parts[0]}.{parts[1]}.{parts[2]}."
                    # Probe some addresses in the same /24 subnet
                    for i in [1, 99, 100, 101, 50, 20, 10, 2, 254]:
                        candidates.append(f"{base}{i}")
                    break
        except Exception:
            pass
        
        # Add common Rigol link-local addresses
        common_ips = [
            "169.254.20.99",   # Common Rigol default
            "169.254.10.1",
            "169.254.1.1",
            "169.254.100.100",
        ]
        
        # Add common IPs that aren't already in candidates
        for ip in common_ips:
            if ip not in candidates:
                candidates.append(ip)
        
        return candidates[:10]  # Limit to first 10 to avoid excessive scanning

    @staticmethod
    def _save_last_address(address: str) -> None:
        """
        Save the last successful connection address to cache file.
        
        Args:
            address: VISA resource string that successfully connected
        """
        try:
            # Create cache directory if it doesn't exist
            os.makedirs(_CACHE_DIR, exist_ok=True)
            
            # Save address to cache file
            with open(_CACHE_FILE, 'w') as f:
                json.dump({'address': address, 'timestamp': time.time()}, f)
        except Exception:
            # Silently fail if we can't write cache - not critical
            pass
    
    @staticmethod
    def _load_last_address() -> Optional[str]:
        """
        Load the last successful connection address from cache file.
        
        Returns:
            Last successful address if available and recent (< 7 days old), None otherwise
        """
        try:
            if os.path.exists(_CACHE_FILE):
                with open(_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # Only use cached address if it's less than 7 days old
                    if time.time() - data.get('timestamp', 0) < 7 * 24 * 3600:
                        return data.get('address')
        except Exception:
            # Silently fail if we can't read cache - not critical
            pass
        return None

    def disconnect(self):
        """Close the VISA session."""
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                print(f"\rDisconnected from RSA3030 at {self.address}")
        self.status = "Not Connected"
        self.instrument = None
        self.address = None

    # -----------------------------
    # Helpers / SCPI utilities
    # -----------------------------
    def _chk(self):
        """Verify instrument is connected."""
        if self.status != "Connected" or self.instrument is None:
            raise ConnectionError(_ERROR_STYLE + "Not connected to RSA3030.")

    # -----------------------------
    # Measurement functions
    # -----------------------------
    def get_identity(self) -> str:
        """
        Query instrument identification.

        Returns:
            str: Instrument identification string (manufacturer, model, serial, firmware).
        """
        self._chk()
        return self.instrument.query("*IDN?").strip()

    def capture_trace(self, trace_number: int = 1) -> tuple:
        """
        Capture trace data from the spectrum analyzer.
        
        Args:
            trace_number: Trace number to capture (1-4, default: 1)
        
        Returns:
            tuple: (frequencies, amplitudes) where:
                   - frequencies: List of frequency points in Hz
                   - amplitudes: List of amplitude values in dBm
        
        Example:
            >>> rsa = RSA3030(ip_address="192.168.1.100")
            >>> freqs, amps = rsa.capture_trace()
            >>> print(f"Captured {len(freqs)} points")
        """
        self._chk()
        
        if trace_number < 1 or trace_number > 4:
            raise ValueError("Trace number must be between 1 and 4")
        
        try:
            # Get frequency span configuration
            center_freq = float(self.instrument.query(":SENSe:FREQuency:CENTer?"))
            span = float(self.instrument.query(":SENSe:FREQuency:SPAN?"))
            
            # Get number of points
            points = int(self.instrument.query(":SENSe:SWEep:POINts?"))
            
            # Save original timeout and increase it for sweep + data transfer
            # Spectrum trace can contain 1000+ points and sweep can take time
            original_timeout = self.instrument.timeout
            self.instrument.timeout = 60000  # 60 seconds for sweep completion + data transfer
            
            # Initiate a single sweep and wait for it to complete
            # This ensures we capture fresh data
            self.instrument.write(":INITiate:IMMediate")
            
            # Wait for sweep to complete
            # Use *OPC? query to wait until operation is complete
            # This is more reliable than fixed sleep time
            import time
            self.instrument.query("*OPC?")  # Wait for operation complete
            time.sleep(1)  # Small additional delay for stability
            
            # Calculate frequency array
            start_freq = center_freq - span / 2
            stop_freq = center_freq + span / 2
            frequencies = [start_freq + (stop_freq - start_freq) * i / (points - 1) for i in range(points)]
            
            try:
                # Try different methods to get trace data
                # Method 1: Try TRACe:DATA? (most common)
                try:
                    trace_data_str = self.instrument.query(f":TRACe:DATA? TRACE{trace_number}")
                    if 'error' in trace_data_str.lower():
                        raise ValueError("Trace data query returned error")
                except Exception as e1:
                    # Method 2: Try without TRACE prefix
                    try:
                        trace_data_str = self.instrument.query(f":TRACe{trace_number}:DATA?")
                        if 'error' in trace_data_str.lower():
                            raise ValueError("Trace data query returned error")
                    except Exception as e2:
                        # Method 3: Try FETCh command (alternative for some spectrum analyzers)
                        try:
                            trace_data_str = self.instrument.query(f":FETCh:SPECtrum:TRACe{trace_number}?")
                            if 'error' in trace_data_str.lower():
                                raise ValueError("Trace data query returned error")
                        except Exception as e3:
                            # Method 4: Try simple TRACE:DATA format
                            try:
                                trace_data_str = self.instrument.query(":TRACE:DATA?")
                                if 'error' in trace_data_str.lower():
                                    raise ValueError("Could not retrieve trace data with any known SCPI command")
                            except Exception as e4:
                                raise ValueError(f"All trace data query methods failed. Errors: {e1}, {e2}, {e3}, {e4}")
            finally:
                # Restore original timeout
                self.instrument.timeout = original_timeout
            
            # Parse trace data (comma-separated values)
            amplitudes = [float(x) for x in trace_data_str.strip().split(',')]
            
            # Verify we got the expected number of points
            if len(amplitudes) != points:
                print(f"Warning: Expected {points} points but got {len(amplitudes)}")
                # Adjust frequency array to match actual data
                if len(amplitudes) > 0:
                    frequencies = [start_freq + (stop_freq - start_freq) * i / (len(amplitudes) - 1) 
                                 for i in range(len(amplitudes))]
            
            return frequencies, amplitudes
            
        except ValueError as e:
            # Re-raise ValueError with more context
            raise ValueError(f"Error capturing trace: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error capturing trace data: {e}")
    
    def capture_spectrogram(self, trace_number: int = 1, filename: Optional[str] = None) -> dict:
        """
        Capture a spectrogram (single sweep) from the spectrum analyzer.
        
        Args:
            trace_number: Trace number to capture (1-4, default: 1)
            filename: Optional filename to save the data (CSV format)
        
        Returns:
            dict: Dictionary containing:
                  - 'frequencies': List of frequency points in Hz
                  - 'amplitudes': List of amplitude values in dBm
                  - 'center_freq': Center frequency in Hz
                  - 'span': Frequency span in Hz
                  - 'rbw': Resolution bandwidth in Hz
                  - 'vbw': Video bandwidth in Hz
                  - 'points': Number of data points
        
        Example:
            >>> rsa = RSA3030(ip_address="192.168.1.100")
            >>> data = rsa.capture_spectrogram(filename="spectrum.csv")
            >>> print(f"Center: {data['center_freq']/1e9:.3f} GHz")
            >>> print(f"Span: {data['span']/1e6:.1f} MHz")
        """
        self._chk()
        
        # Get current configuration
        center_freq = float(self.instrument.query(":SENSe:FREQuency:CENTer?"))
        span = float(self.instrument.query(":SENSe:FREQuency:SPAN?"))
        rbw = float(self.instrument.query(":SENSe:BANDwidth:RESolution?"))
        vbw = float(self.instrument.query(":SENSe:BANDwidth:VIDeo?"))
        
        # Capture trace
        frequencies, amplitudes = self.capture_trace(trace_number)
        
        # Build result dictionary
        result = {
            'frequencies': frequencies,
            'amplitudes': amplitudes,
            'center_freq': center_freq,
            'span': span,
            'rbw': rbw,
            'vbw': vbw,
            'points': len(frequencies)
        }
        
        # Save to file if requested
        if filename:
            import csv
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Frequency (Hz)', 'Amplitude (dBm)'])
                writer.writerow([f'# Center Frequency: {center_freq} Hz'])
                writer.writerow([f'# Span: {span} Hz'])
                writer.writerow([f'# Resolution Bandwidth: {rbw} Hz'])
                writer.writerow([f'# Video Bandwidth: {vbw} Hz'])
                writer.writerow([])  # Blank line
                writer.writerow(['Frequency (Hz)', 'Amplitude (dBm)'])
                for freq, amp in zip(frequencies, amplitudes):
                    writer.writerow([freq, amp])
            print(f"Spectrogram saved to {filename}")
        
        return result
    
    def configure_spectrum(self, center_freq: Optional[float] = None, 
                          span: Optional[float] = None,
                          rbw: Optional[float] = None,
                          vbw: Optional[float] = None) -> None:
        """
        Configure spectrum analyzer parameters.
        
        Args:
            center_freq: Center frequency in Hz (e.g., 1e9 for 1 GHz)
            span: Frequency span in Hz (e.g., 100e6 for 100 MHz)
            rbw: Resolution bandwidth in Hz (e.g., 10e3 for 10 kHz)
            vbw: Video bandwidth in Hz (e.g., 10e3 for 10 kHz)
        
        Example:
            >>> rsa = RSA3030(ip_address="192.168.1.100")
            >>> rsa.configure_spectrum(center_freq=1e9, span=100e6)
            >>> rsa.configure_spectrum(rbw=10e3, vbw=10e3)
        """
        self._chk()
        
        if center_freq is not None:
            self.instrument.write(f":SENSe:FREQuency:CENTer {center_freq}")
            print(f"Set center frequency to {center_freq/1e9:.3f} GHz")
        
        if span is not None:
            self.instrument.write(f":SENSe:FREQuency:SPAN {span}")
            print(f"Set span to {span/1e6:.1f} MHz")
        
        if rbw is not None:
            self.instrument.write(f":SENSe:BANDwidth:RESolution {rbw}")
            print(f"Set RBW to {rbw/1e3:.1f} kHz")
        
        if vbw is not None:
            self.instrument.write(f":SENSe:BANDwidth:VIDeo {vbw}")
            print(f"Set VBW to {vbw/1e3:.1f} kHz")

    def get(self, item: str):
        """
        Generic measurement getter for data_logger integration.

        Args:
            item: Measurement type to retrieve. Supported values:
                  - "identity": Instrument identification string

        Returns:
            Measurement value appropriate for the requested item.

        Raises:
            ValueError: If invalid item is requested.
        """
        k = item.strip().lower()
        if k == "identity":
            return self.get_identity()
        else:
            raise ValueError(_ERROR_STYLE + f"Invalid item: {item} request to RSA3030")
