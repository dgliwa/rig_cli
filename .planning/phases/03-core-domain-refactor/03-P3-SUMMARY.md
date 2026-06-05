---
phase: 3
plan: P3
subsystem: config/loader
tags: [loader, controller, device-graph, refactor, dead-code-removal, tdd]
dependency_graph:
  requires: [03-P1, 03-P2]
  provides: [loader-no-legacy-controller]
  affects:
    - src/rig/config/loader.py
    - tests/test_loader.py
tech_stack:
  patterns:
    - "Pydantic discriminated union handles all device types including controller"
    - "model_copy used for immutable scene injection into ControllerConfig"
key_files:
  modified:
    - src/rig/config/loader.py
    - tests/test_loader.py
decisions:
  - "Removed Controller/ControllerType/MC6Config imports — Pydantic discriminated union in Device handles type: controller"
  - "_parse_controller_legacy removed entirely; loader now treats all YAML files uniformly via _parse_device"
  - "_load_devices_dir simplified from tuple return to dict[str, Device]"
  - "load_rig() no longer has separate controller.yaml / mc6.yaml loading paths"
metrics:
  duration: "4 minutes"
  tasks_completed: 2
  files_modified: 2
  completed_date: "2026-06-05"
---

# Phase 3 Plan P3: Loader Legacy Cleanup Summary

Removed the legacy controller loading path from loader.py — Controller YAML files now flow through the standard `_parse_device` path using the Pydantic discriminated union introduced in P1, completing the full data path from YAML to Rig via the device-graph model.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| T1 (RED) | Add controller-as-device and scenes tests | d6c3f93 | tests/test_loader.py |
| T1 (GREEN) | Remove legacy controller path from loader | 550cd4d | src/rig/config/loader.py |

## What Changed

### src/rig/config/loader.py

- Removed `from rig.models.controller import Controller, ControllerType, MC6Config`
- Removed `_parse_controller_legacy()` function entirely
- Simplified `_load_devices_dir()`: removed `mc6_data` parameter, changed return type from `tuple[dict[str, Device], Controller | None]` to `dict[str, Device]`, all YAML files now routed through `_parse_device()` uniformly
- Removed `controller.yaml` / `mc6.yaml` loading block from `load_rig()` — replaced with single `devices = _load_devices_dir(devices_dir)` call
- `Rig(...)` constructor call no longer passes `controller=` or `scenes=` kwargs

### tests/test_loader.py

- Added `test_loads_controller_as_device`: asserts mc6 device appears in `rig.devices` with `DeviceType.CONTROLLER` type and `rig.controller.id == "mc6"`
- Added `test_scenes_accessible_via_controller`: asserts scenes injected into `ControllerConfig` are accessible via `rig.scenes` compat property

## Verification

Full test suite: **195 passed** (up from 193 baseline, +2 new tests)

End-to-end spot-check:
```
controller id: mc6
devices: ['mc6']
scenes: []
```

## Deviations from Plan

None - plan executed exactly as written.

Note: The behavioral contract was already satisfied by P2 (scene injection, ControllerConfig, compat shim). P3's contribution is structural cleanup — removing dead code paths and unused imports while verifying correct behavior with explicit tests.

## Self-Check

- `src/rig/config/loader.py` exists: FOUND
- `tests/test_loader.py` with `test_loads_controller_as_device`: FOUND
- Commit d6c3f93 (RED test): FOUND
- Commit 550cd4d (GREEN loader cleanup): FOUND
- No `Controller/ControllerType/MC6Config` imports in loader.py: CONFIRMED
- No `_parse_controller_legacy` in loader.py: CONFIRMED
- `_load_devices_dir` returns `dict[str, Device]`: CONFIRMED
- 195 tests pass: CONFIRMED

## Self-Check: PASSED
