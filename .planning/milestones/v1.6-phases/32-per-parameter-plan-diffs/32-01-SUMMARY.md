---
phase: 32-per-parameter-plan-diffs
plan: "01"
subsystem: plan-engine
tags:
  - plan
  - param-diff
  - cli
  - models
dependency_graph:
  requires:
    - phase-30-state-tracking
  provides:
    - per-parameter-plan-diffs
  affects:
    - rig.engine.plan.models
    - rig.engine.plan.compute
    - rig.cli.commands.plan
tech_stack:
  added: []
  patterns:
    - ParamDiff Pydantic model for structured before/after parameter comparisons
    - _find_preset + _compute_param_diff helpers in compute.py
    - param_diff sub-lines rendered under ANALOG and CONFIGURE action lines in CLI
key_files:
  created: []
  modified:
    - packages/rig/src/rig/engine/plan/models.py
    - packages/rig/src/rig/engine/plan/compute.py
    - packages/rig/src/rig/cli/commands/plan.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_cli_plan.py
decisions:
  - "VERIFY actions always get empty param_diff to satisfy truth: VERIFY never shows param lines"
  - "HX Stomp presets have no parameters/values fields; produce empty param_diff by design"
  - "param_diff only populated for ANALOG and CONFIGURE actions that need a change"
  - "before=None in ParamDiff means no prior state (cold start); rendered as '?' in CLI"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-22T21:50:30Z"
  tasks_completed: 4
  files_changed: 5
---

# Phase 32 Plan 01: Per-Parameter Plan Diffs Summary

**One-liner:** Per-parameter before/after diffs for ANALOG and CONFIGURE plan actions using ParamDiff Pydantic model wired through compute engine and CLI renderer.

## What Was Built

Added per-parameter diff tracking to `rig plan` output so each device action shows exactly which knob/switch positions or CC parameters changed, with before and after values.

### Changes

1. **models.py** — Added `ParamDiff(name, before, after)` Pydantic model and `param_diff: list[ParamDiff] = []` field to `DeviceAction`. Backward compatible (defaults to empty list).

2. **compute.py** — Added `_find_preset(rig, pedal_id, preset_id)` to look up preset objects by ID, and `_compute_param_diff(before_preset, after_preset)` to extract parameter diffs from `AnalogPreset.values` or `DigitalPreset.parameters`. Wired into both ANALOG and CONFIGURE branches of `compute_plan`. VERIFY actions always receive `param_diff=[]`.

3. **plan.py CLI** — Under each ANALOG and CONFIGURE action line, renders indented `[dim]param: before → after[/dim]` sub-lines. `before=None` displays as `?`. VERIFY actions have no sub-lines (empty `param_diff`).

4. **test_plan.py** — Added `TestParamDiff` class with 7 tests covering analog cold start (before=None), analog changed-only params, analog VERIFY empty diff, digital Chase Bliss cold start, digital changed-only params, HX Stomp empty diff, and ParamDiff model serialization.

5. **test_cli_plan.py** — Added `TestParamDiffRendering` (5 tests) and `TestPlanJsonParamDiff` (4 tests) covering CLI rendering behavior and JSON output correctness.

## Verification

All plan truths satisfied:
- `rig plan` output shows each changed parameter with before/after values per device action ✓
- Unchanged parameters within a changed scene are not listed ✓
- Analog devices show knob/switch names and positions (from `AnalogPreset.values`) ✓
- VERIFY actions never show param_diff lines (empty list) ✓
- `rig plan --format json` includes `param_diff` field on every DeviceAction ✓
- `before` is None when there is no prior state for a device ✓

Test count: 289 (baseline) → 305 (added 16 new tests)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries introduced.

## Self-Check: PASSED

- packages/rig/src/rig/engine/plan/models.py — ParamDiff class and param_diff field exist ✓
- packages/rig/src/rig/engine/plan/compute.py — _find_preset and _compute_param_diff helpers exist ✓
- packages/rig/src/rig/cli/commands/plan.py — param_diff rendering loop present ✓
- packages/rig/tests/test_plan.py — TestParamDiff class with 7 tests ✓
- packages/rig/tests/test_cli_plan.py — TestParamDiffRendering and TestPlanJsonParamDiff ✓
- Commits: b698106, 1f3d23b, a377e0a, a8af675 — all present in git log ✓
- 305 tests pass ✓
