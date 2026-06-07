# Phase 3: Core Domain Refactor - Research

**Researched:** 2026-06-04
**Domain:** Python domain modeling — Pydantic discriminated unions, structural Protocols, graph traversal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rig as DeviceGraph (D-01 through D-03)**
- D-01: `Rig` IS the DeviceGraph — no separate `DeviceGraph` type. `Rig` gains graph methods directly.
- D-02: Phase 3 adds only `apply_order()` to `Rig`. No `edges`, `nodes`, or `device_at()` in this phase.
- D-03: `apply_order()` is a DFS from the Controller root, children visited in signal chain order.

**Controller as a Special Device Type (D-04 through D-07)**
- D-04: `DeviceType` enum gains `CONTROLLER`. Controller's config joins the `DeviceConfig` discriminated union.
- D-05: `scenes` move from `Rig` to Controller's model. `Rig` no longer owns scenes directly.
- D-06: YAML config-repo layout changes are required and expected. User is NOT concerned about breaking the companion rig config repo.
- D-07: Signal chain edges only in Phase 3. Controller→device trigger relationship is implicit.

**DevicePlugin Protocol (D-08 through D-10)**
- D-08: `DevicePlugin` defines `plan(device, ctx)`, `diff(device, ctx)`, `apply(device, ctx)`.
- D-09: `PluginContext` base dataclass: `state: RigState`, `rig: Rig`, `dry_run: bool` only.
- D-10: `PluginRegistry` exists and is wirable; existing appliers NOT registered (Phase 4).

**Graph Edge Semantics (D-11)**
- D-11: Graph edges represent signal chain only. No separate ownership/dependency edge types.

### Claude's Discretion
- Where to put `ControllerConfig` in the file hierarchy (extend `device.py` or keep in `controller.py` and re-export)
- Exact shape of the `PluginRegistry` wrapper class vs. a plain dict
- How to bridge `rig.scenes` access in CLI/engine in Phase 3 (compatibility shim vs. direct migration)

### Deferred Ideas (OUT OF SCOPE)
- Device trigger registration protocol
- Ownership/dependency edges
- `Rig.edges` / `Rig.device_at()`
- Full CLI migration of `rig.scenes` reads (Phase 4 scope)
</user_constraints>

---

## Summary

Phase 3 is a pure domain modeling refactor with no new user-visible behavior. The codebase is in a clean, tested state (167 passing tests) after Phase 2. The refactor has four independent threads that must land in a careful order: (1) add `ControllerConfig` to the `DeviceConfig` discriminated union so Controller is a Device, (2) move `scenes` off `Rig` and onto Controller's model, (3) add `apply_order()` to `Rig`, and (4) introduce the `DevicePlugin`/`PluginContext`/`PluginRegistry` scaffold.

The primary risk is that `rig.scenes` is accessed in 7 places across the engine and CLI — `diff.py`, `plan/compute.py`, `apply.py`, `mc6.py` (applier), and two CLI commands (`validate.py`, `status.py`). If scenes move to `rig.controller.scenes` without a compatibility bridge, all of these break simultaneously. The safest execution path is to add a `scenes` property shim on `Rig` that delegates to `rig.controller.scenes` (when Controller is present) for Phase 3 backward compatibility, then remove the shim in Phase 4 when those callers are fully migrated.

The second risk is that `Controller` and `Rig` currently import from `controller.py` independently — folding Controller into the Device model requires deciding whether `controller.py` becomes a thin re-export or is dissolved into `device.py`. The existing `ControllerType` enum is referenced in tests (`test_models.py`, `test_mc6_generator.py`), so it must be preserved or re-exported.

**Primary recommendation:** Land changes in wave order: fixtures first, then models, then loader, then compatibility shims, then the new plugin scaffold — each wave fully tested before the next begins.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Controller-as-Device modeling | Domain Models (`models/`) | — | Pure data; no behavior |
| `apply_order()` graph traversal | Domain Models (`Rig`) | — | Traversal depends only on `signal_chain` and `devices` |
| `scenes` ownership | Controller device node | `Rig` compat shim (Phase 3 only) | D-05: scenes belong to Controller |
| `DevicePlugin` Protocol definition | Engine (`engine/plugin.py`) | — | Follows Phase 2 pattern from `ports.py` |
| `PluginContext` dataclass | Engine (`engine/plugin.py`) | — | Dataclass, not Pydantic; same pattern as `ApplyContext` |
| `PluginRegistry` | Engine (`engine/plugin_registry.py`) | — | Dict-dispatch wrapper; empty in Phase 3 |
| YAML loading of Controller-as-device | Config Loader (`config/loader.py`) | — | Sole owner of YAML→model translation |
| Test fixture YAML | `tests/fixtures/sample_rig/` | — | Source of truth for new layout; updated first |

---

## Standard Stack

No new external packages are added in Phase 3. All work uses the existing stack:

| Library | Current Version | Role in Phase 3 |
|---------|----------------|-----------------|
| `pydantic>=2.0` | in use | Discriminated union extension for `ControllerConfig`; `scenes` field on Controller device model |
| `pytest` | in use | All new models and `apply_order()` need unit tests |

**No `npm install` / `pip install` needed.** [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

Not applicable — Phase 3 installs no external packages.

---

## Architecture Patterns

### Current State Diagram (before Phase 3)

```
Rig
├── devices: dict[str, Device]   ← signal-chain members
├── controller: Controller | None ← separate type, NOT a Device
├── scenes: dict[str, Scene]      ← owned by Rig
└── signal_chain: list[SignalChainPosition]

Controller (separate Pydantic model)
└── config: MC6Config

Device
└── config: ManualConfig | MidiConfig | ChaseBlissConfig  ← discriminated union
```

### Target State Diagram (after Phase 3)

```
Rig
├── devices: dict[str, Device]     ← includes Controller device node
├── signal_chain: list[SignalChainPosition]
├── [scenes property SHIM → controller.scenes]  ← compat bridge, Phase 4 removes it
└── apply_order() → list[Device]   ← DFS from Controller root

Device (extended)
└── config: ManualConfig | MidiConfig | ChaseBlissConfig | ControllerConfig  ← union gains controller

ControllerConfig (new, in DeviceConfig union)
├── type: Literal["controller"] = "controller"
├── midi_channel: int = 1
├── banks: list[dict] = []         ← MC6 bank definitions (moved from MC6Config)
└── scenes: dict[str, Scene] = {}  ← moved from Rig

engine/plugin.py (new)
├── PluginContext: dataclass(state, rig, dry_run)
└── DevicePlugin: Protocol(plan, diff, apply)

engine/plugin_registry.py (new)
└── PluginRegistry: empty, wirable registry
```

### Recommended Project Structure Changes

```
src/rig/
  models/
    device.py          — DeviceType gains CONTROLLER; ControllerConfig joins union
    controller.py      — Kept as thin re-export shim for backward compat
    rig.py             — apply_order() added; scenes compat property added
    scene.py           — Unchanged
    signal_chain.py    — Unchanged
  engine/
    plugin.py          — NEW: DevicePlugin Protocol + PluginContext dataclass
    plugin_registry.py — NEW: PluginRegistry (empty)
  config/
    loader.py          — Updated: load Controller from devices/ dir as Device
tests/
  fixtures/
    sample_rig/
      devices/
        mc6.yaml       — NEW: Controller defined as a device here
        hx-stomp.yaml  — Unchanged
        mood.yaml      — Unchanged
      controller.yaml  — REMOVED (Controller moves into devices/)
      scenes/          — Unchanged
```

---

## File-by-File Current State and Required Changes

### 1. `src/rig/models/device.py` — Current State

```python
class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"

# DeviceConfig union:
config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]
```

**Required changes:**
- Add `CONTROLLER = "controller"` to `DeviceType`
- Add `ControllerConfig` class with `type: Literal["controller"] = "controller"`, `midi_channel: int = 1`, `banks: list[dict] = []`, `scenes: dict[str, Scene] = {}`
- Extend `Device.config` discriminated union: `ManualConfig | MidiConfig | ChaseBlissConfig | ControllerConfig`

**Import concern:** `ControllerConfig` needs `Scene` from `models/scene.py`. `device.py` currently imports only from `models/preset.py`. Adding `from rig.models.scene import Scene` is safe — `scene.py` has no imports from `device.py`.

**Where to put `ControllerConfig`:** Put it in `device.py` directly (not in `controller.py`) since it's part of the union defined there. The existing `controller.py` becomes a re-export file.

### 2. `src/rig/models/controller.py` — Current State

```python
class ControllerType(StrEnum):
    MC6 = "mc6"

class MC6Config(BaseModel):
    type: Literal["mc6"] = "mc6"
    midi_channel: int = 1
    banks: list[dict[str, Any]] = []

class Controller(BaseModel):
    id: str; manufacturer: str; model: str; type: ControllerType; config: MC6Config
```

**Required changes:**

`ControllerType` and `MC6Config` are referenced in `tests/test_mc6_generator.py` and `tests/test_models.py`. Two options:

- **Option A (recommended):** Keep `controller.py` with backward-compat re-exports. `ControllerType` becomes a deprecated alias (it's still valid as `mc6` is still a Controller type). `MC6Config` can be kept as-is or aliased to `ControllerConfig`. The old `Controller` model is kept as-is or made an alias for building a `Device` with `type=DeviceType.CONTROLLER`. This minimizes test churn.
- **Option B:** Delete `controller.py` entirely, update all test imports. More invasive; deferred to Phase 4 when test rewrites happen anyway.

**Recommendation:** Option A — preserve `controller.py` as a compat re-export module. The `Controller` class can remain for the `test_mc6_generator.py` fixture builder; the loader stops using it internally.

### 3. `src/rig/models/rig.py` — Current State

```python
class Rig(BaseModel):
    controller: Controller | None = None
    scenes: dict[str, Scene] = {}
    # ...
```

**Required changes:**

1. Remove `controller: Controller | None = None` field (Controller is now in `devices` dict)
2. Remove `scenes: dict[str, Scene] = {}` field (scenes move to `ControllerConfig`)
3. Add `scenes` compat property: returns `rig.controller_device.config.scenes` when a `CONTROLLER`-type device exists, else `{}`
4. Add `controller` compat property: returns the first `Device` with `type == DeviceType.CONTROLLER`, or `None`
5. Add `apply_order() -> list[Device]` method

**`apply_order()` algorithm:**

```python
def apply_order(self) -> list[Device]:
    """DFS from Controller root; children in signal-chain order."""
    controller = self._find_controller()
    if controller is None:
        # No controller: return devices in signal-chain order
        return [self.devices[pos.device_ref]
                for pos in sorted(self.signal_chain, key=lambda p: p.position)
                if pos.device_ref in self.devices]

    # Build signal-chain order index
    chain_order = {
        pos.device_ref: pos.position
        for pos in self.signal_chain
    }

    # Children = all non-controller devices, sorted by chain position
    children = sorted(
        [d for d in self.devices.values() if d.type != DeviceType.CONTROLLER],
        key=lambda d: chain_order.get(d.id, 999)
    )

    # DFS: children first, then controller (controller applies last — it sends PCs)
    return children + [controller]
```

This matches D-03: "DFS from the Controller root; children visited in signal chain order." The Controller applies last because it sends PC messages to the child devices after they are individually configured. [ASSUMED — the exact ordering (children before or after controller) should be confirmed with the user if it matters for Phase 3 correctness, but "children first, controller last" matches the domain description of controller-as-orchestrator.]

**Import changes:** Remove `from rig.models.controller import Controller`. Retain import of `Device` and `DeviceType` (already imported via `device.py`).

### 4. `src/rig/config/loader.py` — Current State

The loader has two distinct paths:

**Path A (current — `controller.yaml` exists):**
```python
controller_path = _resolve(root, "controller.yaml")
if controller_path.exists():
    mc6_data = _read_yaml(controller_path) or {}
    controller: Controller | None = Controller(**mc6_data) if mc6_data else None
    devices, _ = _load_devices_dir(devices_dir, {})
```

**Path B (legacy — `mc6.yaml` exists):**
```python
mc6_data = _read_yaml(mc6_path) if mc6_path.exists() else {}
devices, controller = _load_devices_dir(devices_dir, mc6_data)
```

The `_load_devices_dir` function checks `if data.get("type") == "controller"` to route controller YAML entries — but this currently builds a `Controller` object via `_parse_controller_legacy`, not a `Device`.

**Required changes:**

1. `_load_devices_dir`: When a device YAML has `type == "controller"` (or `type == DeviceType.CONTROLLER`), parse it as a `Device` using the existing `_parse_device` function (which calls `Device(**data)`). Remove the `_parse_controller_legacy` path.

2. `load_rig()`: Remove the `controller_path` / `mc6_path` separate loading logic. Instead, rely on `_load_devices_dir` to pick up the controller from `devices/mc6.yaml` (or whatever file is named). The `controller.yaml` top-level file is no longer used.

3. `Rig(...)` construction: Remove `controller=controller` and `scenes=scenes` fields. Controller is now in `devices`. Scenes are in `ControllerConfig`. But `_load_scenes` still loads scene YAML files and must inject them into the Controller device's config.

**Scene injection pattern:** After loading devices and scenes from their respective directories:
```python
scenes = _load_scenes(scenes_dir)
# Find the controller device and inject scenes into its config
for device_id, device in devices.items():
    if device.type == DeviceType.CONTROLLER:
        updated_config = device.config.model_copy(update={"scenes": scenes})
        devices[device_id] = device.model_copy(update={"config": updated_config})
        break
```

4. `_validate_references`: Currently reads `rig.scenes` and `rig.controller.id` directly. Must be updated to use the compat properties. With the compat shim on `Rig`, this may require no changes to `_validate_references` itself.

5. Imports: Remove `from rig.models.controller import Controller, ControllerType, MC6Config`.

### 5. `src/rig/engine/plugin.py` — New File

Pattern: exactly follows `src/rig/engine/appliers/base.py` and `src/rig/engine/ports.py`.

```python
"""DevicePlugin Protocol and PluginContext for the plugin architecture.

Phase 3: Protocol and context defined; no appliers registered yet (Phase 4).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rig.engine.state import RigState
    from rig.models.device import Device
    from rig.models.rig import Rig


@dataclass
class PluginContext:
    state: RigState
    rig: Rig
    dry_run: bool


class DevicePlugin(Protocol):
    def plan(self, device: Device, ctx: PluginContext) -> object: ...
    def diff(self, device: Device, ctx: PluginContext) -> object: ...
    def apply(self, device: Device, ctx: PluginContext) -> object: ...
```

`PluginContext` is a dataclass (not Pydantic) — same pattern as `ApplyContext`. [VERIFIED: codebase inspection of `base.py`]

The return type of the three Protocol methods is left as `object` in Phase 3 since the consuming engine is Phase 4 work. The planner can use a more specific type if desired but `object` is the minimally-correct choice that satisfies the Protocol without locking in a return shape that Phase 4 might need to change.

### 6. `src/rig/engine/plugin_registry.py` — New File

Pattern: mirrors `registry.py` but is empty (no appliers registered in Phase 3).

```python
"""PluginRegistry — maps device config type strings to DevicePlugin implementations.

Phase 3: Registry is wirable but empty. Appliers are registered in Phase 4.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rig.engine.plugin import DevicePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DevicePlugin] = {}

    def register(self, config_type: str, plugin: DevicePlugin) -> None:
        self._plugins[config_type] = plugin

    def get(self, config_type: str) -> DevicePlugin | None:
        return self._plugins.get(config_type)


# Module-level singleton, following registry.py pattern
_registry = PluginRegistry()
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Discriminated union routing | Custom `isinstance` dispatch | Pydantic `discriminator="type"` | Already the project pattern; Pydantic handles validation |
| Protocol structural subtyping | ABC inheritance | `class Foo(Protocol)` | Project constraint in CLAUDE.md |
| YAML round-trip of new config | Custom serializer | Pydantic `model_dump()` / `model_validate()` | Already handles all model types |
| Graph traversal with cycle detection | Custom graph library | Simple DFS with visited set | Phase 3 is a tree (no cycles), DFS is 10 lines |

---

## `rig.scenes` Access Inventory — Complete Map

This is the most critical risk area. Every caller of `rig.scenes` must either:
(a) work through the compat shim on `Rig` (Phase 3 path), or
(b) be migrated to `rig.controller_device.config.scenes` (Phase 4 path)

| Location | Access Pattern | Phase 3 Action |
|----------|---------------|----------------|
| `engine/diff.py:25` | `config.scenes.items()` | Compat shim covers it |
| `engine/plan/compute.py:69` | `rig.scenes.items()` | Compat shim covers it |
| `engine/plan/compute.py:85` | `len(rig.scenes)` | Compat shim covers it |
| `engine/plan/compute.py:94` | `rig.scenes.items()` | Compat shim covers it |
| `engine/appliers/mc6.py:62` | `ctx.rig.scenes.get(...)` | Compat shim covers it |
| `cli/commands/validate.py:37,43` | `len(rig.scenes)` | Compat shim covers it |
| `cli/commands/status.py:46` | `list(rig.scenes.keys())` | Compat shim covers it |
| `generators/mc6_presets.py:33` | `rig.scenes` | Compat shim covers it |

**`rig.controller` access inventory:**

| Location | Access Pattern | Phase 3 Action |
|----------|---------------|----------------|
| `engine/apply.py:189-190` | `rig.controller.config.banks` | Compat property on `Rig` covering controller device |
| `models/rig.py:52` | `self.controller.config.banks` (in `mc6` property) | Update `mc6` property to use compat controller |

**Recommended compat shim on `Rig`:**

```python
@property
def _controller_device(self) -> Device | None:
    """Return the Controller device node, or None."""
    for d in self.devices.values():
        if d.type == DeviceType.CONTROLLER:
            return d
    return None

@property
def scenes(self) -> dict[str, Scene]:
    """Backward-compat: returns scenes from Controller device config."""
    ctrl = self._controller_device
    if ctrl and isinstance(ctrl.config, ControllerConfig):
        return ctrl.config.scenes
    return {}

@property
def controller(self) -> Device | None:
    """Backward-compat: returns Controller device node."""
    return self._controller_device
```

Note: `Rig.controller` compat property now returns `Device | None` instead of `Controller | None`. The type narrows to `Device` with `type == CONTROLLER`. Callers that access `rig.controller.config.banks` will still work because `ControllerConfig` has a `banks` field. [VERIFIED: design follows from D-04 which states Controller config joins the DeviceConfig union]

---

## Test Impact Analysis

### Tests that BREAK without changes

| Test File | Test Name | Why It Breaks | Fix |
|-----------|-----------|--------------|-----|
| `test_models.py:TestRigConfig::test_rig_config_with_scenes` | Constructs `Rig(scenes={...})` directly | `Rig` no longer has `scenes` field | Construct via Controller device in `devices` dict, or update to use compat shim |
| `test_mc6_generator.py` (all) | `_make_rig()` passes `controller=controller` to `Rig(...)` | `Rig` no longer has `controller` field | Update `_make_rig()` to put Controller in `devices` dict |
| `test_models.py:TestPedalModels::test_controller_type_enum_values` | `from rig.models.controller import ControllerType` | OK if re-export preserved in `controller.py` | Keep re-export; no change needed |
| `test_loader.py::test_loads_scenes` | `assert "billy-clean" in config.scenes` | Works if compat shim is in place | Shim covers it |

### Tests that need loader fixture update

The `rig_dir` fixture in `test_loader.py` uses the old `pedals/` layout with no controller. It does not test controller loading. The `sample_rig/` fixture in `tests/fixtures/` currently has `controller.yaml` at the top level. After Phase 3, `controller.yaml` should be replaced by `devices/mc6.yaml` with `type: controller`.

**New `tests/fixtures/sample_rig/devices/mc6.yaml`:**
```yaml
id: mc6
manufacturer: Morningstar
model: MC6
type: controller
config:
  type: controller
  midi_channel: 1
  banks:
    - bank: 1
      name: Bank 1
      switches:
        A:
          scene: lead
```

**`tests/fixtures/sample_rig/controller.yaml` — DELETE** (no longer used).

### New tests required

| Test | Location | What It Verifies |
|------|----------|-----------------|
| `test_apply_order_no_controller` | `test_models.py` | Returns devices in signal-chain order when no controller |
| `test_apply_order_with_controller` | `test_models.py` | Returns children first (chain order), controller last |
| `test_controller_device_type` | `test_models.py` | `DeviceType.CONTROLLER` exists and has value `"controller"` |
| `test_controller_config_in_union` | `test_models.py` | Device with `type: controller` config parses via discriminated union |
| `test_rig_scenes_compat_shim` | `test_models.py` | `rig.scenes` returns scenes from Controller device config |
| `test_plugin_context_fields` | new `test_plugin.py` | `PluginContext` is a dataclass with correct fields |
| `test_plugin_registry_register_get` | new `test_plugin.py` | `PluginRegistry.register()` and `.get()` work |
| `test_plugin_registry_empty` | new `test_plugin.py` | `.get()` returns `None` for unregistered type |
| `test_loader_loads_controller_as_device` | `test_loader.py` | Loader puts Controller in `devices` dict, scenes on its config |
| `test_loader_scenes_from_controller` | `test_loader.py` | `rig.scenes` works via compat shim after load |

---

## Common Pitfalls

### Pitfall 1: Pydantic Discriminated Union with Forward Reference
**What goes wrong:** Adding `ControllerConfig` to the `Device.config` union requires importing `Scene` in `device.py`. If `Scene` also imports something from `device.py`, Pydantic model rebuild fails with a `PydanticUserError`.
**Root cause:** Circular import via Pydantic's model rebuild at class definition time.
**How to avoid:** Check import chain: `scene.py` → `pydantic` only. No import from `device.py`. Safe to add `from rig.models.scene import Scene` in `device.py`. [VERIFIED: read `scene.py` — only imports `from typing import Literal` and `from pydantic import BaseModel`]
**Warning signs:** `PydanticUserError: A non-annotated attribute was detected` or `ImportError` at module load.

### Pitfall 2: `Rig.scenes` as a Pydantic Field vs Property
**What goes wrong:** If `scenes` is defined as both a Pydantic field (e.g., in `Rig`) and a property, Pydantic 2.x raises `UserWarning: a non-annotated attribute`. In Pydantic v2, `@property` on a `BaseModel` is allowed but must not shadow a declared field.
**Root cause:** Removing the `scenes: dict[str, Scene] = {}` field from `Rig` but adding `@property def scenes(...)` works fine — the property replaces the field entirely.
**How to avoid:** Remove the field declaration when adding the property. [VERIFIED: Pydantic v2 allows properties on BaseModel when no field of the same name exists]

### Pitfall 3: `controller.yaml` Still Present in Fixtures
**What goes wrong:** `loader.py` currently checks `if controller_path.exists()` first. If `controller.yaml` remains in fixtures after the loader logic is updated, the old path silently wins and the Controller-as-device path never executes.
**Root cause:** The fixture and loader change must be coordinated.
**How to avoid:** Delete `tests/fixtures/sample_rig/controller.yaml` in the same task that updates `loader.py`. Run the fixture-loading tests before and after.

### Pitfall 4: `rig.controller` Return Type Change
**What goes wrong:** `engine/apply.py:189` does `rig.controller.config.banks`. After Phase 3, `rig.controller` returns `Device | None` instead of `Controller | None`. If Pydantic's type narrowing or a `mypy` check relies on the old type, it can surface as a runtime error or type error.
**Root cause:** The `controller` compat property on `Rig` changes return type.
**How to avoid:** Add an `isinstance(ctrl.config, ControllerConfig)` guard inside the compat property before returning, and ensure all access through the property gets `ControllerConfig` (which has `banks`). [ASSUMED — mypy is not currently configured in this project, but adding the guard is defensive and correct regardless]

### Pitfall 5: `_load_devices_dir` Still Calls `_parse_controller_legacy`
**What goes wrong:** If `_load_devices_dir` still routes `type == "controller"` through the legacy path, the new `devices/mc6.yaml` with `type: controller` will silently build a `Controller` object instead of a `Device`.
**Root cause:** The old routing logic in `_load_devices_dir`.
**How to avoid:** Remove the `if data.get("type") == "controller": _parse_controller_legacy(...)` branch entirely. Let `_parse_device` handle all YAML including `type: controller` (Pydantic discriminator handles it).

---

## Architecture Patterns

### Pattern 1: Adding a Member to a Pydantic Discriminated Union
**What:** Add `ControllerConfig` to `Device.config` union by adding the type to the `Annotated` union.
**When to use:** Any new Device configuration strategy.
**Example (from existing codebase):**
```python
# Before (device.py line 86):
config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]

# After:
config: Annotated[
    ManualConfig | MidiConfig | ChaseBlissConfig | ControllerConfig,
    Field(discriminator="type")
]
```
The YAML `config: {type: controller, ...}` will then deserialize to `ControllerConfig` automatically. [VERIFIED: codebase inspection of existing union pattern]

### Pattern 2: Protocol with TYPE_CHECKING Guard
**What:** `DevicePlugin` Protocol with forward references to avoid circular imports.
**When to use:** Any new Protocol that references domain models.
**Example (from `base.py` and `ports.py`):**
```python
from __future__ import annotations
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rig.engine.state import RigState
    from rig.models.device import Device
    from rig.models.rig import Rig
```
[VERIFIED: codebase inspection of `base.py` lines 1-14]

### Pattern 3: model_copy for Immutable Updates on Pydantic Models
**What:** Use `device.model_copy(update={...})` to create updated copies of Pydantic models without mutation.
**When to use:** Scene injection into ControllerConfig; any loader transformation.
**Example (from `loader.py`):**
```python
device = device.model_copy(update={"presets": presets})
```
[VERIFIED: codebase inspection of `loader.py`]

### Anti-Patterns to Avoid

- **Don't mutate Pydantic model fields directly:** `device.config.scenes["x"] = ...` will fail in Pydantic v2 by default (models are immutable). Use `model_copy(update=...)`.
- **Don't add `model_config = {"arbitrary_types_allowed": True}`:** This is not needed here; all types are Pydantic-compatible.
- **Don't put scene injection logic in `Rig.__init__` or a model validator:** Scene injection belongs in the loader, not the domain model. Domain models are pure data.
- **Don't register any appliers in `PluginRegistry` during Phase 3:** D-10 is explicit that the registry is empty in Phase 3.

---

## Recommended Task Ordering (Waves)

**Wave 0 — Test infrastructure**
1. Create `tests/fixtures/sample_rig/devices/mc6.yaml` (Controller-as-device fixture)
2. Delete `tests/fixtures/sample_rig/controller.yaml`
3. Verify existing fixture-based tests still pass (they use `sample_rig/` for doc tests, not for `test_loader.py` which uses `tmp_path`)

**Wave 1 — Model layer (no loader, no test changes yet)**
1. Add `CONTROLLER = "controller"` to `DeviceType` in `device.py`
2. Add `ControllerConfig` class in `device.py` (fields: `type`, `midi_channel`, `banks`, `scenes`)
3. Extend `Device.config` union to include `ControllerConfig`
4. Update `controller.py` as backward-compat re-export (keep `ControllerType`, `MC6Config`, `Controller` for test compat)
5. Run `test_models.py` — should pass with one new test to add (`test_controller_device_type`, `test_controller_config_in_union`)

**Wave 2 — `Rig` model update**
1. Remove `controller: Controller | None` and `scenes: dict[str, Scene]` Pydantic fields from `Rig`
2. Add `_controller_device`, `controller`, `scenes` compat properties
3. Add `apply_order()` method
4. Update `rig.py` imports (remove `Controller` import)
5. Run `test_models.py` — fix `test_rig_config_with_scenes` (now builds scene via Controller device)
6. Run `test_mc6_generator.py` — fix `_make_rig()` fixture to put Controller in `devices` dict
7. Run `test_plan.py`, `test_diff.py` — compat shim should make these pass unchanged

**Wave 3 — Loader update**
1. Update `load_rig()` to remove `controller_path`/`mc6_path` logic and `scenes` direct field
2. Update `_load_devices_dir()` to route `type: controller` → `_parse_device()` (not legacy)
3. Remove `_parse_controller_legacy()` or leave as dead code with a `# TODO: remove` marker
4. Add scene injection after loading devices and scenes
5. Remove `Controller, ControllerType, MC6Config` imports from `loader.py`
6. Run `test_loader.py` — fix `rig_dir` fixture if needed, add new Controller-as-device tests
7. Run `test_cli.py` — compat shim covers `rig.scenes` in CLI commands

**Wave 4 — Plugin scaffold (independent of waves 1-3)**
1. Create `src/rig/engine/plugin.py` with `PluginContext` and `DevicePlugin`
2. Create `src/rig/engine/plugin_registry.py` with `PluginRegistry` and `_registry` singleton
3. Create `tests/test_plugin.py` with tests for registry and context
4. Run full suite — all 167+ tests should pass

---

## State of the Art

| Old Approach | Current Approach | Relevance |
|--------------|------------------|-----------|
| `Controller` as peer class to `Device` | `Controller` as a `Device` with `type=CONTROLLER` | Core Phase 3 change |
| `Rig.scenes` as top-level field | `scenes` on `ControllerConfig` inside a `Device` node | Core Phase 3 change |
| `_load_devices_dir` routes controller to legacy parser | `_parse_device()` handles all types via union | Loader simplification |
| No plugin protocol in engine | `DevicePlugin` Protocol in `engine/plugin.py` | Phase 3 scaffold |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `apply_order()` returns children first (signal-chain order), then Controller last | `Rig` model changes | If Controller should be first (unlikely given "it orchestrates/sends PC"), the DFS order needs reversing |
| A2 | `DevicePlugin` Protocol methods return `object` in Phase 3 | `plugin.py` design | If Phase 4 needs a specific return type declared now, an additional type needs defining in Phase 3 |
| A3 | `mypy` is not configured; type annotation mismatches will not block tests | Pitfall 4 | If strict mypy checking is added in Phase 3, the `rig.controller` return type change may surface errors |
| A4 | `controller.py` is kept as re-export shim rather than deleted | `controller.py` changes | If the planner decides to delete it, `test_mc6_generator.py` and `test_models.py` need import updates |

---

## Open Questions

1. **`apply_order()` child ordering when device is in both signal chain and NOT in signal chain**
   - What we know: `apply_order()` sorts by `signal_chain` position
   - What's unclear: If a device is in `devices` but NOT in `signal_chain`, should it appear in `apply_order()` output? The current signal chain in the sample rig excludes the MC6 controller.
   - Recommendation: Devices not in the signal chain should still appear (appended after chain-ordered devices), sorted by dict insertion order. The Controller always goes last regardless.

2. **`_make_rig()` in `test_mc6_generator.py` passes `controller=controller` and `scenes={...}` separately to `Rig`**
   - What we know: After Wave 2, `Rig` will no longer accept these fields.
   - What's unclear: The test will need to put the controller in `devices` and put `scenes` in its `ControllerConfig` instead.
   - Recommendation: This is a known Wave 2 fix. The planner should include a task to update `test_mc6_generator.py`'s `_make_rig()` as part of Wave 2.

3. **Scenes directory still exists and is loaded separately — should `_load_scenes` disappear?**
   - What we know: YAML scene files are still in `scenes/` directory. The loader currently reads them, then the compat bridge needs to inject them into the Controller's config.
   - What's unclear: Should `scenes/` YAML files be eliminated in favor of inline scenes in `devices/mc6.yaml`?
   - Recommendation: Keep `scenes/` YAML files and the `_load_scenes` function for Phase 3. The injection pattern (load scenes from files, inject into Controller config) is the right bridge. Consolidation is a future concern.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 3 is purely code refactoring with no external tool dependencies beyond the existing Python/uv/pytest stack.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (in `pyproject.toml` dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_models.py tests/test_loader.py tests/test_plan.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

**Baseline:** 167 tests passing before Phase 3 begins. [VERIFIED: ran test suite]

### Phase Requirements → Test Map

| Behavior | Test Type | Command | Notes |
|----------|-----------|---------|-------|
| `DeviceType.CONTROLLER` exists | unit | `pytest tests/test_models.py -k controller_device_type` | New test |
| `ControllerConfig` parses via discriminated union | unit | `pytest tests/test_models.py -k controller_config` | New test |
| `Rig.apply_order()` — no controller | unit | `pytest tests/test_models.py -k apply_order_no_controller` | New test |
| `Rig.apply_order()` — with controller | unit | `pytest tests/test_models.py -k apply_order_with_controller` | New test |
| `Rig.scenes` compat shim | unit | `pytest tests/test_models.py -k scenes_compat` | New test |
| `PluginContext` dataclass fields | unit | `pytest tests/test_plugin.py` | New file |
| `PluginRegistry` register/get | unit | `pytest tests/test_plugin.py` | New file |
| Loader puts Controller in `devices` dict | unit | `pytest tests/test_loader.py -k controller_as_device` | New test |
| Full regression — all existing tests | integration | `uv run pytest tests/ -q` | Must remain 167+ passing |

### Wave 0 Gaps
- [ ] `tests/test_plugin.py` — covers `PluginContext` and `PluginRegistry`

*(All other tests build on existing `test_models.py` and `test_loader.py` — extend in place)*

---

## Security Domain

Phase 3 is a pure domain refactor — no authentication, session management, input from external sources, or cryptography involved. No ASVS categories apply. ASVS V5 (Input Validation) is nominally touched by the YAML loader, but the loader already uses `yaml.safe_load()` (not `yaml.load()`) and Pydantic model validation; no changes to that behavior are made in Phase 3.

---

## Sources

### Primary (HIGH confidence)
- Codebase inspection — all source files read directly (`src/rig/models/`, `src/rig/config/loader.py`, `src/rig/engine/`, `tests/`)
- Pydantic v2 discriminated union behavior — verified against existing patterns in `device.py` line 86

### Secondary (MEDIUM confidence)
- Pydantic v2 property-on-BaseModel behavior — verified by project convention; no `model_config` override needed

### Tertiary (LOW confidence / ASSUMED)
- `apply_order()` child-before-controller ordering — derived from domain description in CONTEXT.md but not explicitly stated; flagged as A1

---

## Metadata

**Confidence breakdown:**
- Model layer changes: HIGH — exact current code read; discriminated union pattern already in use
- Loader changes: HIGH — full loader read; two code paths identified
- `apply_order()` algorithm: MEDIUM — algorithm is straightforward but traversal order assumption (children before controller) is flagged ASSUMED
- Plugin scaffold: HIGH — direct copy of established Protocol + dataclass patterns from `ports.py` and `base.py`
- Test impact: HIGH — all test files read; all `rig.scenes` access points catalogued

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable Python project; no fast-moving dependencies)

---

## RESEARCH COMPLETE
