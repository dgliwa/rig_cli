---
plan: "20-01"
phase: 20
title: "Quick Wins & Dead Code"
status: complete
wave: 1
commit: c8d5b57
---

## What Was Done

Executed all four cleanup tasks in a single atomic commit.

**TYPE-04 — Dead `plan()`/`diff()` stubs removed:**
- Deleted `plan()` and `diff()` from `Device` Protocol in `plugin.py` (method definitions + docstring example + module-level bullet)
- Deleted the 4-line stub blocks from all four plugin device files: `rig_analog/device.py`, `rig_hx/device.py`, `rig_chasebliss/device.py`, `rig_morningstar/device.py`
- Removed `PluginContext` from imports in all four plugin device files (F401 unused import)
- Deleted 8 `*_plan_raises_not_implemented` / `*_diff_raises_not_implemented` tests from `test_devices.py`
- Deleted `test_device_protocol_has_distinct_context_types` from `test_plugin.py`
- Updated `test_device_protocol_satisfied_by_class_with_all_members`, `test_device_protocol_missing_property_detected_via_hasattr`, and `test_discovery_placeholder_implements_device_protocol` to remove plan/diff references
- Updated structural Protocol check in `test_devices.py` from `("id", "name", "config", "plan", "diff", "apply")` → `("id", "name", "config", "apply")`

**TEST-01 — Stale root `tests/` directory deleted:**
- Removed all 19 files from root `tests/` (imported pre-refactor module paths; 9 caused collection errors)
- Updated `Makefile` `test`, `lint`, `lint-all`, `format`, `format-all` targets from `tests/`/`src/` to `packages/`

**QUAL-01 — Raw device-type string comparisons fixed:**
- `packages/rig/src/rig/engine/plan/compute.py`: `pedal.type.value == "analog"` → `pedal.type == DeviceType.ANALOG` (added import)
- `packages/rig/src/rig/cli/commands/plan.py`: `action.device_type == "analog"` → `action.device_type == DeviceType.ANALOG` (added import)
- `packages/rig-hx/src/rig_hx/device.py`: `data.get("type") == "modeler"` → `data.get("type") == DeviceType.MODELER`

**QUAL-02 — TODO resolved:**
- Replaced single-line TODO in `models/device.py` with a 4-line explanation: StrEnum is for runtime comparisons; Literal fields are required by Pydantic discriminated union dispatch; the two are orthogonal.

## Key Files

- `packages/rig/src/rig/engine/plugin.py` — Protocol cleaned
- `packages/rig-*/src/*/device.py` — stubs and imports removed (4 files)
- `packages/rig/src/rig/engine/plan/compute.py` — enum comparison + import
- `packages/rig/src/rig/cli/commands/plan.py` — enum comparison + import
- `packages/rig/src/rig/models/device.py` — TODO replaced
- `packages/rig/tests/test_devices.py` — 8 stub tests removed
- `packages/rig/tests/test_plugin.py` — 4 tests/assertions updated
- `Makefile` — test/lint/format targets updated
- `tests/` — deleted (19 files)

## Test Results

**Before:** `3 failed, 302 passed` (305 total)
**After:** `3 failed, 293 passed` (296 total)

9 tests deleted (8 stub tests + 1 context-types test). The 3 failures are identical pre-existing stdin-capture failures unrelated to Phase 20. No new failures introduced.

`make test` now runs `uv run pytest -v` (picks up `testpaths = ["packages"]` from `pyproject.toml`) and exits cleanly for the 293 passing tests.
