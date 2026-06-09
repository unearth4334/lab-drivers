# Install Instructions

## Requirements

- Python 3.9+
- VISA runtime for VISA-connected instruments

## Install from GitHub

The simplest way to install `lab-drivers` into any project environment is directly from GitHub using pip.

Replace `v0.1.0` with the [latest tagged release](https://github.com/unearth4334/lab-drivers/releases) if a newer version is available.

```bash
pip install "lab-drivers[all] @ git+https://github.com/unearth4334/lab-drivers.git@v0.2.3"
```

## Add as a project dependency

**`pyproject.toml`** — add to your `[project]` dependencies:

```toml
[project]
dependencies = [
  "lab-drivers[all] @ git+https://github.com/unearth4334/lab-drivers.git@v0.2.3",
]
```

**`requirements.txt`:**

```text
lab-drivers[all] @ git+https://github.com/unearth4334/lab-drivers.git@v0.2.3
```

Then install normally:

```bash
pip install -r requirements.txt
```

## Local / editable install

For development or contributing to this repository:

```bash
git clone https://github.com/unearth4334/lab-drivers.git
cd lab-drivers
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[all]"
```

## Verify

```python
from lab_drivers.drivers.visa import DMM6500

device = DMM6500(auto_connect=False)
print(device.__class__.__name__)
```

Go to [API Reference](api/index.md) to select a specific driver.
