---
phase: 03-core-domain-refactor
plan: P1
subsystem: models
tags: [pydantic, device, controller, discriminated-union, domain-model]
requires: []
provides:
  - DeviceType.CONTROLLER enum value ("controller")
  - ControllerConfig Pydantic model with banks/scenes fields
  - Device.config discriminated union extended to include ControllerConfig
  - controller.py backward-compat re-export shim
  - tests/fixtures/sample_rig/devices/mc6.yaml controller fixture
affects: [03-P2, 03-P3, loader, plan-engine, apply-engine]
key_files:
  created:
    - tests/fixtures/sample_rig/devices/mc6.yaml
  modified:
    - src/rig/models/device.py
    - src/rig/models/controller.py
    - src/rig/config/loader.py
    - tests/test_models.py
decisions:
  - "ControllerConfig uses Field(default_factory=dict) for scenes to avoid mutable default"
  - "controller.py kept as backward-compat shim re-exporting ControllerConfig from device.py"
  - "tests/fixtures/sample_rig/controller.yaml deleted; replaced by devices/mc6.yaml"
  - "_parse_controller_legacy temporarily updated to read banks from device config (Wave 3 removes it entirely)"
metrics:
  tasks_completed: 2
  commits: 2
  completed_date: "2026-06-05"
---

# Phase 3 Plan P1: Controller-as-Device Model Summary

Added `DeviceType.CONTROLLER` and `ControllerConfig` to `device.py`'s discriminated union so YAML devices with `config.type: controller` deserialize as first-class `Device` models. Updated `controller.py` as a backward-compat re-export shim and migrated the sample_rig fixture to `devices/mc6.yaml`.

## Tasks Completed

### Task 1: Add ControllerConfig + DeviceType.CONTROLLER to device.py
- Added `DeviceType.CONTROLLER = "controller"` to the StrEnum
- Added `ControllerConfig(DeviceConfig)` with `banks: list[dict[str, Any]] = []` and `scenes: dict[str, Scene] = Field(default_factory=dict)`
- Extended `Device.config` discriminated union to include `ControllerConfig`
- Added `TestControllerConfig` test class with construction and round-trip tests

### Task 2: Update controller.py as compat shim + migrate fixture YAML
- Added `from rig.models.device import ControllerConfig as ControllerConfig` re-export to `controller.py`
- Created `tests/fixtures/sample_rig/devices/mc6.yaml` with `type: controller` config
- Deleted `tests/fixtures/sample_rig/controller.yaml` (old top-level format)
- Minor fix to `_parse_controller_legacy` to read banks from device config (removed in Wave 3)

## Self-Check: PASSED

All 185 tests pass after wave 1 merge (167 baseline + new controller + plugin tests).
