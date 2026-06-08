#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture and summarize an analog channel on the Saleae Logic 8.

Captures 1 second of data from analog channel 6 (by default), prints a
framed colored summary of the statistics, and optionally plots the
waveform when ``--display-plot`` is passed.

Requires the Logic 2 desktop app to be running with the Automation
Server enabled.

Usage:
    python scripts/logic8_capture.py
    python scripts/logic8_capture.py --display-plot
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
import tempfile

import numpy as np
from colorama import Fore, Style, init as colorama_init

from lab_drivers.drivers.saleae.Logic8 import Logic8

CHANNEL = 6
# Valid analog rates reported by Logic Pro 8 for a single analog channel
# include 1_562_500, 781_250, etc. Adjust if the device rejects this rate.
SAMPLE_RATE_HZ = 1_562_500
DURATION_S = 1.0


# ---------------------------------------------------------------------------
# Binary parser
# ---------------------------------------------------------------------------
def parse_saleae_analog_binary(path: str):
    """Parse a Saleae raw-binary analog export.

    Returns (begin_time_s, sample_rate_hz, downsample, samples_volts).
    """
    with open(path, "rb") as f:
        ident = f.read(8)
        if ident != b"<SALEAE>":
            raise ValueError(f"Not a Saleae binary file: {path!r} (got {ident!r})")
        version, dtype = struct.unpack("<ii", f.read(8))
        if version != 0 or dtype != 1:
            raise ValueError(f"Unsupported analog version/type: v={version} t={dtype}")
        (begin_time,) = struct.unpack("<d", f.read(8))
        sample_rate, downsample, num_samples = struct.unpack("<QQQ", f.read(24))
        samples = np.frombuffer(f.read(num_samples * 4), dtype="<f4")
    return float(begin_time), int(sample_rate), int(downsample), samples


# ---------------------------------------------------------------------------
# Pretty-printed framed summary
# ---------------------------------------------------------------------------
def _visible_len(s: str) -> int:
    """Length of a string ignoring ANSI escape sequences."""
    out, i = 0, 0
    while i < len(s):
        if s[i] == "\x1b":
            j = s.find("m", i)
            if j == -1:
                break
            i = j + 1
        else:
            out += 1
            i += 1
    return out


def print_framed_summary(title: str, rows: list[tuple[str, str]]) -> None:
    """Print a Unicode-bordered, colorized key/value table."""
    label_w = max(len(k) for k, _ in rows)
    value_w = max(_visible_len(v) for _, v in rows)
    inner_w = max(label_w + 2 + value_w, len(title))

    top = f"{Fore.CYAN}{Style.BRIGHT}╔{'═' * (inner_w + 2)}╗{Style.RESET_ALL}"
    mid = f"{Fore.CYAN}{Style.BRIGHT}╠{'═' * (inner_w + 2)}╣{Style.RESET_ALL}"
    bot = f"{Fore.CYAN}{Style.BRIGHT}╚{'═' * (inner_w + 2)}╝{Style.RESET_ALL}"
    bar = f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}"

    title_pad = inner_w - len(title)
    print(top)
    print(f"{bar} {Fore.YELLOW}{Style.BRIGHT}{title}{Style.RESET_ALL}{' ' * title_pad} {bar}")
    print(mid)
    for label, value in rows:
        lpad = label_w - len(label)
        vpad = value_w - _visible_len(value)
        print(
            f"{bar} {Fore.WHITE}{Style.BRIGHT}{label}{Style.RESET_ALL}{' ' * lpad}"
            f"  {value}{' ' * vpad} {bar}"
        )
    print(bot)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--display-plot",
        action="store_true",
        help="Show a matplotlib plot of the captured waveform.",
    )
    parser.add_argument("--channel", type=int, default=CHANNEL, help="Analog channel index (default: %(default)s).")
    parser.add_argument("--rate", type=int, default=SAMPLE_RATE_HZ, help="Sample rate in Hz (default: %(default)s).")
    parser.add_argument("--duration", type=float, default=DURATION_S, help="Capture duration in seconds (default: %(default)s).")
    args = parser.parse_args()

    colorama_init(autoreset=False)

    out_dir = os.path.join(tempfile.gettempdir(), "logic8_capture")
    os.makedirs(out_dir, exist_ok=True)

    with Logic8() as logic:
        print(
            f"{Fore.CYAN}Starting {args.duration:g} s capture of A{args.channel} "
            f"@ {args.rate/1e6:g} MS/s ...{Style.RESET_ALL}"
        )
        logic.start_capture(
            analog_channels=[args.channel],
            analog_sample_rate_hz=args.rate,
            duration_s=args.duration,
        )
        logic.wait_capture()
        logic.export_raw(out_dir, analog_channels=[args.channel])
        logic.close_capture()

    bin_path = os.path.join(out_dir, f"analog_{args.channel}.bin")
    if not os.path.exists(bin_path):
        print(f"{Fore.RED}Expected file not found: {bin_path}{Style.RESET_ALL}", file=sys.stderr)
        return 1

    begin_time, sample_rate, downsample, samples = parse_saleae_analog_binary(bin_path)
    effective_rate = sample_rate / max(downsample, 1)
    n = samples.size

    mean_v = float(np.mean(samples))
    std_v = float(np.std(samples, ddof=1)) if n > 1 else 0.0
    min_v = float(np.min(samples))
    max_v = float(np.max(samples))
    pp_v = max_v - min_v
    rms_v = float(np.sqrt(np.mean(np.square(samples))))
    actual_duration = n / effective_rate

    rows = [
        ("Channel",         f"{Fore.GREEN}A{args.channel}{Style.RESET_ALL}"),
        ("Requested rate",  f"{args.rate:>15,d} Hz"),
        ("Effective rate",  f"{effective_rate:>15,.0f} Hz"),
        ("Duration",        f"{actual_duration:>15.6f} s"),
        ("Sample count",    f"{n:>15,d}"),
        ("Mean",            f"{Fore.GREEN}{mean_v:>+15.6f} V{Style.RESET_ALL}"),
        ("Std deviation",   f"{Fore.YELLOW}{std_v:>15.6f} V{Style.RESET_ALL}"),
        ("Min",             f"{min_v:>+15.6f} V"),
        ("Max",             f"{max_v:>+15.6f} V"),
        ("Peak-to-peak",    f"{pp_v:>15.6f} V"),
        ("RMS",             f"{rms_v:>15.6f} V"),
        ("Export file",     bin_path),
    ]
    print_framed_summary(f"Saleae Logic 8 - A{args.channel} capture summary", rows)

    if args.display_plot:
        import matplotlib.pyplot as plt

        t = begin_time + np.arange(n) / effective_rate
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(t, samples, linewidth=0.8)
        ax.axhline(mean_v, color="tab:red", linestyle="--", linewidth=1.0,
                   label=f"mean = {mean_v:.4f} V")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(f"A{args.channel} [V]")
        ax.set_title(f"Saleae Logic 8 - A{args.channel} capture")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")
        ax.relim()
        ax.autoscale(axis="y")

        info = (
            f"channel: A{args.channel}\n"
            f"requested rate: {args.rate:,} Hz\n"
            f"effective rate: {effective_rate:,.0f} Hz\n"
            f"duration: {actual_duration:.4f} s ({n:,} samples)\n"
            f"mean: {mean_v:+.6f} V\n"
            f"std: {std_v:.6f} V\n"
            f"min/max: {min_v:+.4f} / {max_v:+.4f} V\n"
            f"RMS: {rms_v:.6f} V"
        )
        ax.text(
            0.01, 0.99, info,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="0.7", alpha=0.9),
        )
        fig.tight_layout()
        plt.show()

    return 0


if __name__ == "__main__":
    sys.exit(main())
