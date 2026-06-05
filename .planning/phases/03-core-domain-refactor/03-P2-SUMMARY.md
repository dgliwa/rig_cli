---
phase: 3
plan: P2
subsystem: models
tags: [rig, device-graph, apply_order, compat, tdd]
dependency_graph:
  requires: [03-P1]
  provides: [Rig.apply_order, Rig.scenes-property, Rig.controller-property]
  affects:
    - src/rig/models/rig.py
    - src/rig/config/loader.py
    - tests/test_models.py
    - tests/test_mc6_generator.py
    - tests/test_diff.py
    - tests/test_plan.py
    - tests/test_apply.py
    - tests/test_loader.py
tech_stack:
  added: []
  patterns:
    - "Device-graph model: scenes owned by ControllerConfig, not Rig top-level field"
    - "Compat properties: controller and scenes delegate to _controller_device lookup"
    - "apply_order() DFS: chain-ordered, off-chain, controller last"
key_files:
  created: []
  modified:
    - src/rig/models/rig.py
    - src/rig/config/loader.py
    - tests/test_models.py
    - tests/test_mc6_generator.py
    - tests/test_diff.py
    - tests/test_plan.py
    - tests/test_apply.py
    - tests/test_loader.py
decisions:
  - "Scenes are owned by ControllerConfig in rig.devices, not a top-level Rig field"
  - "Rig.scenes and Rig.controller are read-only properties delegating to _controller_device lookup"
  - "apply_order() sorts in-chain devices by position, appends off-chain devices, appends controller last"
  - "Loader wires filesystem scenes into controller device ControllerConfig via model_copy"
  - "Test fixtures updated: _make_rig() helpers now build Device(type=CONTROLLER) with scenes in ControllerConfig"
  - "test_loader fixture now includes a controller device so scene wiring works end-to-end"
metrics:
  duration: "8m"
  tasks_completed: 2
  completed_date: "2026-06-05"
---

# Phase 3 Plan P2: Rig Device-Graph Model and apply_order() Summary

Removed `controller` and `scenes` as Pydantic fields from Rig, replacing them with compat properties backed by the CONTROLLER device in the devices dict, and added `apply_order()` for deterministic device apply sequencing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for Rig compat properties + apply_order | c0deb47 | tests/test_models.py |
| 1 (GREEN) | Remove fields, add compat properties + apply_order | 0411721 | src/rig/models/rig.py, src/rig/config/loader.py, tests/test_diff.py, tests/test_plan.py, tests/test_apply.py, tests/test_loader.py |
| 2 | Fix test_mc6_generator _make_rig() | ec4a7a8 | tests/test_mc6_generator.py |

## What Was Built

### Rig model changes (src/rig/models/rig.py)

- **Removed** `controller: Controller | None = None` Pydantic field
- **Removed** `scenes: dict[str, Scene] = {}` Pydantic field
- **Added** `_controller_device` private property: scans `self.devices.values()` for the first `DeviceType.CONTROLLER` device
- **Added** `controller` property: returns `Device | None` via `_controller_device`
- **Added** `scenes` property: returns `ControllerConfig.scenes` when controller exists, else `{}`
- **Updated** `mc6` property: now uses `_controller_device` instead of the removed `self.controller` field
- **Added** `apply_order() -> list[Device]`: returns non-controller devices sorted by signal-chain position (in-chain first, off-chain after), then controller device last

### Loader changes (src/rig/config/loader.py)

- **Added** `ControllerConfig` import
- **Updated** `_load_devices_dir`: controller-typed device yaml entries are now registered in both the legacy `controller` path AND the `devices` dict (as a `Device`)
- **Updated** `load_rig`: after merging presets, scenes loaded from `scenes_dir` are wired into the controller device's `ControllerConfig` via `model_copy`; the `Rig` constructor no longer receives `controller=` or `scenes=` kwargs

### Test fixture updates

- **tests/test_loader.py**: Added `pedals/mc6.yaml` controller device to the `rig_dir` fixture so scenes get properly wired to the controller
- **tests/test_diff.py**, **tests/test_plan.py**, **tests/test_apply.py**: Updated `_make_rig()` helpers to build a `Device(type=CONTROLLER)` with scenes in `ControllerConfig` instead of passing `scenes=` to Rig
- **tests/test_mc6_generator.py**: Replaced `Controller()` + `Rig(controller=, scenes=)` pattern with `Device(type=CONTROLLER)` in `devices` dict

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated all affected test _make_rig() helpers and loader.py**

- **Found during:** Task 1 GREEN phase (running full test suite after Rig field removal)
- **Issue:** Removing the `controller` and `scenes` Pydantic fields from Rig silently dropped data for all callers that used `Rig(controller=..., scenes=...)`. Pydantic accepts extra kwargs without error, so the data was silently ignored rather than raising. This caused 23 test failures across test_plan.py, test_diff.py, test_apply.py, test_loader.py, and test_catalog.py.
- **Fix:** Updated `loader.py` to wire scenes into the CONTROLLER device's `ControllerConfig`, updated all `_make_rig()` helpers in affected test files to use the new device-graph model.
- **Files modified:** src/rig/config/loader.py, tests/test_diff.py, tests/test_plan.py, tests/test_apply.py, tests/test_loader.py
- **Commit:** 0411721

## Verification

```
uv run pytest tests/ -q
```

Result: 193 passed (up from 185 baseline, +8 new apply_order and compat property tests)

End-to-end compat property verification passed:
- `scenes: ['s1']`
- `controller id: mc6`
- `apply_order: ['mc6']`

## Self-Check

Verifying key artifacts exist:
- `src/rig/models/rig.py` with `apply_order`: FOUND
- `tests/test_models.py` with `TestApplyOrder`: FOUND
- `tests/test_mc6_generator.py` with `DeviceType.CONTROLLER`: FOUND
- Commit c0deb47 (RED test): FOUND
- Commit 0411721 (GREEN rig.py + loader + tests): FOUND
- Commit ec4a7a8 (Task 2 mc6_generator): FOUND

## Self-Check: PASSED
