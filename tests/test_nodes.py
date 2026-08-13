"""Node-layer contract.

These need ``automation_nodes``, which the DM-TP automation server provides at
runtime. They skip where it is absent -- the driver layer must remain testable
on its own, which is the whole reason the node code lives in a separate package.
"""

from __future__ import annotations

import logging
import threading

import pytest

pytest.importorskip("automation_nodes", reason="DM-TP automation_nodes not on the path")

from automation_nodes.base import NodeContext  # noqa: E402
from automation_nodes.registry import NodeRegistry  # noqa: E402

import lab_drivers_nodes  # noqa: E402,F401  (imported for its @register side effects)
from lab_drivers_nodes._logging import driver_logs_to  # noqa: E402

# lab_drivers.core.log (and its get_logger helper) no longer exists on main --
# none of the driver modules call `logging` today, they print via colorama
# instead. driver_logs_to() itself is still real, working code (kept for when
# structured logging returns, or is replaced by a console-capture mechanism),
# so these tests drive it directly against the stdlib logging module rather
# than through the deleted convenience wrapper.
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

NODE_TYPES = ["dmm6500-measure", "ka3010p-output", "rigol-dp711-output"]


@pytest.fixture
def registry() -> NodeRegistry:
    reg = NodeRegistry()
    for node_cls in (
        lab_drivers_nodes.DMM6500MeasureNode,
        lab_drivers_nodes.KA3010POutputNode,
        lab_drivers_nodes.RigolDP711OutputNode,
    ):
        reg.add(node_cls)
    return reg


class _Recorder:
    """Minimal stand-in for the run's execution log."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def context(self) -> NodeContext:
        return NodeContext(config={}, log=lambda level, text: self.lines.append((level, text)))


# ---- registration ----------------------------------------------------------


@pytest.mark.parametrize("type_key", NODE_TYPES)
def test_node_types_are_registered(registry: NodeRegistry, type_key: str) -> None:
    assert registry.get(type_key) is not None


@pytest.mark.parametrize("type_key", NODE_TYPES)
def test_catalog_entries_are_complete(registry: NodeRegistry, type_key: str) -> None:
    entry = next(e for e in registry.catalog() if e["type"] == type_key)

    assert entry["label"] and entry["summary"]
    assert entry["category"] == "instrument"
    # Every node inherits the address input from InstrumentNode.
    assert "address" in [i["name"] for i in entry["inputs"]]


def test_configuration_defaults_validate(registry: NodeRegistry) -> None:
    node = registry.create("ka3010p-output", {})

    assert node.config["voltage"] == 0.0
    assert node.config["output_on"] is True


def test_out_of_range_configuration_is_rejected(registry: NodeRegistry) -> None:
    from automation_nodes.base import NodeValidationError

    with pytest.raises(NodeValidationError):
        registry.create("ka3010p-output", {"voltage": 500.0})


def test_unknown_configuration_key_is_rejected(registry: NodeRegistry) -> None:
    from automation_nodes.base import NodeValidationError

    with pytest.raises(NodeValidationError, match="Unknown input"):
        registry.create("dmm6500-measure", {"sampels": 3})


def test_measurement_function_is_a_closed_set(registry: NodeRegistry) -> None:
    from automation_nodes.base import NodeValidationError

    with pytest.raises(NodeValidationError):
        registry.create("dmm6500-measure", {"function": "Inductance"})


# ---- log bridging ----------------------------------------------------------


def test_driver_logs_reach_the_node_context() -> None:
    recorder = _Recorder()
    with driver_logs_to(recorder.context()):
        get_logger("lab_drivers.test").info("connected to instrument")

    assert ("info", "connected to instrument") in recorder.lines


def test_log_levels_map_to_context_levels() -> None:
    recorder = _Recorder()
    with driver_logs_to(recorder.context(), level=logging.DEBUG):
        log = get_logger("lab_drivers.test")
        log.error("bad")
        log.warning("careful")

    assert ("error", "bad") in recorder.lines
    assert ("warn", "careful") in recorder.lines


def test_the_handler_is_removed_afterwards() -> None:
    recorder = _Recorder()
    with driver_logs_to(recorder.context()):
        pass
    get_logger("lab_drivers.test").info("after the block")

    assert recorder.lines == []


def test_another_threads_records_are_not_captured() -> None:
    """Two checkpoints running at once must not cross-contaminate their logs."""
    recorder = _Recorder()
    done = threading.Event()

    def other_thread() -> None:
        get_logger("lab_drivers.test").info("from the other node")
        done.set()

    with driver_logs_to(recorder.context()):
        worker = threading.Thread(target=other_thread)
        worker.start()
        done.wait(timeout=5)
        worker.join(timeout=5)
        get_logger("lab_drivers.test").info("from this node")

    assert ("info", "from this node") in recorder.lines
    assert ("info", "from the other node") not in recorder.lines


# ---- headless behaviour ----------------------------------------------------


def test_nodes_build_drivers_without_prompting(registry: NodeRegistry) -> None:
    """make_driver must construct unconnected, and never stop to ask anything."""
    for type_key in ("ka3010p-output", "rigol-dp711-output"):
        node = registry.create(type_key, {})
        driver = node.make_driver()
        assert driver.status == "Not Connected"


def test_nodes_are_pinned_non_interactive(registry: NodeRegistry) -> None:
    assert registry.create("ka3010p-output", {}).interactive is False


# ---- connection kwarg adaptation --------------------------------------------
#
# lab-drivers' connect() methods disagree on the port-selection kwarg: most
# VISA drivers take `address`, the serial ones take `com_port`, and a few
# auto-detect with no port kwarg at all. LabDriverNode._connect() picks the
# right one by inspecting the driver's actual connect() signature.


class _FakeDriverBase:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def disconnect(self) -> None:
        self.calls.append(("disconnect",))


def _node_with_driver(monkeypatch: pytest.MonkeyPatch, driver: object) -> "lab_drivers_nodes.DMM6500MeasureNode":
    node = lab_drivers_nodes.DMM6500MeasureNode({"function": "DC voltage", "samples": 1, "nplc": 1.0})
    monkeypatch.setattr(node, "make_driver", lambda: driver)
    monkeypatch.setattr(node, "perform", lambda driver, context: None)
    return node


def test_connect_prefers_address_kwarg_when_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    class Driver(_FakeDriverBase):
        def connect(self, address=None):
            self.calls.append(("connect", "address", address))

    driver = Driver()
    node = _node_with_driver(monkeypatch, driver)
    node.config["address"] = "TCPIP::1.2.3.4::INSTR"
    node.execute(NodeContext(config=node.config))

    assert ("connect", "address", "TCPIP::1.2.3.4::INSTR") in driver.calls


def test_connect_falls_back_to_com_port_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    class Driver(_FakeDriverBase):
        def connect(self, com_port=None):
            self.calls.append(("connect", "com_port", com_port))

    driver = Driver()
    node = _node_with_driver(monkeypatch, driver)
    node.config["address"] = "COM4"
    node.execute(NodeContext(config=node.config))

    assert ("connect", "com_port", "COM4") in driver.calls


def test_connect_calls_bare_connect_when_driver_only_auto_detects(monkeypatch: pytest.MonkeyPatch) -> None:
    class Driver(_FakeDriverBase):
        def connect(self):
            self.calls.append(("connect",))

    driver = Driver()
    node = _node_with_driver(monkeypatch, driver)
    node.config["address"] = "ignored"
    logged: list[str] = []
    context = NodeContext(config=node.config, log=lambda level, text: logged.append(text))
    node.execute(context)

    assert ("connect",) in driver.calls
    assert any("ignored" in line for line in logged)


def test_connect_skips_the_call_entirely_when_address_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    class Driver(_FakeDriverBase):
        def connect(self, address=None):
            self.calls.append(("connect", address))

    driver = Driver()
    node = _node_with_driver(monkeypatch, driver)
    node.execute(NodeContext(config=node.config))

    assert ("connect", None) in driver.calls


def test_disconnect_always_runs_even_when_connect_is_never_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    class Driver(_FakeDriverBase):
        def connect(self, address=None):
            raise ConnectionError("simulated failure")

    driver = Driver()
    node = _node_with_driver(monkeypatch, driver)
    with pytest.raises(Exception):
        node.execute(NodeContext(config=node.config))

    assert ("disconnect",) in driver.calls


# ---- generated coverage (automation_nodes.introspect) ----------------------
#
# Most instrument methods reach the picker via generation, not hand-written
# wrappers -- see lab_drivers_nodes/__init__.py. These exercise that coverage
# through the real discovery path (not the curated-only `registry` fixture
# above), so a count assertion is used instead of an exhaustive type-key list:
# the exact count shifts whenever a driver gains/loses a method.


@pytest.fixture
def discovered_registry() -> NodeRegistry:
    reg = NodeRegistry()
    reg.discover(extra_packages=["lab_drivers_nodes"])
    return reg


def test_generation_covers_far_more_than_the_curated_nodes(discovered_registry: NodeRegistry) -> None:
    assert len(discovered_registry.types()) > 40, discovered_registry.warnings


def test_generated_nodes_are_attributed_to_this_package(discovered_registry: NodeRegistry) -> None:
    catalog = {entry["type"]: entry for entry in discovered_registry.catalog()}
    generated = catalog["dl3021-enable"]  # DL3021 has no hand-written node

    assert generated["package"] == "lab_drivers_nodes"
    assert generated["instrument"] == {"key": "dl3021", "label": "Rigol DL3021 Electronic Load"}


def test_excluded_methods_are_not_also_generated(discovered_registry: NodeRegistry) -> None:
    """The curated nodes' own methods must not get a second, raw-method node."""
    type_keys = set(discovered_registry.types())
    assert "dmm6500-measure-voltage" not in type_keys
    assert "ka3010p-set-voltage" not in type_keys
    assert "rigol-dp711-turn-on" not in type_keys


def test_generated_node_types_survive_forced_rediscovery(discovered_registry: NodeRegistry) -> None:
    """Regression: generated classes must report their real owning module.

    A forced re-discovery (every node-package install/update/uninstall) can't
    re-run an already-imported module's top-level code, so it recovers types
    via module-prefix ownership matching. Generated classes originally
    reported ``automation_nodes.introspect`` as their module (the frame where
    ``type()`` was called), not ``lab_drivers_nodes`` -- silently dropping
    every generated node on the next re-discovery even though the package
    stayed installed.
    """
    before = len(discovered_registry.types())
    discovered_registry.discover(extra_packages=["lab_drivers_nodes"], force=True)
    assert len(discovered_registry.types()) == before


# ---- connection editor + connection test -----------------------------------
#
# Every instrument node declares how it is addressed (a ConnectionSpec) and can
# be connection-tested. VISA drivers get the resource/LAN transports; serial
# drivers get the serial-port transport. The test itself connects through the
# same _connect() a run uses, so it honours each driver's connect() kwarg.


def test_visa_nodes_offer_the_visa_transport_set(registry: NodeRegistry) -> None:
    entry = next(e for e in registry.catalog() if e["type"] == "dmm6500-measure")
    assert entry["supports_connection_test"] is True
    keys = [t["key"] for t in entry["connection"]["transports"]]
    assert keys == ["visa", "tcpip", "socket", "auto", "direct"]


def test_serial_nodes_offer_the_serial_transport_set(registry: NodeRegistry) -> None:
    entry = next(e for e in registry.catalog() if e["type"] == "ka3010p-output")
    keys = [t["key"] for t in entry["connection"]["transports"]]
    assert keys == ["serial", "auto", "direct"]


def test_generated_visa_nodes_carry_the_visa_connection(discovered_registry: NodeRegistry) -> None:
    entry = next(e for e in discovered_registry.catalog() if e["type"] == "dl3021-enable")
    keys = [t["key"] for t in entry["connection"]["transports"]]
    assert keys == ["visa", "tcpip", "socket", "auto", "direct"]


class _IdentifiableDriver(_FakeDriverBase):
    """A VISA-style driver that connects by ``address`` and caches an identity."""

    def __init__(self) -> None:
        super().__init__()
        self.status = "Not Connected"
        self._idn = ""

    def connect(self, address=None):
        if address == "fail":
            raise ConnectionError("nothing at 'fail'")
        self.calls.append(("connect", address))
        self.status = "Connected"
        self._idn = f"KEITHLEY,DMM6500,{address or 'auto'},1.7"


def test_test_connection_connects_reads_identity_and_disconnects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _IdentifiableDriver()
    node = lab_drivers_nodes.DMM6500MeasureNode({"address": "TCPIP::localhost::5025::SOCKET"})
    monkeypatch.setattr(node, "make_driver", lambda: driver)

    result = node.test_connection()

    assert result.ok is True
    assert "KEITHLEY,DMM6500" in result.identity
    assert ("connect", "TCPIP::localhost::5025::SOCKET") in driver.calls
    assert ("disconnect",) in driver.calls


def test_test_connection_reports_failure_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _IdentifiableDriver()
    node = lab_drivers_nodes.DMM6500MeasureNode({"address": "fail"})
    monkeypatch.setattr(node, "make_driver", lambda: driver)

    result = node.test_connection()

    assert result.ok is False
    assert "fail" in result.message
    assert ("disconnect",) in driver.calls  # disconnect still runs


def test_test_connection_uses_the_serial_com_port_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A serial node's test must connect the way its driver does (com_port)."""

    class SerialDriver(_FakeDriverBase):
        def __init__(self) -> None:
            super().__init__()
            self.status = "Not Connected"

        def connect(self, com_port=None):
            self.calls.append(("connect", "com_port", com_port))
            self.status = "Connected"

    driver = SerialDriver()
    node = lab_drivers_nodes.KA3010POutputNode({"address": "/dev/ttyUSB0"})
    monkeypatch.setattr(node, "make_driver", lambda: driver)

    result = node.test_connection()

    assert result.ok is True
    assert ("connect", "com_port", "/dev/ttyUSB0") in driver.calls

