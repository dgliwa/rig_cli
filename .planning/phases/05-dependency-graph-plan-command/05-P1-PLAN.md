---
phase: 5
plan: P1
type: implementation
wave: 1
depends_on: []
files_modified:
  - src/rig/models/graph.py
  - src/rig/models/rig.py
  - tests/test_graph.py
requirements: [D-01, D-02, D-03]
must_haves:
  - DeviceGraph class exists at src/rig/models/graph.py and is importable
  - DeviceGraph(rig).apply_order() returns devices in signal-chain position order with controllers last
  - DeviceGraph raises ConfigError on cycle detection
  - Rig.apply_order() delegates to DeviceGraph without changing its signature
  - tests/test_graph.py passes with all cases covered
---

# Phase 5 P1: DeviceGraph Model

## Context

`Rig.apply_order()` contains the signal-chain + controller-last ordering logic inline. This plan
formalizes that logic into a standalone `DeviceGraph` class in `src/rig/models/graph.py` with
explicit cycle detection. `Rig.apply_order()` is updated to delegate to it — no external callers
change. Decision D-01 specifies DeviceGraph as a standalone class (not embedded in Rig). D-02
specifies edges are derived from signal_chain position order only, with CONTROLLER devices always
last. D-03 specifies ConfigError as the exception type on cycle detection.

The current `Rig.apply_order()` implementation (rig.py lines 79-103) is the authoritative
reference for ordering logic. Mirror it exactly, then layer cycle detection on top.

---

## Task P5-T1: Create src/rig/models/graph.py

**File:** `src/rig/models/graph.py`

**Changes:**

Add `from __future__ import annotations` at the top. Import `logging`, `Device`, `DeviceType`
from `rig.models.device`, `SignalChainPosition` from `rig.models.signal_chain`, and `ConfigError`
from `rig.config.errors`. Add `TYPE_CHECKING` guard and import `Rig` under it to avoid circular
imports (graph imports from rig, rig will import from graph).

Define a `CycleError(ConfigError)` subclass with docstring `"""Signal chain contains a cycle."""`

Define `DeviceGraph` as a plain Python class (not a Pydantic BaseModel, per D-01) with:

- `__init__(self, rig: Rig) -> None` — stores `self._rig = rig`
- `apply_order(self) -> list[Device]` — implements ordering with cycle detection

The `apply_order()` implementation must:

1. Return `[]` immediately when `self._rig.devices` is empty.
2. Run cycle detection before building the ordered list. Cycle detection: build a graph where
   nodes are device IDs present in `signal_chain`. For each consecutive pair `(signal_chain[i],
   signal_chain[i+1])`, add a directed edge `i.device_ref → i+1.device_ref`. Run DFS with a
   `visited` set and a `recursion_stack` set. If a node is encountered that is already in
   `recursion_stack`, raise `CycleError` with message
   `f"Cycle detected in signal chain involving device '{device_id}'"`. In practice, `signal_chain`
   is a linear list so cycles require a device appearing twice. Check for duplicate `device_ref`
   values in `signal_chain` — if any `device_ref` appears more than once, raise `CycleError` with
   message `f"Device '{device_ref}' appears multiple times in signal chain"`. This is the realistic
   cycle scenario for this domain.
3. After cycle detection, mirror the exact logic from `Rig.apply_order()` lines 79-103:
   - Find controller device (first device where `device.type == DeviceType.CONTROLLER`).
   - Build `chain_positions: dict[str, int]` from `signal_chain` positions.
   - Separate devices into `in_chain` (in signal_chain, not controller) and `off_chain` (not in
     signal_chain, not controller).
   - Sort `in_chain` by position.
   - Return `in_chain + off_chain + [ctrl]` (ctrl omitted from list if None).

Module-level logger: `logger = logging.getLogger(__name__)`

Export `DeviceGraph` and `CycleError` at module level (they are the only public names).

Do not add docstrings beyond the class-level one for `CycleError` — code is self-documenting per
project convention.

### Tests

None for this task — tests are in Task P5-T3.

---

## Task P5-T2: Update Rig.apply_order() to delegate

**File:** `src/rig/models/rig.py`

**Changes:**

Add import: `from rig.models.graph import DeviceGraph` inside `apply_order()` as a local import
(to avoid circular import at module level — `graph.py` imports `Rig` under `TYPE_CHECKING`, so
a local import here is safe at runtime).

Replace the body of `apply_order()` (lines 79-103) with:

```
def apply_order(self) -> list[Device]:
    """Return devices in apply order: signal-chain devices by position, off-chain devices, then controller last."""
    from rig.models.graph import DeviceGraph
    return DeviceGraph(self).apply_order()
```

No other changes to `rig.py`. The method signature is unchanged. The docstring stays as-is.

### Tests

None for this task — covered by test_graph.py.

---

## Task P5-T3: Create tests/test_graph.py

**File:** `tests/test_graph.py`

**Changes:**

Add `from __future__ import annotations`. Import `pytest`, `DeviceGraph`, `CycleError` from
`rig.models.graph`, `ConfigError` from `rig.config.errors`, `Device` and `DeviceType` from
`rig.models.device`, `ManualConfig`, `MidiConfig`, `ControllerConfig` from `rig.models.device`,
`DigitalPreset` from `rig.models.preset`, `Rig` from `rig.models.rig`, `Scene` from
`rig.models.scene`, `SignalChainPosition` from `rig.models.signal_chain`.

Create a `_make_device(id, type, config=None)` builder that returns a `Device` with `manufacturer`
and `model` set to short strings. Default config: `ManualConfig()` for analog/manual types,
`MidiConfig(midi_channel=1)` for digital/modeler. Accept override via `config` kwarg.

Create a `_make_rig(devices, signal_chain_ids, scenes=None)` builder: constructs `Rig` with
`name="test"`, `devices` dict from the list of Device objects (keyed by `device.id`), and
`signal_chain` built from `signal_chain_ids` as `[SignalChainPosition(device_ref=id, position=i)
for i, id in enumerate(signal_chain_ids)]`. Scene support is optional for these tests; pass an
empty `ControllerConfig` or omit.

Write test cases grouped by class:

**class TestApplyOrder:**
- `test_linear_signal_chain_order`: three devices `[d1, d2, d3]` in signal chain positions 0/1/2,
  no controller; assert `apply_order()` returns `[d1, d2, d3]`.
- `test_controller_always_last`: two effect devices in signal chain, one controller device NOT in
  signal chain; assert controller is last in result regardless of insertion order in `devices` dict.
- `test_off_chain_device_between_chain_and_controller`: one in-chain device, one device absent from
  signal chain (not controller), one controller; assert order is `[in_chain, off_chain, ctrl]`.
- `test_empty_devices_returns_empty_list`: `Rig` with no devices, any signal_chain; assert
  `apply_order()` returns `[]`.
- `test_single_device_no_signal_chain`: one non-controller device, empty signal_chain; assert
  `apply_order()` returns `[device]` (it is off-chain).

**class TestCycleDetection:**
- `test_no_duplicate_passes`: signal chain with unique device refs — no exception raised.
- `test_duplicate_device_ref_raises_cycle_error`: signal chain where the same `device_ref` appears
  twice (e.g., `["hx", "brothers", "hx"]`); assert `DeviceGraph(rig).apply_order()` raises
  `CycleError`. Use `pytest.raises(CycleError)`.
- `test_cycle_error_is_config_error`: verify `CycleError` is a subclass of `ConfigError` by
  asserting `issubclass(CycleError, ConfigError)`.

All assertions use plain `assert` statements. No pytest fixtures required — use builder helpers.

### Verification

```
uv run pytest tests/test_graph.py -v
```

All tests must pass. Zero failures.
