# Lab Drivers Reference

This site is a concise API reference for bench drivers.

## Fast path

1. Install dependencies from [Install Instructions](install-instructions.md).
2. Open [API Reference](api/index.md).
3. Pick a driver and use the generated class/method docs.

## How to read driver docs

- Driver pages are generated from in-code docstrings via mkdocstrings.
- Public methods are the supported command surface.
- Constructor parameters and examples are source-of-truth in the driver module.

## Minimal usage pattern

```python
from lab_drivers.drivers.visa import DMM6500

device = DMM6500()
value = device.get("voltage")
print(value)
device.disconnect()
```
