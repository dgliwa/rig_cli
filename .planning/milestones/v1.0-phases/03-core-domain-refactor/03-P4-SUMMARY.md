---
phase: 3
plan: P4
subsystem: engine
tags: [plugin, protocol, registry, tdd]
dependency_graph:
  requires: []
  provides: [DevicePlugin, PluginContext, PluginRegistry]
  affects: [src/rig/engine/plugin.py, src/rig/engine/plugin_registry.py]
tech_stack:
  added: []
  patterns: [Protocol structural subtyping, dataclass context object, wirable registry]
key_files:
  created:
    - src/rig/engine/plugin.py
    - src/rig/engine/plugin_registry.py
    - tests/test_plugin.py
  modified: []
decisions:
  - "PluginContext uses dataclass (not Pydantic BaseModel) per existing ApplyContext pattern"
  - "No module-level PluginRegistry singleton in Phase 3 — Phase 4 decides singleton strategy when wiring appliers"
  - "DevicePlugin Protocol returns object for plan/diff/apply — Phase 4 narrows to specific result types"
  - "Device and Rig under TYPE_CHECKING guard in plugin.py to avoid circular imports"
metrics:
  duration: "1m 45s"
  completed: "2026-06-05"
  tasks_completed: 2
  files_created: 3
---

# Phase 3 Plan P4: Plugin Protocol and Registry Summary

DevicePlugin Protocol + PluginContext dataclass + empty PluginRegistry scaffold using TDD (RED/GREEN per task).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for DevicePlugin/PluginContext | 2a7ceb9 | tests/test_plugin.py |
| 1 (GREEN) | Create engine/plugin.py | 59ba24b | src/rig/engine/plugin.py |
| 2 (RED) | Failing tests for PluginRegistry | 45cc1ff | tests/test_plugin.py |
| 2 (GREEN) | Create engine/plugin_registry.py | f294253 | src/rig/engine/plugin_registry.py |

## What Was Built

- `src/rig/engine/plugin.py`: `DevicePlugin` Protocol (plan/diff/apply methods returning `object`) and `PluginContext` dataclass with exactly three required fields: `state: RigState`, `rig: Rig`, `dry_run: bool`. Uses `from __future__ import annotations` and `TYPE_CHECKING` guard for `Device`/`Rig` forward references.
- `src/rig/engine/plugin_registry.py`: `PluginRegistry` class with `register(config_type, plugin)` and `get(config_type) -> DevicePlugin | None` methods. Empty by default, no module-level singleton, no registered appliers.
- `tests/test_plugin.py`: 13 tests covering PluginContext (dataclass check, field names/count, instantiation, not Pydantic) and PluginRegistry (empty on creation, register/get, overwrite, no side effects at import time).

## Verification

- Full test suite: 180 passed (167 baseline + 13 new plugin tests)
- Import check: `PluginContext fields: ['state', 'rig', 'dry_run']`, `empty get: None`, `registered get is not None: True`
- No circular import issues

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

Both tasks followed the full RED/GREEN cycle:
- Task 1: `test(03-P4)` RED commit (2a7ceb9) → `feat(03-P4)` GREEN commit (59ba24b)
- Task 2: `test(03-P4)` RED commit (45cc1ff) → `feat(03-P4)` GREEN commit (f294253)

## Known Stubs

None.

## Threat Flags

No new security-relevant surface introduced. PluginRegistry accepts arbitrary objects as plugins per T-03P4-01 (accepted risk — internal/trusted in Phase 3).

## Self-Check: PASSED

- `src/rig/engine/plugin.py` exists: FOUND
- `src/rig/engine/plugin_registry.py` exists: FOUND
- `tests/test_plugin.py` exists: FOUND
- Commit 2a7ceb9 (RED test): FOUND
- Commit 59ba24b (GREEN plugin.py): FOUND
- Commit 45cc1ff (RED registry tests): FOUND
- Commit f294253 (GREEN plugin_registry.py): FOUND
