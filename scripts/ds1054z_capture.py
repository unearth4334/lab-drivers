"""CLI wrapper around ``RigolDS1054Z`` for screenshots and waveform CSVs.

Usage:
    python ds1054z_capture.py                       # screenshot only
    python ds1054z_capture.py shot.bmp              # screenshot to path
    python ds1054z_capture.py --waveform            # screenshot + waveform CSV
    python ds1054z_capture.py --waveform --raw      # full memory waveform
    python ds1054z_capture.py --no-screenshot --waveform   # waveform only
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from lab_drivers.drivers.visa.RigolDS1054Z import RigolDS1054Z


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DS1054Z screenshot/waveform capture")
    p.add_argument("output", nargs="?", default=None,
                   help="Output path for screenshot BMP (default: timestamped in cwd)")
    p.add_argument("--no-screenshot", action="store_true",
                   help="Skip screenshot capture")
    p.add_argument("--waveform", action="store_true",
                   help="Also download waveform from enabled channels to CSV")
    p.add_argument("--raw", action="store_true",
                   help="With --waveform, capture full memory depth (stops scope)")
    p.add_argument("--waveform-out", default=None,
                   help="Output path for waveform CSV (default: alongside screenshot)")
    p.add_argument("--address", default=None,
                   help="Explicit VISA resource string")
    p.add_argument("--ip", default=None, help="Scope IP address (LAN connection)")
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bmp_path = Path(args.output) if args.output else Path.cwd() / f"DS1054Z_{stamp}.bmp"
    csv_path = Path(args.waveform_out) if args.waveform_out else bmp_path.with_suffix(".csv")

    if args.raw and not args.waveform:
        print("WARN: --raw has no effect without --waveform", file=sys.stderr)

    try:
        with RigolDS1054Z(address=args.address, ip_address=args.ip) as scope:
            if not args.no_screenshot:
                scope.save_screenshot(str(bmp_path))
            if args.waveform:
                scope.save_waveform(str(csv_path), raw=args.raw)
    except Exception as exc:  # noqa: BLE001 - top-level CLI handler
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
