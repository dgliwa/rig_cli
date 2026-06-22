---
phase: 30-state-tracking
plan: 01
subsystem: engine
tags: [plan, apply, analog, verify, state-tracking]

# Dependency graph
requires:
  - phase: 29-catalog-integrity
    provides: catalog validation and test infrastructure baseline
provides:
  - Correct VERIFY/ANALOG status assignment for analog devices in compute.py
  - VERIFY action skip in apply.py (no user prompt for already-correct analog devices)
  - Correct CLI rendering: ✓ for analog VERIFY, ⚠ only for ANALOG (needs manual change)
affects: [engine, cli, plan, apply, state]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ActionStatus.VERIFY used for all device types (including analog) when preset already matches state"
    - "apply.py skips device.apply() for any VERIFY-status action — no prompt, no state write"
    - "plan.py renders by action.status (not device_type) so VERIFY analog shows ✓"

key-files:
  created: []
  modified:
    - packages/rig/src/rig/engine/plan/compute.py
    - packages/rig/src/rig/engine/apply.py
    - packages/rig/src/rig/cli/commands/plan.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_cli_plan.py

key-decisions:
  - "Use action.status (not device_type) in plan.py rendering so VERIFY applies consistently across device types"
  - "Promote ActionStatus/DeviceAction/DeviceType to module-level imports in apply.py, eliminating duplicate local imports that caused UnboundLocalError"

patterns-established:
  - "VERIFY is the universal 'already correct' status — device type does not override it"

requirements-completed:
  - STATE-01

# Metrics
duration: 12min
completed: 2026-06-22
---

# Phase 30 Plan 01: State Tracking Summary

**Fixed two false-positive bugs: analog devices with matching state now get VERIFY status in compute.py, apply.py skips device.apply() for VERIFY actions, and plan.py shows ✓ instead of ⚠ for already-correct analog devices.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-22T00:00:00Z
- **Completed:** 2026-06-22T00:12:00Z
- **Tasks:** 3 (2 code tasks + 1 regression test run)
- **Files modified:** 6

## Accomplishments
- `compute.py`: analog devices with `actual_preset == preset_id` now get `ActionStatus.VERIFY` (not `ANALOG`), eliminating a false-positive that marked unchanged analog devices as needing manual action
- `apply.py`: added a VERIFY guard before the device dispatch loop — VERIFY-status actions are skipped entirely, so already-correct devices receive no user prompt
- `plan.py`: changed the rendering condition from `device_type == ANALOG` to `status == ANALOG`, so VERIFY-status analog devices fall through to the checkmark branch
- 5 new tests (3 in test_plan.py, 1 in test_apply.py, 1 in test_cli_plan.py) covering all new behavior
- Full suite: 372 tests pass, 0 regressions

## Task Commits

1. **Task 1: Fix compute.py + apply.py, write tests** - `5c2dc0f` (fix)
2. **Task 2: Fix plan.py display, write CLI test** - `469b23c` (fix)
3. **Task 3: Full test suite — 372 passed**

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `packages/rig/src/rig/engine/plan/compute.py` - Use VERIFY/ANALOG conditionally based on `actual_preset != preset_id` for analog devices
- `packages/rig/src/rig/engine/apply.py` - Skip device.apply() for VERIFY-status actions; promote imports to module level
- `packages/rig/src/rig/cli/commands/plan.py` - Render on `action.status` not `action.device_type`; remove unused DeviceType import
- `packages/rig/tests/test_plan.py` - Three new tests for verify/analog/cold-start analog cases
- `packages/rig/tests/test_apply.py` - One new test asserting device.apply() is not called for VERIFY
- `packages/rig/tests/test_cli_plan.py` - One new test asserting ✓ displayed for analog VERIFY

## Decisions Made
- Render by `action.status` (not `action.device_type`) in plan.py so the same VERIFY semantics apply uniformly regardless of device type — avoids special-casing analog in the rendering layer
- Promoted `ActionStatus`, `DeviceAction`, `DeviceType` to module-level imports in `apply.py` to eliminate local imports that shadowed the module-level name and caused `UnboundLocalError`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] UnboundLocalError from duplicate local import in apply.py**
- **Found during:** Task 1 (fix apply.py)
- **Issue:** Adding `ActionStatus` at module level while the same name was re-imported locally inside `apply_plan()` caused Python to treat the module-level name as a local that hadn't been assigned yet at line 115
- **Fix:** Promoted `ActionStatus`, `DeviceAction`, `DeviceType` to module-level imports and removed all duplicate local imports from `apply_plan()` and `apply_device_preset()`
- **Files modified:** `packages/rig/src/rig/engine/apply.py`
- **Verification:** All tests pass; ruff passes
- **Committed in:** `5c2dc0f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking — import scoping)
**Impact on plan:** Necessary fix to make the module-level import work. No scope creep.

## Issues Encountered
None beyond the import scoping issue above, which was resolved inline.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- State tracking correctness is now established: analog devices in state will be VERIFY (not ANALOG) when already at the desired preset
- `rig plan` output accurately reflects device state without false-positive warnings
- `rig apply` will not prompt users for devices that are already at the correct preset

---
*Phase: 30-state-tracking*
*Completed: 2026-06-22*
