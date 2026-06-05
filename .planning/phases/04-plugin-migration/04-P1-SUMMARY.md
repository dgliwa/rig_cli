---
phase: 4
plan: P1
subsystem: engine/plugin
tags: [plugin-architecture, protocol, dataclass, registry]
dependency_graph:
  requires: []
  provides:
    - Device Protocol (src/rig/engine/plugin.py)
    - DeviceApplyContext dataclass (src/rig/engine/plugin.py)
    - PluginRegistry.register_model/get_model (src/rig/engine/plugin_registry.py)
  affects:
    - P2 (concrete device types implement Device Protocol)
    - P3 (loader uses register_model for registry-driven dispatch)
tech_stack:
  added: []
  patterns:
    - Protocol structural subtyping (Device replaces DevicePlugin)
    - dataclass for context objects (DeviceApplyContext)
    - TYPE_CHECKING guard for avoiding circular imports
key_files:
  created: []
  modified:
    - src/rig/engine/plugin.py
    - src/rig/engine/plugin_registry.py
    - tests/test_plugin.py
decisions:
  - "Device Protocol uses properties (id, name, config) instead of passing device as method arg — device IS the protocol instance per D-01"
  - "DeviceApplyContext mirrors ApplyContext from appliers/base.py but adds action field for the target preset; both coexist during migration"
  - "PluginRegistry grows register_model/get_model independently from register/get to support P3 loader dispatch without breaking P2 plugin registration"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-05"
  tasks_completed: 3
  files_modified: 3
---

# Phase 4 Plan P1: Device Protocol Foundation Summary

**One-liner:** Device Protocol with id/name/config properties replaces DevicePlugin; DeviceApplyContext dataclass added for apply-time context; PluginRegistry gains model-class registration for P3 loader dispatch.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for Device Protocol + DeviceApplyContext + register_model | 7d0fc71 | tests/test_plugin.py |
| GREEN T1+T2+T3 | Device Protocol, DeviceApplyContext, PluginRegistry.register_model | ffc4870 | src/rig/engine/plugin.py, src/rig/engine/plugin_registry.py |

## What Was Built

### Task 1: Replace DevicePlugin with Device Protocol

`src/rig/engine/plugin.py` now defines `Device` as a `typing.Protocol` with:
- Properties: `id: str`, `name: str`, `config: Any`
- Methods: `plan(ctx: PluginContext) -> object`, `diff(ctx: PluginContext) -> object`, `apply(ctx: DeviceApplyContext) -> object`

The old `DevicePlugin` Protocol (which took `device` as a separate argument to each method) is removed. Concrete device types will BE the protocol instance — the device object itself carries state and behavior.

### Task 2: Add DeviceApplyContext dataclass

`DeviceApplyContext` is a `@dataclass` in `plugin.py` with all 8 fields:
- Required: `action: DeviceAction`, `state: RigState`, `rig: Rig`, `dry_run: bool`, `confirmation_io: ConfirmationIO`
- Optional: `midi: MidiManager | None = None`, `connected_devices: set[str] = field(default_factory=set)`, `config_path: str | None = None`

All imports for external types (`DeviceAction`, `ConfirmationIO`, `MidiManager`, `Rig`) are guarded under `TYPE_CHECKING` to avoid circular imports at runtime.

### Task 3: Extend PluginRegistry with model-class registration

`PluginRegistry` gains `register_model(config_type, model_class)` and `get_model(config_type)` backed by a separate `_model_classes` dict. These are independent from `register/get` — the loader (P3) will call `get_model` for YAML dispatch while P2 registers concrete `Device` instances via `register`.

## Verification

- `python -c "from rig.engine.plugin import Device, DeviceApplyContext, PluginContext"` exits 0
- `python -c "from rig.engine.plugin_registry import PluginRegistry; r = PluginRegistry(); r.register_model('midi', object); assert r.get_model('midi') is object"` exits 0
- `uv run pytest tests/test_plugin.py -v` — 25 passed
- `uv run pytest tests/ -q` — 208 passed (full suite)
- No `DevicePlugin` class in plugin.py (only mention is in docstring noting its removal)

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

1. RED gate commit: `7d0fc71` — `test(04-P1): add failing tests for Device Protocol and DeviceApplyContext`
2. GREEN gate commit: `ffc4870` — `feat(04-P1): replace DevicePlugin with Device Protocol, add DeviceApplyContext`

Both gates satisfied.

## Self-Check: PASSED

- [x] `src/rig/engine/plugin.py` contains `class Device(Protocol)`
- [x] `src/rig/engine/plugin.py` contains `class DeviceApplyContext`
- [x] `src/rig/engine/plugin_registry.py` contains `register_model`
- [x] `tests/test_plugin.py` has 25 tests, all passing
- [x] Commit `7d0fc71` exists (RED gate)
- [x] Commit `ffc4870` exists (GREEN gate)
