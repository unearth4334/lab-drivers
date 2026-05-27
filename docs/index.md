# Lab Drivers Reference

`v0.2.2` — Reusable Python drivers for VISA and serial lab instruments.

## Fast path

1. Install dependencies from [Install Instructions](install-instructions.md).
2. Open [API Reference](api/index.md).
3. Pick a driver and use the generated class/method docs.

## Drivers at a glance

| Driver | Interface | Instrument type |
|---|---|---|
| [DL3021](api/drivers/dl3021.md) | VISA | Electronic load |
| [DMM6500](api/drivers/dmm6500.md) | VISA | Digital multimeter |
| [DP832](api/drivers/dp832.md) | VISA | DC power supply |
| [FLUKE45](api/drivers/fluke45.md) | Serial | Digital multimeter |
| [KA3010P](api/drivers/ka3010p.md) | Serial | DC power supply |
| [Keysight34460A](api/drivers/keysight34460a.md) | VISA | Digital multimeter |
| [KeysightMSOX4154A](api/drivers/keysightmsox4154a.md) | VISA | Mixed-signal oscilloscope |
| [KS33500B](api/drivers/ks33500b.md) | VISA | Waveform generator |
| [RigolDP711](api/drivers/rigoldp711.md) | Serial | DC power supply |
| [RigolDP832](api/drivers/rigoldp832.md) | VISA | DC power supply |
| [RigolDS1054Z](api/drivers/rigolds1054z.md) | VISA | Digital oscilloscope |
| [RigolDS7034](api/drivers/rigolds7034.md) | VISA | Digital oscilloscope |
| [RSA3030](api/drivers/rsa3030.md) | VISA | Spectrum analyser |
| [StanfordPS310](api/drivers/stanfordps310.md) | VISA | HV power supply |
| [TektronixMSO4](api/drivers/tektronixmso4.md) | VISA | Mixed-signal oscilloscope |
| [U1233A](api/drivers/u1233a.md) | Serial | Digital multimeter |

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

```python
# Oscilloscopes (KeysightMSOX4154A and TektronixMSO4 share the same API)
from lab_drivers.drivers.visa import TektronixMSO4

scope = TektronixMSO4()
wfm = scope.get_waveform(channel=1)
print(wfm["t"], wfm["y"])  # time axis and scaled voltage samples
scope.disconnect()
```
