# lab-drivers

`lab-drivers` is a focused Python package for laboratory equipment drivers.

## Scope

This repository contains hardware communication drivers only:
- VISA instruments (DMMs, oscilloscopes, supplies, loads, RF analyzers)
- Serial instruments (multimeters, power supplies)

This repository intentionally excludes orchestration/UI concerns (for example progress spinners and data logging workflow code).

## Install

```bash
pip install "lab-drivers[all] @ git+https://github.com/unearth4334/lab-drivers.git@v0.2.3"
```

See [Install Instructions](https://unearth4334.github.io/lab-drivers/install-instructions/) for full details including `pyproject.toml` and `requirements.txt` usage.

## Package layout

- `lab_drivers.drivers.visa` - VISA-backed instrument drivers
- `lab_drivers.drivers.serial` - serial-backed instrument drivers
- `lab_drivers.core` - shared core primitives (small and transport-agnostic)

## Design notes

- Keep driver APIs stable where practical (`connect`, `disconnect`, `get`, `measure_*`).
- Keep transport-specific dependencies optional via extras.
- Keep non-driver UI/helpers out of this repo.
