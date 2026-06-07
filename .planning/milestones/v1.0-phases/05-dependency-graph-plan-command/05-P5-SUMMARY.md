---
phase: 5
plan: P5
subsystem: engine/apply
tags: [apply, plan, optional-parameter, fallback, keyword-only]
dependency_graph:
  requires: [P2, P3]
  provides: [apply_plan-optional-plan]
  affects: [cli/commands/apply.py, tests/test_apply.py]
tech_stack:
  added: []
  patterns: [keyword-only parameters via bare *, lazy local import to avoid circular dep]
key_files:
  created: []
  modified:
    - src/rig/engine/apply.py
    - tests/test_apply.py
decisions:
  - Use bare * after plan param to make all subsequent params keyword-only — cleanest approach that keeps all existing callers valid
  - Local import of compute_plan inside fallback block to keep module-level dependency explicit and avoid circular import risk
metrics:
  duration: ~4 minutes
  completed: 2026-06-06
  tasks_completed: 2
  files_modified: 2
---

# Phase 5 Plan P5: apply_plan() Optional Pre-Computed Plan Summary

apply_plan() now accepts plan as optional (Plan | None = None) with keyword-only remaining params, falling back to compute_plan(rig) internally when no plan is provided; raises ValueError when both plan and rig are absent.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| P5-T9 | Make plan parameter optional in apply_plan() | ee335fc |
| P5-T10 | Add TestApplyPlanFallback tests | b7c7ddd |

## What Was Built

**T9 — apply_plan() signature change** (`src/rig/engine/apply.py`):
- Changed `plan: Plan` to `plan: Plan | None = None` as first parameter
- Added bare `*` after plan to force all remaining parameters to keyword-only
- Added fallback block at function entry: when plan is None with a rig, calls `compute_plan(rig, root_path=config_path)` via local import; raises `ValueError` with descriptive message when both plan and rig are absent
- All existing callers (CLI apply command, test_apply.py) remain valid — they pass plan positionally and all subsequent args as kwargs

**T10 — TestApplyPlanFallback** (`tests/test_apply.py`):
- Added `from __future__ import annotations`, `import pytest`, `ApplyResult` to imports
- `test_raises_when_no_plan_and_no_rig`: confirms ValueError on bare call with only fakes
- `test_fallback_computes_plan_from_rig`: confirms compute_plan() runs internally, returns ApplyResult
- `test_explicit_plan_bypasses_compute`: confirms clean plan uses early-return path (status="no_changes")

## Verification

```
uv run pytest tests/test_apply.py -v   # 22 passed
uv run pytest tests/ -q               # 262 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- [x] `src/rig/engine/apply.py` — modified, plan param now optional
- [x] `tests/test_apply.py` — 3 new tests, all pass
- [x] Commit ee335fc — T9 feat(apply)
- [x] Commit b7c7ddd — T10 test(apply)
- [x] 262 tests passing, no regressions
