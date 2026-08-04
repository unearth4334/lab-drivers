"""lab_drivers package.

Reusable laboratory equipment drivers for VISA and serial instruments.

Drivers report through :mod:`logging` rather than printing, so nothing is
emitted until the application asks for it. Scripts that want the console output
the drivers used to print call :func:`enable_console_logging` once at start-up::

    import lab_drivers
    from lab_drivers.drivers.visa import DMM6500

    lab_drivers.enable_console_logging()
    dmm = DMM6500()
"""

from lab_drivers.core.log import enable_console_logging, get_logger, remove_console_logging

__all__ = [
    "core",
    "drivers",
    "enable_console_logging",
    "get_logger",
    "remove_console_logging",
]
