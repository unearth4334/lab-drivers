# Installation

## Requirements

- Python 3.9+
- Optional: VISA runtime for VISA-connected instruments

## Install package

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

## Optional extras

```bash
pip install -e ".[serial]"
pip install -e ".[visa]"
```

## Verify

```python
from lab_drivers.drivers.visa import DMM6500

device = DMM6500(auto_connect=False)
print(device.__class__.__name__)
```

Go to [API Reference](api/index.md) to select a specific driver.
