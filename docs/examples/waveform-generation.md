# Waveform Generation Examples

## KS33500B: Single Channel Sine

```python
from lab_drivers.drivers.visa import KS33500B

wfg = KS33500B()
wfg.set_function("SIN", channel=1)
wfg.set_frequency(1000.0, channel=1)
wfg.set_amplitude(2.0, channel=1)
wfg.set_output_state(True, channel=1)

# ... test setup here ...

wfg.set_output_state(False, channel=1)
wfg.disconnect()
```

## KS33500B: Dual Channel Signals

```python
from lab_drivers.drivers.visa import KS33500B

wfg = KS33500B()

wfg.set_function("SIN", channel=1)
wfg.set_frequency(1000.0, channel=1)
wfg.set_amplitude(1.0, channel=1)

wfg.set_function("SQU", channel=2)
wfg.set_frequency(500.0, channel=2)
wfg.set_amplitude(1.0, channel=2)

wfg.set_output_state(True, channel=1)
wfg.set_output_state(True, channel=2)

wfg.disconnect()
```
