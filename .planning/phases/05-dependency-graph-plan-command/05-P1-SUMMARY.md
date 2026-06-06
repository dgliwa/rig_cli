---
phase: 5
plan: P1
subsystem: models
tags: [graph, ordering, cycle-detection, refactor]
dependency_graph:
  requires: []
  provides: [DeviceGraph, CycleError]
  affects: [Rig.apply_order, engine/plan, engine/apply]
tech_stack:
  added: []
  patterns: [plain-class-not-pydantic, local-import-for-circular-avoidance]
key_files:
  created:
    - src/rig/models/graph.py
    - tests/test_graph.py
  modified:
    - src/rig/models/rig.py
decisions:
  - D-01: DeviceGraph as standalone plain class (not Pydantic BaseModel) in src/rig/models/graph.py
  - D-02: Edges derived from signal_chain position order; CONTROLLER devices always last
  - D-03: ConfigError (CycleError subclass) raised on cycle detection
metrics:
  duration: "2m"
  completed: "2026-06-06"
  tasks_completed: 3
  files_changed: 3
---

# Phase 5 Plan P1: DeviceGraph Model Summary

## One-liner

Extracted `Rig.apply_order()` ordering logic into a standalone `DeviceGraph` class with duplicate-device-ref cycle detection raising `CycleError(ConfigError)`.

## What Was Built

`DeviceGraph` is a plain Python class (not Pydantic) that takes a `Rig` and computes device apply order. It mirrors the former inline `Rig.apply_order()` logic exactly: signal-chain devices sorted by position, off-chain non-controller devices, then the CONTROLLER device last. Before ordering, it checks for duplicate `device_ref` values in `signal_chain` and raises `CycleError` if found.

`Rig.apply_order()` now delegates to `DeviceGraph(self).apply_order()` via a local import (to avoid circular imports at module level — `graph.py` imports `Rig` under `TYPE_CHECKING`). The method signature is unchanged; no external callers were affected.

8 tests in `tests/test_graph.py` cover all ordering scenarios and cycle detection behavior. Full suite: 247 passed.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| P5-T1 | Create src/rig/models/graph.py | 6255e48 |
| P5-T2 | Update Rig.apply_order() to delegate | 9b46c6d |
| P5-T3 | Create tests/test_graph.py | f191f7f |

## Deviations from Plan

None - plan executed exactly as written. Ruff auto-formatted both new files on commit (line-length wrapping for dict comprehension and list comprehension); changes were accepted and re-committed.

## Known Stubs

None.

## Threat Flags

None - no new network endpoints, auth paths, or trust boundary changes introduced.

## Self-Check: PASSED

- `src/rig/models/graph.py` exists and is importable
- `tests/test_graph.py` exists with 8 tests, all passing
- `src/rig/models/rig.py` delegates to DeviceGraph
- Commits 6255e48, 9b46c6d, f191f7f all present in git log
- Full test suite: 247 passed, 0 failures
