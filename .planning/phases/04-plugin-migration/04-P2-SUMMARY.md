---
phase: 4
plan: P2
subsystem: engine/devices
tags: [plugin-architecture, concrete-device-types, pydantic, registry]
dependency_graph:
  requires:
    - P1 (Device Protocol, DeviceApplyContext, PluginRegistry.register_model)
  provides:
    - AnalogDevice (src/rig/engine/devices.py)
    - MidiDevice (src/rig/engine/devices.py)
    - ChaseBlissDevice (src/rig/engine/devices.py)
    - MC6Device (src/rig/engine/devices.py)
    - default_registry (src/rig/engine/devices.py)
    - get_registry() (src/rig/engine/plugin_registry.py)
  affects:
    - P3 (loader uses default_registry.get_model() for YAML dispatch)
    - P3 (apply.py routes through registry.get(type).apply())
tech_stack:
  added: []
  patterns:
    - Pydantic BaseModel with arbitrary_types_allowed for concrete device types
    - Protocol structural subtyping (Device Protocol satisfied without inheritance)
    - Deferred plan/diff via NotImplementedError (Phase 5 fills in)
    - Lazy import in get_registry() to break circular import cycle
key_files:
  created:
    - src/rig/engine/devices.py
    - tests/test_devices.py
  modified:
    - src/rig/engine/plugin_registry.py
decisions:
  - "Concrete device types are Pydantic BaseModel subclasses with config: Any (arbitrary_types_allowed=True) so tests can pass plain object() as config without type errors"
  - "ChaseBlissDevice.apply() delegates to MidiDevice.apply() — CBA scene switching is a plain PC message; 3-phase setup stays in ChaseBlissApplier for now (D-06 scope)"
  - "default_registry lives in devices.py (not plugin_registry.py) to avoid circular import: devices.py imports PluginRegistry from plugin_registry.py; get_registry() in plugin_registry.py uses a lazy import to return the devices.py default_registry"
  - "MC6Device.apply() uses lazy imports for MC6 SysEx helpers to keep module-level imports clean"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-05"
  tasks_completed: 3
  files_modified: 3
---

# Phase 4 Plan P2: Concrete Device Plugin Types Summary

**One-liner:** Four concrete Device Protocol types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) as Pydantic models migrating applier logic into apply() methods, registered in a module-level default PluginRegistry.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for all four concrete device types + default_registry | ad0d340 | tests/test_devices.py |
| GREEN T1+T2+T3 | AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device + registry | 1d43537 | src/rig/engine/devices.py, src/rig/engine/plugin_registry.py |

## What Was Built

### Task 1: AnalogDevice and MidiDevice

Both are `Pydantic BaseModel` subclasses in `src/rig/engine/devices.py` with `model_config = ConfigDict(arbitrary_types_allowed=True)`:

- Fields: `id: str`, `name: str`, `config: Any`
- `plan(ctx: PluginContext)` and `diff(ctx: PluginContext)` raise `NotImplementedError`
- `apply(ctx: DeviceApplyContext) -> DeviceApplyResult`
  - `AnalogDevice.apply()`: dry-run path returns skipped; live path calls `ctx.confirmation_io.prompt_analog()` and handles confirm/skip/quit
  - `MidiDevice.apply()`: dry-run path returns skipped; live path tries PC send, loops on `prompt_device()`, handles confirm/retry/skip/quit

### Task 2: ChaseBlissDevice and MC6Device

- `ChaseBlissDevice.apply()`: delegates to a shared `MidiDevice` instance — CBA scene switching is a plain PC message; the 3-phase setup flow stays in `ChaseBlissApplier`
- `MC6Device.apply()`: inlines MC6Applier.apply_banks logic — reads banks from `self.banks`, iterates SysEx messages per switch, handles dry-run and MIDI connection prompt

### Task 3: Default PluginRegistry

`src/rig/engine/devices.py` defines a module-level `default_registry: PluginRegistry` that:
- Calls `register("manual", AnalogDevice(...))` — for `registry.get()` callers (apply.py in P3)
- Calls `register_model("manual", AnalogDevice)` — for loader dispatch in P3
- Registered for all four config types: `"manual"`, `"midi"`, `"chase_bliss"`, `"controller"`

`src/rig/engine/plugin_registry.py` gains `get_registry() -> PluginRegistry` as a convenience function using a lazy import to avoid circular dependency.

## Verification

- `uv run pytest tests/test_devices.py -v` — 38 passed
- `uv run pytest tests/ -q` — 246 passed (no regressions; baseline was 208)
- `python -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(r.get_model('midi'))"` prints `<class 'rig.engine.devices.MidiDevice'>`
- All four device types satisfy Device Protocol: id, name, config, plan, diff, apply all present

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**One implementation note:** The plan's Task 3 suggested adding the module-level registry wiring to `plugin_registry.py`, but this would create a circular import (`plugin_registry → devices → plugin_registry`). Instead, `default_registry` was defined in `devices.py` and `get_registry()` in `plugin_registry.py` uses a lazy import to return it. This achieves the same public API without the circular dependency.

## Known Stubs

None — all four apply() methods execute real logic, not placeholders.

## TDD Gate Compliance

1. RED gate commit: `ad0d340` — `test(04-P2): add failing tests for concrete Device plugin types`
2. GREEN gate commit: `1d43537` — `feat(04-P2): implement AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device`

Both gates satisfied. No REFACTOR pass needed (logic is clean).

## Self-Check: PASSED

- [x] `src/rig/engine/devices.py` exists with AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device
- [x] All four types have id, name, config fields and plan/diff/apply methods
- [x] plan() and diff() raise NotImplementedError on all four types
- [x] apply() delegates to appropriate applier logic
- [x] `default_registry` in devices.py has all four types registered
- [x] `get_registry()` in plugin_registry.py works
- [x] Commit `ad0d340` exists (RED gate)
- [x] Commit `1d43537` exists (GREEN gate)
- [x] 246 tests pass, no regressions
