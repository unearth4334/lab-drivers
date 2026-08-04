# Compatibility and Versioning Policy

This document describes how `lab-drivers` manages API stability and compatibility across releases.

## Versioning Scheme

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version bump: Breaking API changes (old code may need updates)
- **MINOR** version bump: New backward-compatible features
- **PATCH** version bump: Bug fixes and internal improvements

## Compatibility Windows

- **Current major version** (e.g., v0.x.y): Full backward compatibility within the version
- **Previous major version**: Deprecation warnings for 2+ minor releases, then removal
- **Older major versions**: Not supported; migrate to current version

## API Stability

### What's Stable (Won't Break)
- Driver class constructors (`DMM6500()`, `U1233A()`, etc.)
- Core measurement methods (`measure_voltage()`, `connect()`, `disconnect()`, `get()`)
- VISA resource discovery and error handling
- CSV/data export formats

### What Can Change
- Internal implementation (wire protocol, caching, buffering)
- Optional helper utilities (progress spinners, logging)
- Package layout (import paths may change; use public `__all__` exports)
- Debug/diagnostic attributes (prefixed with `_`)

## Current Deprecations

| Deprecated | Since | Replacement | Removal |
| --- | --- | --- | --- |
| `com_port=` on serial constructors and `connect()` | 0.2.0 | `address=` | 1.0.0 |

`address=` is now the parameter name on every driver, VISA and serial alike, so
one caller can address any instrument the same way. Passing `com_port=` still
works and emits a `DeprecationWarning`.

Behaviour changes in 0.2.0 that are not API breaks, but are worth knowing:

- **Drivers no longer print.** Output goes to the `lab_drivers` logger and is
  silent until the application configures logging. Call
  `lab_drivers.enable_console_logging()` to restore the previous console output.
- **No prompting without a terminal.** A driver that cannot resolve a serial
  port now raises `ConnectionError` instead of printing a selection menu, unless
  stdin is a tty. The old behaviour blocked forever under a server or CI job.
- **`DMM6500.fetch_trace(step=)` now defaults to `False`.** It previously
  defaulted to `True`, prompting between every buffer transfer.

Fixed in 0.2.0: `Keysight34460A`, `RigolDP832`, `RigolDS7034` and `U1233A` could
not be imported at all -- they referenced a `loading` module that does not exist
in this repository.

## Deprecation Process

1. **Announce** deprecated API in release notes and docstrings
2. **Warn** at runtime for 2+ minor releases (e.g., v0.5 → v0.7)
3. **Remove** in next major release (e.g., v1.0)

Example:
```python
# v0.5.0: Announce deprecation
def old_method(self):
    """Deprecated. Use new_method() instead."""
    import warnings
    warnings.warn("old_method() is deprecated; use new_method()", DeprecationWarning)
    return self.new_method()

# v0.7.0+: Remove old_method entirely
```

## Consumer Requirements

When depending on `lab-drivers`, consumers should:

1. **Pin to a major version** (recommended):
   ```toml
   lab-drivers @ git+https://github.com/unearth4334/lab-drivers.git@v0.1.0
   ```

2. **Read release notes** before upgrading to a new major version

3. **Run smoke tests** after updating (recommended via CI)

## Release Checklist

Before tagging a release:
- [ ] Update `pyproject.toml` version
- [ ] Update `README.md` if user-facing behavior changed
- [ ] Document breaking changes in release notes
- [ ] Tag commit: `git tag -a v0.x.y -m "Release v0.x.y"`
- [ ] Push tag: `git push origin v0.x.y`

## Questions or Issues?

If you find a breaking change or incompatibility:
1. Check the release notes for that version
2. File an issue describing the problem and version you're using
3. For urgent compatibility gaps, open a PR with a temporary shim/alias
