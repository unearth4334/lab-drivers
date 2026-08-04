"""Driver-layer contract: imports, logging, addressing and headless safety.

None of these touch hardware. The serial tests stub ``comports`` so the
"no port given" paths are exercised on any machine.
"""

from __future__ import annotations

import io
import logging
import sys

import pytest

import lab_drivers
from lab_drivers.core import log as core_log
from lab_drivers.core import ports
from lab_drivers.core.progress import loading
from lab_drivers.drivers import serial as serial_pkg
from lab_drivers.drivers import visa as visa_pkg

SERIAL_DRIVERS = ["FLUKE45", "KA3010P", "RigolDP711", "U1233A"]


# ---- package exports -------------------------------------------------------


@pytest.mark.parametrize("name", visa_pkg.__all__)
def test_visa_names_resolve_to_classes(name: str) -> None:
    """``from lab_drivers.drivers.visa import X`` must give the class, not the module."""
    assert isinstance(getattr(visa_pkg, name), type)


@pytest.mark.parametrize("name", serial_pkg.__all__)
def test_serial_names_resolve_to_classes(name: str) -> None:
    assert isinstance(getattr(serial_pkg, name), type)


def test_full_module_path_import_still_works() -> None:
    """The path existing callers use must keep resolving to the same object."""
    from lab_drivers.drivers.visa import DMM6500 as viaPackage
    from lab_drivers.drivers.visa.DMM6500 import DMM6500 as viaModule

    assert viaPackage is viaModule


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        visa_pkg.NoSuchInstrument


# ---- logging ---------------------------------------------------------------


def test_package_is_silent_until_asked() -> None:
    """A library must not configure logging on import."""
    root = logging.getLogger(core_log.LOGGER_NAME)
    assert all(isinstance(h, logging.NullHandler) for h in root.handlers)


def test_console_logging_round_trip() -> None:
    stream = io.StringIO()
    lab_drivers.enable_console_logging(stream=stream)
    try:
        core_log.get_logger("lab_drivers.test").info("hello bench")
    finally:
        lab_drivers.remove_console_logging()

    assert "hello bench" in stream.getvalue()


def test_console_logging_is_not_installed_twice() -> None:
    """Calling twice must replace the handler, not double every line."""
    first, second = io.StringIO(), io.StringIO()
    lab_drivers.enable_console_logging(stream=first)
    lab_drivers.enable_console_logging(stream=second)
    try:
        core_log.get_logger("lab_drivers.test").info("once")
    finally:
        lab_drivers.remove_console_logging()

    assert second.getvalue().count("once") == 1
    assert first.getvalue() == ""
    assert logging.getLogger(core_log.LOGGER_NAME).handlers


def test_driver_loggers_sit_under_the_package_root() -> None:
    assert core_log.get_logger("lab_drivers.drivers.visa.DMM6500").name.startswith(
        f"{core_log.LOGGER_NAME}.")
    assert core_log.get_logger("plain").name == f"{core_log.LOGGER_NAME}.plain"


# ---- addressing ------------------------------------------------------------


def test_com_port_alias_warns_but_works() -> None:
    with pytest.warns(DeprecationWarning, match="com_port="):
        assert ports.resolve_address(None, "/dev/ttyUSB3") == "/dev/ttyUSB3"


def test_address_wins_over_the_deprecated_alias() -> None:
    with pytest.warns(DeprecationWarning):
        assert ports.resolve_address("/dev/ttyA", "/dev/ttyB") == "/dev/ttyA"


def test_address_alone_does_not_warn(recwarn) -> None:
    assert ports.resolve_address("/dev/ttyA", None) == "/dev/ttyA"
    assert not [w for w in recwarn if issubclass(w.category, DeprecationWarning)]


# ---- headless safety -------------------------------------------------------


class _FakePort:
    def __init__(self, device: str) -> None:
        self.device = device
        self.description = "fake"


@pytest.fixture
def fake_ports(monkeypatch):
    monkeypatch.setattr(
        ports.serial.tools.list_ports, "comports",
        lambda: [_FakePort("/dev/ttyFAKE0"), _FakePort("/dev/ttyFAKE1")],
    )


def test_explicit_port_is_returned_unchanged(fake_ports) -> None:
    assert ports.select_port("X", port="/dev/ttyUSB0") == "/dev/ttyUSB0"


def test_environment_variable_is_consulted(fake_ports, monkeypatch) -> None:
    monkeypatch.setenv("X_PORT", "/dev/ttyENV")
    assert ports.select_port("X", env_var="X_PORT") == "/dev/ttyENV"


def test_non_interactive_refuses_instead_of_prompting(fake_ports) -> None:
    """The whole point: no terminal means an error, never a blocked process."""
    with pytest.raises(ConnectionError) as excinfo:
        ports.select_port("X", env_var="X_PORT", interactive=False)

    message = str(excinfo.value)
    assert "cannot prompt" in message
    assert "/dev/ttyFAKE0" in message   # tells the operator what it could have used


def test_no_ports_at_all_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(ports.serial.tools.list_ports, "comports", list)
    with pytest.raises(ConnectionError, match="No serial ports found"):
        ports.select_port("X", interactive=False)


def test_can_prompt_follows_stdin(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO())   # not a tty
    assert ports.can_prompt() is False
    assert ports.can_prompt(True) is True


def test_progress_prompt_refuses_when_unattended() -> None:
    with pytest.raises(RuntimeError, match="Interactive input is required"):
        loading(interactive=False).input_with_flashing("continue? ")


def test_progress_helpers_are_silent_no_ops() -> None:
    helper = loading(interactive=False)
    helper.delay_with_loading_indicator(0.0)
    helper.display_loading_bar(0.5, "working")


@pytest.mark.parametrize("name", SERIAL_DRIVERS)
def test_serial_drivers_refuse_to_connect_without_a_port(name, fake_ports) -> None:
    """Every serial driver must fail fast rather than block on a prompt."""
    driver_cls = getattr(serial_pkg, name)
    with pytest.raises(ConnectionError):
        driver_cls(auto_connect=True, interactive=False)


@pytest.mark.parametrize("name", SERIAL_DRIVERS)
def test_serial_drivers_still_accept_com_port(name, fake_ports) -> None:
    driver_cls = getattr(serial_pkg, name)
    with pytest.warns(DeprecationWarning):
        driver_cls(auto_connect=False, com_port="/dev/ttyUSB0")


@pytest.mark.parametrize(
    "name", ["Keysight34460A", "RigolDP832", "RigolDS7034", "DMM6500", "DL3021"])
def test_visa_connect_accepts_an_address(name) -> None:
    """InstrumentNode always calls connect(address=...); every driver must accept it."""
    import inspect

    signature = inspect.signature(getattr(visa_pkg, name).connect)
    assert "address" in signature.parameters


def test_fetch_trace_does_not_prompt_by_default() -> None:
    import inspect

    signature = inspect.signature(visa_pkg.DMM6500.fetch_trace)
    assert signature.parameters["step"].default is False
    assert signature.parameters["debug"].default is False
