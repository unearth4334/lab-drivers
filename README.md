# lab-drivers

`lab-drivers` is a focused Python package for laboratory equipment drivers.

## Scope

This repository contains hardware communication drivers only:
- VISA instruments (DMMs, oscilloscopes, supplies, loads, RF analyzers)
- Serial instruments (multimeters, power supplies)

This repository intentionally excludes orchestration/UI concerns (for example progress spinners and data logging workflow code).

The one exception is `nodes/lab_drivers_nodes`, an optional layer that adapts
these drivers for the DM-TP Automation WebUI. It is a separate package, imported
only by that server; nothing under `src/lab_drivers` depends on it.

## Install

```bash
pip install -e .
```

Recommended extras:

```bash
pip install -e ".[visa,serial]"
```

## Package layout

- `lab_drivers.drivers.visa` - VISA-backed instrument drivers
- `lab_drivers.drivers.serial` - serial-backed instrument drivers
- `lab_drivers.core` - shared core primitives (small and transport-agnostic)
- `nodes/lab_drivers_nodes` - optional DM-TP automation nodes (see below)

Driver classes are importable straight from their transport package:

```python
from lab_drivers.drivers.visa import DMM6500
from lab_drivers.drivers.serial import KA3010P
```

Imports are lazy, so `pyvisa` is only needed once you touch a VISA driver.

## Logging

Drivers report through the standard `logging` module and are **silent by
default**, as a library should be. Scripts that want the console output enable
it once:

```python
import lab_drivers

lab_drivers.enable_console_logging()
```

Everything sits under the `lab_drivers` logger, so an application can capture it
with a single handler, or narrow it to one instrument by module name.

## Unattended use

Drivers never stop to ask a question unless a terminal is attached. Where a
serial port is not supplied, resolution order is:

1. the `address=` argument;
2. the driver's environment variable (e.g. `KA3010P_COM_PORT`);
3. an interactive menu -- **only** when stdin is a terminal.

Otherwise the driver raises `ConnectionError` naming the ports it found. Pass
`interactive=False` to force that behaviour, or `interactive=True` to insist on
prompting.

## DM-TP automation nodes

Install this repository from the DM-TP Automation WebUI under
**Settings -> Custom Nodes**:

```
https://github.com/unearth4334/lab-drivers.git
```

`dmtp_nodes.toml` at the repository root tells the installer what to put on
`sys.path` and which modules to import. The nodes themselves live in
`nodes/lab_drivers_nodes`.

## Design notes

- Keep driver APIs stable where practical (`connect`, `disconnect`, `get`, `measure_*`).
- `connect(address=...)` is the shared spelling across every transport.
- Keep transport-specific dependencies optional via extras.
- Report through `logging`; never `print` from a driver.
- Never block on input in a code path an unattended caller can reach.
- Keep non-driver UI/helpers out of this repo.

## Tests

```bash
pip install pytest
pytest tests
```

The node-layer tests skip unless DM-TP's `automation_nodes` package is on the
path.
