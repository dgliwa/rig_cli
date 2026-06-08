---
phase: 09-core-model-cleanup
plan: 02
subsystem: models
tags: [signal-chain, loader, graph]
requires:
  - phase: 09
    provides: clean Scene and Rig models
provides:
  - Rig.signal_chain as list[str] (not list[SignalChainPosition])
  - signal_chain.py deleted
  - DeviceGraph iterates string IDs
  - Loader extracts device ID strings from YAML chain entries
  - SignalChainPosition removed from models/__init__.py
affects: [phase 10, phase 11]
tech-stack:
  added: []
  patterns: ["signal chain is an ordered list of device ID strings"]
key-files:
  created: []
  modified:
    - packages/rig/src/rig/models/rig.py
    - packages/rig/src/rig/models/graph.py
    - packages/rig/src/rig/config/loader.py
    - packages/rig/src/rig/models/__init__.py
    - packages/rig/tests/test_models.py
    - packages/rig/tests/test_graph.py
    - packages/rig/tests/test_loader.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_diff.py
    - packages/rig/tests/test_mc6_generator.py
    - packages/rig/tests/test_appliers.py
  deleted:
    - packages/rig/src/rig/models/signal_chain.py
key-decisions: []
patterns-established: []
requirements-completed:
  - SCHEMA-03
duration: 15min
completed: 2026-06-08
---

# Phase 09: Core Model Cleanup — Wave 2 Summary

**Simplified signal chain from list[SignalChainPosition] to list[str]; deleted signal_chain.py; updated DeviceGraph and loader**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-08T04:28:00Z
- **Completed:** 2026-06-08T04:43:00Z
- **Tasks:** 2
- **Files modified:** 12
- **Files deleted:** 1

## Accomplishments
- `Rig.signal_chain` is now `list[str]` (device ID strings) with default `[]`
- `signal_chain.py` deleted — `SignalChainPosition` class removed entirely
- `DeviceGraph.apply_order()` uses `enumerate()` on string list instead of `.device_ref`/`.position`
- `DeviceGraph._detect_cycles()` iterates string IDs directly
- Loader extracts device IDs from YAML chain entries (supports `device`, `pedal`, `device_ref`, `pedal_ref` keys)
- `SignalChainPosition` removed from `models/__init__.py` imports
- All 12 test files updated to use `["device-id"]` syntax instead of `[SignalChainPosition(device_ref="...", position=N)]`
- 4 tests removed (TestSignalChainModel class)
- 295 tests pass

## Task Commits

## Files Modified
- `packages/rig/src/rig/models/rig.py` — Changed signal_chain type to `list[str] = []`
- `packages/rig/src/rig/models/graph.py` — Updated apply_order and _detect_cycles to iterate strings
- `packages/rig/src/rig/config/loader.py` — Updated chain construction and _validate_references
- `packages/rig/src/rig/models/__init__.py` — Removed SignalChainPosition import/export
- 8 test files — Updated signal_chain construction

## Files Deleted
- `packages/rig/src/rig/models/signal_chain.py`

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## Next Phase Readiness
- Ready for Wave 3: Move plugin config types to plugin packages; remove CBA plan-time detection
