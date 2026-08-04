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
from lab_drivers.core.log import get_logger  # noqa: E402
from lab_drivers_nodes._logging import driver_logs_to  # noqa: E402

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
