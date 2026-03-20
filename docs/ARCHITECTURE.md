# Architecture

## Principles

- Hardware communication code lives in driver modules only.
- Keep orchestration, workflow, UI, and progress display outside this package.
- Preserve established driver method conventions while improving consistency incrementally.

## Current structure

- `lab_drivers.drivers.visa`: VISA instruments.
- `lab_drivers.drivers.serial`: serial instruments.
- `lab_drivers.core`: shared utilities that are not tied to one instrument family.

## Extension pattern

Future drivers should be added under transport folders and expose a class with familiar methods:
- `connect(...)`
- `disconnect()`
- `get(item, *args, **kwargs)`
- `measure_*()` as applicable
