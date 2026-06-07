---
phase: 5
plan: P6
subsystem: engine/appliers
tags: [cba, appliers, plan, convergence, refactor]
dependency_graph:
  requires: [P5]
  provides: [PLAN-10, D-10]
  affects: [src/rig/engine/plan/compute.py, src/rig/engine/appliers/chase_bliss.py, tests/test_appliers.py]
tech_stack:
  added: []
  patterns: [forward-looking plan detection, plan-authoritative apply]
key_files:
  created: []
  modified:
    - src/rig/engine/plan/compute.py
    - src/rig/engine/appliers/chase_bliss.py
    - tests/test_appliers.py
decisions:
  - detect_cba_setup now produces all 3 CBA phases in one call for a fresh device
  - apply_setup executes only the pre-computed action list; no dynamic re-queuing at apply time
metrics:
  duration: ~10 minutes
  completed: 2026-06-06T21:40:44Z
---

# Phase 5 Plan P6: Fix CBA single-apply convergence (PLAN-10 gap) Summary

**One-liner:** Made `detect_cba_setup()` forward-looking so a single `rig apply` converges a fresh CBA device through all 3 phases, and removed the `_enqueue_new_actions` re-detection from `ChaseBlissApplier`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| P6-T1 | Fix detect_cba_setup() in compute.py | dba05f9 | src/rig/engine/plan/compute.py |
| P6-T2 | Remove _enqueue_new_actions from chase_bliss.py | b947f84 | src/rig/engine/appliers/chase_bliss.py |
| P6-T3 | Update tests in test_appliers.py | 27ab406 | tests/test_appliers.py |

## What Was Built

### T1 — detect_cba_setup() forward-looking fix

Removed the `continue` early-exit after the `establish_channel` phase block, so phases 2 and 3 are always computed in a single `detect_cba_setup()` call regardless of whether the channel is already established.

Dropped the `not has_unsaved` guard on `register_scenes` so registration is included whenever `registration_done=False`. Removed the now-unused `has_unsaved` variable.

A fresh CBA device now produces `establish_channel` + all `build_preset` actions + `register_scenes` in one call. The plan is complete and authoritative before `apply` starts.

### T2 — Remove _enqueue_new_actions

Removed `detect_cba_setup` from the import in `chase_bliss.py`. Removed the `_enqueue_new_actions` nested function (lines 33-39) and its two call sites (after `establish_channel` confirm and after `build_preset` confirm).

`apply_setup()` now simply iterates the passed actions list in order. No runtime re-detection. The apply path is no longer coupled to plan computation.

### T3 — New applier tests

Added two tests to `TestChaseBlissApplierSetup`:

- `test_detect_cba_setup_fresh_device_produces_all_phases`: builds a minimal CBA rig inline (1 device, 2 presets, 1 scene) with empty state and asserts that `detect_cba_setup()` returns all 3 phase types in the correct order.
- `test_apply_setup_does_not_enqueue_actions_dynamically_on_confirm`: passes a single `establish_channel` action and asserts exactly 1 result is returned after confirmation (no dynamic additions).

## Verification Results

- `uv run pytest tests/test_appliers.py -v`: 11 passed (9 existing + 2 new)
- `uv run pytest tests/ -q`: 268 passed, 0 failures
- `grep detect_cba_setup src/rig/engine/appliers/chase_bliss.py`: no output
- `grep _enqueue_new_actions src/rig/engine/appliers/chase_bliss.py`: no output

## Deviations from Plan

**1. [Rule 1 - Bug] Removed unused `has_unsaved` variable**
- **Found during:** T1 — after removing the `not has_unsaved` guard, the variable was still being assigned but never read
- **Issue:** Ruff would flag `has_unsaved = True` as an unused variable assignment
- **Fix:** Removed the `has_unsaved = False` initialization and the `has_unsaved = True` assignment inside the loop
- **Files modified:** src/rig/engine/plan/compute.py
- **Commit:** dba05f9

**2. [Rule 1 - Lint] Ruff auto-fixed import ordering in test_appliers.py**
- **Found during:** T3 commit — pre-commit hook ran ruff which consolidated imports in the test method
- **Fix:** Staged ruff's auto-correction and re-committed
- **Files modified:** tests/test_appliers.py
- **Commit:** 27ab406

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- [x] src/rig/engine/plan/compute.py exists and was modified
- [x] src/rig/engine/appliers/chase_bliss.py exists and was modified
- [x] tests/test_appliers.py exists and was modified
- [x] Commit dba05f9 exists (T1)
- [x] Commit b947f84 exists (T2)
- [x] Commit 27ab406 exists (T3)
- [x] 268 tests pass
