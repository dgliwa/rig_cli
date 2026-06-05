---
phase: 03-core-domain-refactor
verified: 2026-06-05T17:14:12Z
status: passed
score: 18/18
overrides_applied: 0
re_verification: false
---

# Phase 3: Core Domain Refactor — Verification Report

**Phase Goal:** Refactor domain model — Controller becomes a first-class Device, Rig gains apply_order(), loader drops legacy controller path, DevicePlugin Protocol scaffold established.
**Verified:** 2026-06-05T17:14:12Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

#### P1 Truths (Controller-as-Device Model)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DeviceType.CONTROLLER exists with value 'controller' | VERIFIED | `DeviceType.CONTROLLER.value == "controller"` confirmed via runtime check |
| 2 | ControllerConfig parses via the DeviceConfig discriminated union | VERIFIED | Device(config={'type':'controller',...}) resolves to ControllerConfig instance |
| 3 | Device with type=controller round-trips through Pydantic | VERIFIED | JSON round-trip shows config.type == "controller" |
| 4 | controller.py re-exports ControllerType, MC6Config, Controller for backward compat | VERIFIED | `from rig.models.device import ControllerConfig as ControllerConfig` present; ControllerType, MC6Config, Controller class all still defined |
| 5 | tests/fixtures/sample_rig/devices/mc6.yaml exists with type: controller; controller.yaml deleted | VERIFIED | mc6.yaml exists with correct content; controller.yaml absent from fixture directory |

#### P2 Truths (Rig Device-Graph Model)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Rig no longer has controller or scenes as Pydantic fields | VERIFIED | `Rig.model_fields` = ['name', 'description', 'signal_chain', 'devices', 'midi_channel'] — no controller or scenes |
| 7 | Rig.scenes property returns scenes from ControllerConfig when CONTROLLER device exists | VERIFIED | `rig.scenes` returns `{'s1': ...}` when CONTROLLER device with scenes is in devices |
| 8 | Rig.controller property returns Device with type==CONTROLLER, or None | VERIFIED | Returns Device or None depending on devices dict content |
| 9 | Rig.apply_order() returns non-controller devices in signal-chain order, then controller last | VERIFIED | `apply_order: ['hx-stomp', 'mc6']` with hx at position 1, mc6 as controller |
| 10 | Rig.apply_order() with no controller returns devices sorted by signal-chain position | VERIFIED | Two devices at positions 1 and 2 returned in ascending order |
| 11 | All existing tests pass including test_mc6_generator.py after _make_rig() update | VERIFIED | 195 passed in 0.41s |

#### P3 Truths (Loader Legacy Cleanup)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 12 | loader.py routes controller YAML through _parse_device (not legacy controller path) | VERIFIED | `_parse_device(data)` handles all YAML types; `_load_devices_dir` returns `dict[str, Device]` |
| 13 | load_rig() no longer passes controller= or scenes= to Rig constructor | VERIFIED | `Rig(name=..., description=..., midi_channel=..., signal_chain=chain, devices=devices)` — no controller= or scenes= |
| 14 | Scenes injected into Controller device's ControllerConfig after loading | VERIFIED | `device.config.model_copy(update={"scenes": scenes})` wiring present in loader.py lines 199-201 |
| 15 | _parse_controller_legacy is removed; no Controller/ControllerType/MC6Config imports in loader | VERIFIED | Imports confirm only `ControllerConfig, Device, DeviceType` from device module; no legacy imports |
| 16 | test_loader.py has controller-as-device tests | VERIFIED | `test_loads_controller_as_device` and `test_scenes_accessible_via_controller` both present and passing |

#### P4 Truths (Plugin Protocol Scaffold)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 17 | DevicePlugin is a Protocol class with plan, diff, and apply methods; PluginContext is a dataclass with exactly three fields: state, rig, dry_run | VERIFIED | `DevicePlugin` inherits from `Protocol`; `dataclasses.fields(PluginContext)` == `['state', 'rig', 'dry_run']` |
| 18 | PluginRegistry has register/get; get() returns None for unregistered types; no appliers registered in Phase 3; both files use TYPE_CHECKING guard | VERIFIED | `PluginRegistry().get('unknown') == None`; fresh registry returns None for manual/midi/chase_bliss; TYPE_CHECKING guard confirmed in both plugin.py and plugin_registry.py |

**Score:** 18/18 truths verified

### Roadmap Success Criteria Coverage

| SC | Criterion | Status | Evidence |
|----|-----------|--------|----------|
| SC1 | A DeviceGraph type models devices as nodes with directed edges; Controller is root-node subtype owning scenes | VERIFIED (via design decision D-01) | PATTERNS.md D-01 explicitly resolved: "Rig IS the DeviceGraph — no separate DeviceGraph type." Rig has devices (nodes), apply_order() (traversal), CONTROLLER device owns scenes via ControllerConfig. Device can satisfy both signal-chain and scene-referenced roles (verified by runtime check). |
| SC2 | DevicePlugin protocol defines plan/diff/apply — no plan/diff/apply behavior lives on domain models | VERIFIED | DevicePlugin Protocol exists in plugin.py. Domain models have no plan/diff/apply methods — only compat properties and apply_order() ordering utility as specified in D-03. |
| SC3 | PluginRegistry maps config type strings to DevicePlugin; existing appliers not yet migrated | VERIFIED | PluginRegistry exists, empty by default. No appliers registered in Phase 3. |
| SC4 | All existing tests pass; loader produces new graph structure from existing YAML | VERIFIED | 195 passed; loader spot-check produces controller device correctly from YAML. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/rig/models/device.py` | DeviceType.CONTROLLER + ControllerConfig + extended discriminated union | VERIFIED | Contains CONTROLLER enum value, ControllerConfig class, union includes ControllerConfig |
| `src/rig/models/controller.py` | Backward-compat re-exports of ControllerType, MC6Config, Controller | VERIFIED | All three preserved; adds `from rig.models.device import ControllerConfig as ControllerConfig` |
| `tests/fixtures/sample_rig/devices/mc6.yaml` | Controller-as-device fixture YAML with type: controller | VERIFIED | Present with correct content; controller.yaml deleted |
| `src/rig/models/rig.py` | apply_order() method + scenes/controller compat properties | VERIFIED | apply_order(), controller property, scenes property, _controller_device helper all present |
| `tests/test_models.py` | apply_order tests + rig_scenes_compat test | VERIFIED | TestApplyOrder class with 5 tests; TestRigConfig with compat property tests |
| `tests/test_mc6_generator.py` | Updated _make_rig() using DeviceType.CONTROLLER | VERIFIED | _make_rig() builds Device(type=DeviceType.CONTROLLER) with scenes in ControllerConfig |
| `src/rig/config/loader.py` | Updated loader building Controller as Device | VERIFIED | No legacy imports; _load_devices_dir returns dict[str, Device]; scene injection via model_copy |
| `tests/test_loader.py` | Tests for controller-as-device loading and scenes compat | VERIFIED | test_loads_controller_as_device and test_scenes_accessible_via_controller both pass |
| `src/rig/engine/plugin.py` | DevicePlugin Protocol + PluginContext dataclass | VERIFIED | Protocol with plan/diff/apply; dataclass with state/rig/dry_run; TYPE_CHECKING guard |
| `src/rig/engine/plugin_registry.py` | PluginRegistry class (empty registry) | VERIFIED | register()/get() methods; empty by default; TYPE_CHECKING guard |
| `tests/test_plugin.py` | Tests for PluginContext and PluginRegistry | VERIFIED | 13 tests covering fields, instantiation, register/get, overwrite, no-side-effects |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/rig/models/device.py | src/rig/models/scene.py | ControllerConfig.scenes field | PARTIAL | Import NOT present; `scenes: dict[str, Any] = {}` used instead of `dict[str, Scene]`. Functionally correct — loader injects Scene objects and Rig.scenes returns dict[str, Scene] — but type annotation is weaker than planned. |
| src/rig/models/controller.py | src/rig/models/device.py | re-export of ControllerConfig | VERIFIED | `from rig.models.device import ControllerConfig as ControllerConfig` on line 8 |
| src/rig/models/rig.py | src/rig/models/device.py | DeviceType.CONTROLLER + ControllerConfig import | VERIFIED | `from rig.models.device import ControllerConfig, Device, DeviceType` on line 7 |
| Rig.scenes property | ControllerConfig.scenes | rig._controller_device.config.scenes | VERIFIED | `ctrl.config.scenes` returned when isinstance(ctrl.config, ControllerConfig) |
| src/rig/config/loader.py | src/rig/models/device.py | Device(**data) handles type: controller | VERIFIED | `_parse_device` on line 38-40 routes all YAML through Device(**data) |
| src/rig/config/loader.py | src/rig/models/rig.py | Rig() without controller= or scenes= | VERIFIED | Rig constructor call on lines 203-209 has no controller= or scenes= kwargs |
| src/rig/engine/plugin.py | src/rig/engine/state.py | PluginContext.state: RigState (direct import) | VERIFIED | `from rig.engine.state import RigState` on line 11 |
| src/rig/engine/plugin_registry.py | src/rig/engine/plugin.py | TYPE_CHECKING import of DevicePlugin | VERIFIED | `if TYPE_CHECKING: from rig.engine.plugin import DevicePlugin` on lines 10-11 |

### Data-Flow Trace (Level 4)

This phase is a domain model refactor — no rendering of dynamic data to UI. Data-flow applicable to the scene injection path only.

| Data Path | Source | Destination | Produces Real Data | Status |
|-----------|--------|-------------|-------------------|--------|
| YAML files -> Device | `_read_yaml` + `_parse_device` in loader.py | `rig.devices` dict | Real YAML content | FLOWING |
| scenes/ YAML -> ControllerConfig.scenes | `_load_scenes` + `model_copy` in loader.py (lines 197-201) | `ctrl_device.config.scenes` | Real Scene objects from filesystem | FLOWING |
| rig.scenes property | `_controller_device` lookup + `ctrl.config.scenes` return | caller | Actual Scene objects | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| DeviceType.CONTROLLER value | `DeviceType.CONTROLLER.value` | `'controller'` | PASS |
| ControllerConfig round-trip | Device(type=CONTROLLER, config={type:controller,...}) | config type: ControllerConfig | PASS |
| Rig.apply_order() ordering | rig with hx (pos 1) + mc6 (controller) | `['hx-stomp', 'mc6']` | PASS |
| Loader end-to-end | load_rig() with controller device YAML | controller id: mc6, devices: ['mc6'] | PASS |
| DevicePlugin Protocol | `hasattr(DevicePlugin, 'plan/diff/apply')` | True for all three | PASS |
| PluginRegistry empty default | `PluginRegistry().get('unknown')` | None | PASS |
| Full test suite | `uv run pytest tests/ -q` | 195 passed | PASS |

### Probe Execution

No probe files defined for this phase. Step 7c: SKIPPED.

### Requirements Coverage

Phase 3 plans declared no requirement IDs (`requirements: []`). ROADMAP notes `Requirements: TBD (gather in discuss phase)`. No requirement cross-reference to validate.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/rig/models/device.py | 84 | `scenes: dict[str, Any] = {}` instead of `dict[str, Scene]` with `Field(default_factory=dict)` | INFO | P1 plan specified `dict[str, Scene]` and `Field(default_factory=dict)` per threat T-03P1-01. Pydantic v2 handles mutable default isolation automatically (confirmed by test), so no shared-state bug exists. Type annotation is weaker than intended but functionally correct since loader injects Scene objects. |
| src/rig/config/loader.py | 39 | `# TODO:` (empty comment) | INFO | Pre-existing from "add a bunch of TODOs" commit (209b55f). Not introduced by Phase 3. |
| src/rig/config/loader.py | multiple | Multiple `# TODO:` design-note comments | INFO | All pre-existing. None reference unreferenced incomplete work. |

No TBD, FIXME, or XXX markers found in Phase 3 files. No blocker anti-patterns.

### Design Decision Notes

**SC1 "DeviceGraph" wording vs D-01 implementation decision:** ROADMAP SC1 says "A `DeviceGraph` type models devices as nodes with directed edges." PATTERNS.md D-01, the approved implementation decision, says "Rig IS the DeviceGraph — no separate DeviceGraph type. Rig gains graph methods directly." The implementation follows D-01. The DeviceGraph concept from the ROADMAP is realized through Rig with devices (nodes), apply_order() (traversal), and ControllerConfig owning scenes (root-node behavior). Phase 5 SC1 introduces `DeviceGraph.apply_order()` with cycle detection — this is a future enhancement on top of the Phase 3 foundation, not a Phase 3 gap.

**ControllerConfig.scenes type annotation:** P1 plan action specified `dict[str, Scene]` with `from rig.models.scene import Scene` import. The implementation used `dict[str, Any] = {}` (no Scene import in device.py). This is functionally equivalent because: (1) Pydantic v2 isolates mutable defaults automatically; (2) the loader injects `Scene` objects; (3) `Rig.scenes` return type is annotated as `dict[str, Scene]`. Type safety at the ControllerConfig level is weaker than specified, but no runtime behavior differs.

### Human Verification Required

None. All Phase 3 deliverables are verifiable through code inspection and test execution. The phase is a pure domain model and infrastructure refactor with no UI, real-time, or external service components.

---

## Gaps Summary

No gaps found. All 18 must-have truths are VERIFIED, all artifacts are substantive and wired, all 195 tests pass.

The `ControllerConfig.scenes: dict[str, Any]` type annotation is a minor deviation from the P1 plan's specified `dict[str, Scene]` but does not affect any observable truth or runtime behavior. Noted as INFO.

---

_Verified: 2026-06-05T17:14:12Z_
_Verifier: Claude (gsd-verifier)_
