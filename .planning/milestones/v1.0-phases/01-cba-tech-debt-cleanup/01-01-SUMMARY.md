---
phase: 01-cba-tech-debt-cleanup
plan: "01"
subsystem: engine/appliers
tags: [refactor, cba, tech-debt, state-management]

dependency_graph:
  requires: []
  provides:
    - mark_preset_saved helper (rig.engine.appliers.base)
    - detect_cba_setup public function (rig.engine.plan)
  affects:
    - src/rig/engine/appliers/base.py
    - src/rig/engine/plan.py
    - src/rig/engine/appliers/chase_bliss.py

tech_stack:
  added: []
  patterns:
    - Single-path state mutation via named helper (mark_preset_saved)
    - Public function API for cross-module coordination (detect_cba_setup)

key_files:
  modified:
    - src/rig/engine/appliers/base.py
    - src/rig/engine/plan.py
    - src/rig/engine/appliers/chase_bliss.py

decisions:
  - Inline _is_cba as isinstance check rather than keeping a private helper; no additional abstraction needed for a two-line check
  - Place mark_preset_saved in base.py so it sits beside update_device_state (the function it delegates to)

metrics:
  duration: "~2 minutes"
  completed: "2026-06-04"
  tasks_completed: 3
  files_modified: 3
---

# Phase 01 Plan 01: CBA Tech Debt Cleanup Summary

**One-liner:** Consolidate CBA state mutations through `mark_preset_saved` and promote `_detect_cba_setup` to a public API to eliminate cross-module private symbol references.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add `mark_preset_saved` helper to `base.py` | 7b46b09 |
| 2 | Promote `_detect_cba_setup` → `detect_cba_setup` (public), inline `_is_cba` | 31b0591 |
| 3 | Wire `chase_bliss.py` to use both public helpers | 664c6a1 |

## Truths Verified

- All `presets_saved` updates in `ChaseBlissApplier` now flow through `mark_preset_saved`
- `ChaseBlissApplier` imports `detect_cba_setup` (public, no leading underscore) from `plan.py`
- No private symbol (`_name`) is referenced across module boundaries anywhere in the engine package
- All 53 target tests pass unchanged after the refactor (behavior-neutral)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Test Results

- 53 target tests (test_appliers, test_apply, test_plan) pass
- 2 pre-existing failures in test_catalog.py are unrelated to this plan and were present before any changes

## Self-Check: PASSED

Files exist:
- src/rig/engine/appliers/base.py: FOUND
- src/rig/engine/plan.py: FOUND
- src/rig/engine/appliers/chase_bliss.py: FOUND

Commits exist:
- 7b46b09: FOUND
- 31b0591: FOUND
- 664c6a1: FOUND
