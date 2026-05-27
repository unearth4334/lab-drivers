"""Capture a screenshot from a Rigol DS1054Z oscilloscope.

The DS1000Z series supports the SCPI command ``:DISPlay:DATA?`` which
returns the current screen as a BMP image (IEEE 488.2 definite-length
binary block, ~1,152,054 bytes for the full 800x480 24-bit BMP).

Usage:
    python scripts/ds1054z_screenshot.py [output_path]

If no path is given, a timestamped file ``DS1054Z_<YYYYmmdd_HHMMSS>.bmp``
is written to the current directory.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pyvisa


SCOPE_IDN_KEYWORDS = ("DS1054Z", "DS1Z", "DS1000Z")


def find_ds1054z(rm: pyvisa.ResourceManager) -> str:
    """Return the VISA resource string of the first DS1054Z found.

    Falls back to *IDN? probing for any USB/TCPIP resource that does not
    advertise a model in its resource string.
    """
    resources = rm.list_resources()
    if not resources:
        raise RuntimeError("No VISA resources found. Is the scope powered on and connected?")

    # First pass: cheap match by resource string
    for res in resources:
        if any(k in res.upper() for k in SCOPE_IDN_KEYWORDS):
            return res

    # Second pass: query *IDN? on each candidate
    for res in resources:
        if not (res.startswith("USB") or res.startswith("TCPIP")):
            continue
        try:
            inst = rm.open_resource(res)
            inst.timeout = 2000
            idn = inst.query("*IDN?").strip()
            inst.close()
            if any(k in idn.upper() for k in SCOPE_IDN_KEYWORDS):
                return res
        except pyvisa.VisaIOError:
            continue

    raise RuntimeError(
        f"DS1054Z not found. Available resources: {resources}"
    )


def capture_screenshot(output: Path) -> Path:
    rm = pyvisa.ResourceManager()
    try:
        address = find_ds1054z(rm)
        print(f"Found scope at: {address}")

        scope = rm.open_resource(address)
        try:
            scope.timeout = 20_000  # screenshot transfer can be slow
            scope.chunk_size = 1024 * 1024
            idn = scope.query("*IDN?").strip()
            print(f"*IDN? -> {idn}")

            # :DISP:DATA? returns BMP by default on DS1000Z series.
            data = scope.query_binary_values(
                ":DISP:DATA?", datatype="B", container=bytes
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            print(f"Saved screenshot ({len(data)} bytes) to {output}")
            return output
        finally:
            scope.close()
    finally:
        rm.close()


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        out = Path(argv[1])
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = Path.cwd() / f"DS1054Z_{stamp}.bmp"

    try:
        capture_screenshot(out)
    except Exception as exc:  # noqa: BLE001 - top-level CLI handler
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
