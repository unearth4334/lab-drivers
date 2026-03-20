#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigol DP711 Programmable DC Power Supply Driver
================================================

Driver for Rigol DP711 power supply with serial (RS-232) connectivity.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import serial
import serial.tools.list_ports
from colorama import init, Fore, Style


# Console output styles
_ERROR_STYLE = Fore.RED + Style.BRIGHT + "\rError! "
_SUCCESS_STYLE = Fore.GREEN + Style.BRIGHT + "\r"
_WARNING_STYLE = Fore.YELLOW + Style.BRIGHT + "\rWarning! "

_DELAY = 0.2   # inter-command delay (s)
_IDN_DELAY = 0.5  # longer wait after *IDN? on first connect

class RigolDP711:
    """
    Driver for Rigol DP711 Programmable DC Power Supply.
    
    This class provides methods for connecting to and controlling a
    DP711 power supply via RS-232 serial interface (USB-to-RS232 adapter).
    
    Features
    --------
    - Auto-detection of USB-to-serial ports
    - Voltage and current measurement/control
    - Output enable/disable
    - Simple command-based interface
    
    Basic Usage
    -----------
    ```python
    from lab_drivers.drivers.serial.RigolDP711 import RigolDP711
    
    # Auto-connect to first available DP711
    psu = RigolDP711()
    
    # Set voltage and enable output
    psu.set_voltage(12.0)
    psu.set_current(2.5)
    psu.turn_on()
    
    # Measure
    v = psu.measure_voltage()
    i = psu.measure_current()
    print(f"Voltage: {v:.3f}V, Current: {i:.3f}A")
    
    # Clean up
    psu.turn_off()
    psu.disconnect()
    ```
    """
    
    def __init__(self, auto_connect: bool = True, com_port: Optional[str] = None, baud_rate: int = 9600):
        """
        Initialize RigolDP711 driver.
        
        Args:
            auto_connect: Automatically connect to device on initialization
            com_port: Optional explicit COM port (e.g., 'COM4', '/dev/ttyUSB0')
            baud_rate: Serial baud rate (default: 9600)
        """
        init(autoreset=True)
        
        self.ser: Optional[serial.Serial] = None
        self.address: Optional[str] = None
        self.status: str = "Not Connected"
        self.identity: Optional[str] = None
        self._com_port_hint: Optional[str] = com_port
        self._baud_rate: int = baud_rate

        if auto_connect:
            self.connect(com_port=com_port, baud_rate=baud_rate)
    
    def connect(self, com_port: Optional[str] = None, baud_rate: int = 9600) -> None:
        """Establish connection to RigolDP711 power supply."""
        # Try explicit COM port first
        explicit_port = com_port or self._com_port_hint
        
        # Try environment variable
        if explicit_port is None:
            try:
                explicit_port = os.environ.get('DP711_COM_PORT')
            except Exception:
                pass
        
        # Prompt user to select COM port
        if explicit_port is None:
            ports = serial.tools.list_ports.comports()
            if not ports:
                raise ConnectionError(_ERROR_STYLE + "No COM ports found")
            
            print("\nAvailable COM ports:")
            for i, port in enumerate(ports, start=1):
                print(f"  {i}. {port.device} - {port.description}")
            
            while True:
                try:
                    selection = int(input("Select COM port for Rigol DP711 (1, 2, ...): "))
                    if 1 <= selection <= len(ports):
                        explicit_port = ports[selection - 1].device
                        os.environ['DP711_COM_PORT'] = explicit_port
                        break
                    print(_ERROR_STYLE + "Invalid selection")
                except ValueError:
                    print(_ERROR_STYLE + "Invalid input. Enter a number.")
        
        # Open serial connection
        try:
            self.ser = serial.Serial(
                explicit_port,
                baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                timeout=2,
            )
            self.address = explicit_port

            # Assert DTR + RTS
            self.ser.dtr = True
            self.ser.rts = True
            time.sleep(0.05)

            # Flush buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            time.sleep(0.1)

            # Try \r\n first (Rigol standard), fall back to \n
            self.identity = None
            for terminator in (b'\r\n', b'\n'):
                self.ser.reset_input_buffer()
                self.ser.write(b'*IDN?' + terminator)
                self.ser.flush()
                time.sleep(_IDN_DELAY)

                n = self.ser.in_waiting
                raw = self.ser.read(n) if n > 0 else b''
                candidate = raw.decode('ascii', errors='ignore').strip()
                if len(candidate) >= 5:
                    self.identity = candidate
                    break

            if not self.identity:
                raise ConnectionError(_ERROR_STYLE + "Device not responding with valid identity")

            self.status = "Connected"
            print(_SUCCESS_STYLE + f"Connected to {self.identity}")

        except serial.SerialException as e:
            raise ConnectionError(_ERROR_STYLE + f"Failed to connect to {explicit_port}: {e}")
        except Exception as e:
            raise ConnectionError(_ERROR_STYLE + f"Unexpected error connecting to {explicit_port}: {e}")

    def disconnect(self) -> None:
        """Close the serial connection to the device."""
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            finally:
                print(f"\rDisconnected from Rigol DP711 at {self.address}")
                self.ser = None
        
        self.status = "Not Connected"
        self.address = None
    
    def _chk(self) -> None:
        """Verify device is connected before operations."""
        if self.status != "Connected" or self.ser is None or not self.ser.is_open:
            raise ConnectionError(_ERROR_STYLE + "Not connected to Rigol DP711")
    
    def _write(self, command: str) -> None:
        """Write a command to the device."""
        self._chk()
        self.ser.write(f"{command}\r\n".encode('ascii'))
        self.ser.flush()
        time.sleep(_DELAY)
    
    def _query(self, command: str) -> str:
        """Query the device and return the response."""
        self._chk()
        self.ser.reset_input_buffer()
        self.ser.write(f"{command}\r\n".encode('ascii'))
        self.ser.flush()
        time.sleep(_DELAY)
        n = self.ser.in_waiting
        raw = self.ser.read(n) if n > 0 else b''
        return raw.decode('ascii', errors='ignore').strip()
    
    def get(self, item: str, channel: int = 1) -> float:
        """Retrieve measurement value by name."""
        self._chk()

        item_upper = item.strip().upper()
        
        items = {
            "CURR": self.measure_current,
            "CURRENT": self.measure_current,
            "VOLT": self.measure_voltage,
            "VOLTAGE": self.measure_voltage
        }
        
        if item_upper not in items:
            raise ValueError(
                _ERROR_STYLE + f"Invalid item '{item}'. "
                f"Valid items: {', '.join(items.keys())}"
            )

        return items[item_upper]()

    def set_voltage(self, voltage: float) -> None:
        """Set the output voltage."""
        self._chk()
        
        if not 0 <= voltage <= 30:
            raise ValueError(_ERROR_STYLE + f"Voltage {voltage}V out of range (0-30V)")
        
        command = f':VOLT {voltage:.3f}'
        self._write(command)

    def set_current(self, current: float) -> None:
        """Set the output current limit."""
        self._chk()
        
        if not 0 <= current <= 5:
            raise ValueError(_ERROR_STYLE + f"Current {current}A out of range (0-5A)")
        
        command = f':CURR {current:.3f}'
        self._write(command)

    def measure_voltage(self) -> float:
        """Measure the actual output voltage."""
        try:
            response = self._query(':MEAS:VOLT?')
            return float(response)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse voltage measurement: {e}")

    def measure_current(self) -> float:
        """Measure the actual output current."""
        try:
            response = self._query(':MEAS:CURR?')
            return float(response)
        except ValueError as e:
            raise ValueError(_ERROR_STYLE + f"Failed to parse current measurement: {e}")

    def set_output_state(self, state: bool) -> None:
        """Enable or disable the power supply output."""
        self._chk()
        
        if state:
            command = ':OUTP ON'
            print(_SUCCESS_STYLE + "Rigol DP711 output: ON")
        else:
            command = ':OUTP OFF'
            print(_SUCCESS_STYLE + "Rigol DP711 output: OFF")
        
        self._write(command)

    def turn_on(self) -> None:
        """Turn on the power supply output."""
        self.set_output_state(True)

    def turn_off(self) -> None:
        """Turn off the power supply output."""
        self.set_output_state(False)
