# Spectrum Analysis Examples

## RSA3030: Basic Sweep

```python
from lab_drivers.drivers.visa import RSA3030

rsa = RSA3030()
rsa.configure_spectrum(
    center_freq=2.4e9,
    span=100e6,
    rbw=100e3,
    vbw=100e3,
)

data = rsa.capture_spectrogram(filename="capture.csv")
print(f"Points: {data['points']}")

rsa.disconnect()
```

## RSA3030: Peak Search from Trace

```python
from lab_drivers.drivers.visa import RSA3030

rsa = RSA3030()
rsa.configure_spectrum(center_freq=915e6, span=20e6, rbw=10e3, vbw=10e3)
freqs, amps = rsa.capture_trace(trace_number=1)
peak_index = amps.index(max(amps))
print(f"Peak {amps[peak_index]:.2f} dBm @ {freqs[peak_index]/1e6:.3f} MHz")
rsa.disconnect()
```
