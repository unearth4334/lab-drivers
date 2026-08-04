"""Serial-port selection, with a safe default for unattended callers.

The serial drivers historically resolved a missing port by printing a menu and
calling :func:`input`. That is fine at a bench and fatal anywhere else: an
automation server, a CI job or a ``nohup`` script has nobody to answer, so the
call blocks forever rather than failing.

:func:`select_port` keeps the menu for an interactive terminal and raises a
clear :class:`ConnectionError` everywhere else. ``interactive`` decides:

* ``None`` (default) -- prompt only when stdin is a terminal;
* ``True`` -- always prompt;
* ``False`` -- never prompt, raise instead.
"""

from __future__ import annotations

import os
import sys
import warnings

import serial.tools.list_ports

from lab_drivers.core.log import get_logger

_log = get_logger(__name__)


def resolve_address(address: str | None, com_port: str | None) -> str | None:
    """Fold the deprecated ``com_port=`` argument into ``address=``.

    The serial drivers originally named this parameter ``com_port`` while the
    VISA drivers used ``address``. They are one concept, so ``address`` is now
    the name on every driver; ``com_port`` keeps working for the existing
    callers and warns, per the project's deprecation policy.
    """
    if com_port is not None:
        warnings.warn(
            "com_port= is deprecated and will be removed in 1.0; use address=",
            DeprecationWarning,
            stacklevel=3,
        )
        return address or com_port
    return address


def can_prompt(interactive: bool | None = None) -> bool:
    """Whether this process may stop and ask the operator a question."""
    if interactive is not None:
        return interactive
    stdin = getattr(sys, "stdin", None)
    try:
        return bool(stdin is not None and stdin.isatty())
    except (AttributeError, ValueError):  # closed or replaced stream
        return False


def select_port(
    instrument: str,
    *,
    port: str | None = None,
    env_var: str | None = None,
    interactive: bool | None = None,
) -> str:
    """Resolve the serial port to open for ``instrument``.

    Resolution order: the explicit ``port``, then ``env_var``, then an
    interactive menu when one is permitted.

    Raises:
        ConnectionError: no port could be resolved, or one was needed but this
            process cannot prompt for it.
    """
    if port:
        return port

    if env_var:
        from_env = os.environ.get(env_var)
        if from_env:
            _log.debug("%s: using %s from %s", instrument, from_env, env_var)
            return from_env

    ports = serial.tools.list_ports.comports()
    if not ports:
        raise ConnectionError(f"No serial ports found for {instrument}.")

    if not can_prompt(interactive):
        available = ", ".join(p.device for p in ports)
        hint = f" or set {env_var}" if env_var else ""
        raise ConnectionError(
            f"No serial port given for {instrument} and this process cannot prompt for "
            f"one. Pass address=<port>{hint}. Available ports: {available}."
        )

    print(f"\nAvailable COM ports for {instrument}:")
    for index, entry in enumerate(ports, start=1):
        print(f"  {index}. {entry.device} - {entry.description}")

    while True:
        try:
            selection = int(input(f"Select COM port for {instrument} (1, 2, ...): "))
        except ValueError:
            print("Invalid input. Enter a number.")
            continue
        except (EOFError, KeyboardInterrupt) as ex:
            raise ConnectionError(f"Port selection for {instrument} was cancelled.") from ex
        if 1 <= selection <= len(ports):
            chosen = ports[selection - 1].device
            if env_var:
                os.environ[env_var] = chosen
            return chosen
        print("Invalid selection.")
