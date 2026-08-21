#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rapid resistance capture helper for the B&K Precision 2831E / 5491B.

Steps through a sequence of resistance measurements. Before each reading the
script runs a *gap* countdown (reposition the probes) followed by a *dwell*
countdown (let the reading stabilize), then records the value. Each countdown is
drawn as a braille progress bar that depletes as time runs out and flashes
inverted/non-inverted during the final three seconds.

Measurements are appended to a CSV named ``YYYYMMDD-HHMMSS_<note>.csv``.

Usage:
    python scripts/resistance_capture.py --scale 20k -n 10 --dwell 2 --gap 3 --note coupon_a
    python scripts/resistance_capture.py --scale auto -n 5 --dwell 1.5 --gap 2 --note vias --com COM7
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from colorama import init as colorama_init

from lab_drivers.drivers.serial.BK2831E import BK2831E


# ---------------------------------------------------------------------------
# Scale parsing
# ---------------------------------------------------------------------------
# Named resistance scales for the 2831E (the 5491B uses the 5xx series, but the
# meter selects a range by expected value so these tokens still work there).
_SCALE_MULTIPLIERS = {"": 1.0, "r": 1.0, "ohm": 1.0, "ohms": 1.0,
                      "k": 1e3, "m": 1e6, "meg": 1e6}


def parse_scale(text: str) -> float | None:
    """Parse a scale token into an expected-ohms value, or None for auto-range.

    Accepts ``auto`` or values like ``200``, ``2k``, ``20k``, ``200k``, ``2M``,
    ``20M`` (case-insensitive; ``M`` means mega-ohms).
    """
    s = text.strip().lower()
    if s in ("auto", "a"):
        return None
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*([a-zΩ]*)", s)
    if match is None:
        raise argparse.ArgumentTypeError(f"Invalid scale: {text!r}")
    value = float(match.group(1))
    unit = match.group(2).replace("Ω", "").replace("ω", "")
    if unit not in _SCALE_MULTIPLIERS:
        raise argparse.ArgumentTypeError(f"Unknown scale unit in {text!r}")
    return value * _SCALE_MULTIPLIERS[unit]


# ---------------------------------------------------------------------------
# Braille timer bar
# ---------------------------------------------------------------------------
_BRAILLE_BLANK = "\u2800"       # empty cell
_BRAILLE_LEFT = "\u2847"        # left column filled (dots 1,2,3,7)
_BRAILLE_FULL = "\u28ff"        # both columns filled


def braille_bar(fraction: float, width: int = 24) -> str:
    """Render a braille progress bar for ``fraction`` in [0, 1].

    Each cell holds two sub-steps (its two dot columns), giving ``2 * width``
    steps of horizontal resolution.
    """
    fraction = max(0.0, min(1.0, fraction))
    filled_sub = round(fraction * width * 2)
    cells = []
    for c in range(width):
        cell_sub = filled_sub - c * 2
        if cell_sub >= 2:
            cells.append(_BRAILLE_FULL)
        elif cell_sub == 1:
            cells.append(_BRAILLE_LEFT)
        else:
            cells.append(_BRAILLE_BLANK)
    return "".join(cells)


def countdown(seconds: float, label: str, width: int = 24, fps: int = 15) -> None:
    """Show a depleting braille countdown bar for ``seconds``.

    The bar flashes inverted/non-inverted (reverse video) twice per second
    during the final three seconds.
    """
    if seconds <= 0:
        return

    start = time.monotonic()
    end = start + seconds
    try:
        while True:
            now = time.monotonic()
            remaining = max(0.0, end - now)
            bar = braille_bar(remaining / seconds, width)
            flash = remaining <= 3.0 and int(now * 2) % 2 == 0
            line = f"  {label:<12} \u2595{bar}\u258f {remaining:4.1f}s"
            if flash:
                line = f"\x1b[7m{line}\x1b[0m"
            sys.stdout.write("\r" + line + "\x1b[K")
            sys.stdout.flush()
            if remaining <= 0:
                break
            time.sleep(min(1.0 / fps, remaining))
    finally:
        sys.stdout.write("\r\x1b[K")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BK2831E rapid resistance capture")
    p.add_argument("--scale", type=parse_scale, default=None,
                   help="Resistance scale: auto, 200, 2k, 20k, 200k, 2M, 20M "
                        "(default: auto-range)")
    p.add_argument("-n", "--count", type=int, required=True,
                   help="Number of measurements to take")
    p.add_argument("--dwell", type=float, default=2.0,
                   help="Dwell time per measurement in seconds, to let the "
                        "reading stabilize (default: 2.0)")
    p.add_argument("--gap", type=float, default=3.0,
                   help="Gap time between measurements in seconds, to reposition "
                        "the probes (default: 3.0)")
    p.add_argument("--note", default="",
                   help="Note appended to the CSV filename")
    p.add_argument("--outdir", default=None,
                   help="Output directory for the CSV (default: current directory)")
    p.add_argument("--com", "--port", dest="com", default=None,
                   help="Serial COM port (e.g., COM7, /dev/ttyUSB0)")
    p.add_argument("--baud", type=int, default=9600,
                   help="Serial baud rate (default: 9600)")
    return p.parse_args(argv[1:])


def _safe_note(note: str) -> str:
    """Sanitize a note for use in a filename."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", note.strip())
    return cleaned.strip("_")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    colorama_init()

    if args.count <= 0:
        print("ERROR: --count must be a positive integer", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    note = _safe_note(args.note)
    filename = f"{stamp}_{note}.csv" if note else f"{stamp}.csv"
    outdir = Path(args.outdir) if args.outdir else Path.cwd()
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / filename

    scale_label = "auto" if args.scale is None else f"{args.scale:g}"
    print(f"Capturing {args.count} resistance measurement(s)")
    print(f"  scale={scale_label}  dwell={args.dwell:g}s  gap={args.gap:g}s")
    print(f"  output: {csv_path}")

    rows: list[tuple[int, str, float]] = []
    try:
        with BK2831E(com_port=args.com, baud_rate=args.baud) as dmm:
            dmm.set_function("RESISTANCE")
            if args.scale is None:
                dmm.set_resistance_autorange(True)
            else:
                dmm.set_resistance_range(args.scale)

            for i in range(1, args.count + 1):
                print(f"\nMeasurement {i}/{args.count}")
                countdown(args.gap, "Reposition")
                countdown(args.dwell, "Stabilize")

                resistance = dmm.measure_resistance()
                timestamp = datetime.now().isoformat(timespec="milliseconds")
                rows.append((i, timestamp, resistance))

                display = "OVERLOAD" if resistance == float("inf") else f"{resistance:.4g} \u03a9"
                print(f"  #{i}: {display}")
    except KeyboardInterrupt:
        print("\nInterrupted; writing partial results.", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - top-level CLI handler
        print(f"\nERROR: {exc}", file=sys.stderr)
        if not rows:
            return 1

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "timestamp", "resistance_ohms", "scale", "note"])
        for index, timestamp, resistance in rows:
            value = "inf" if resistance == float("inf") else f"{resistance:.6g}"
            writer.writerow([index, timestamp, value, scale_label, args.note])

    finite = [r for _, _, r in rows if r != float("inf")]
    print(f"\nWrote {len(rows)} row(s) to {csv_path}")
    if finite:
        mean = sum(finite) / len(finite)
        print(f"  mean of {len(finite)} finite reading(s): {mean:.6g} \u03a9")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
