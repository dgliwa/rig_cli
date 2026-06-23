---
phase: 31-mc6-clear-sysex-fix
plan: "01"
subsystem: midi
tags: [sysex, mc6, morningstar, flash, persistence]

# Dependency graph
requires: []
provides:
  - "clear_preset_messages() defaults to save=True, writing cleared switch slots to MC6 flash"
affects: [mc6-applier, rig-apply]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All three MC6 SysEx write functions (update_preset_name, update_preset_pc, clear_preset_messages) now consistently default save=True"

key-files:
  created: []
  modified:
    - packages/rig-morningstar/src/rig_morningstar/sysex.py
    - packages/rig-morningstar/tests/test_sysex.py
    - packages/rig/tests/test_mc6_sysex.py

key-decisions:
  - "save=True default for clear_preset_messages aligns with MC6 web UI behaviour and sibling functions, eliminating power-cycle regression"

patterns-established:
  - "MC6 SysEx save default: all write operations default to flash (0x7F); callers opt-in to RAM-only (0x00) explicitly"

requirements-completed:
  - MC6-01

# Metrics
duration: 5min
completed: 2026-06-22
---

# Phase 31 Plan 01: MC6 Clear SysEx Default Fix Summary

**Fixed power-cycle regression: `clear_preset_messages()` now defaults `save=True` (Op6=0x7F) so cleared switch slots persist to MC6 flash, matching the MC6 web UI and all sibling SysEx write functions.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-22T00:00:00Z
- **Completed:** 2026-06-22T00:05:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Changed `save: bool = False` to `save: bool = True` in `clear_preset_messages()` in sysex.py
- Updated docstring to explain Op6=0x7F (flash) vs Op6=0x00 (RAM-only)
- Updated existing test assertion from `0x00` to `0x7F` and removed stale comment about "avoids MC6 bank navigation"
- Added `test_clear_preset_messages_no_save` in test_mc6_sysex.py to cover explicit `save=False`
- Added `test_default_saves_to_flash` and `test_explicit_no_save` in test_sysex.py for full coverage
- All 392 tests pass

## Task Commits

1. **Task 1: Fix clear_preset_messages default and update test assertions** - `14bd8a9` (fix)

## Files Created/Modified

- `packages/rig-morningstar/src/rig_morningstar/sysex.py` — Changed default `save=False` to `save=True`, updated docstring
- `packages/rig-morningstar/tests/test_sysex.py` — Added `test_default_saves_to_flash` and `test_explicit_no_save` to `TestClearPresetMessages`
- `packages/rig/tests/test_mc6_sysex.py` — Updated slot sequence assertion to `0x7F`, added `test_clear_preset_messages_no_save`

## Decisions Made

Followed plan exactly: changed one default parameter to make the API internally consistent and fix the power-cycle regression where cleared slots were only written to RAM.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — this change only affects the save byte in outbound SysEx messages with no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- `packages/rig-morningstar/src/rig_morningstar/sysex.py` — FOUND (modified)
- `packages/rig-morningstar/tests/test_sysex.py` — FOUND (modified)
- `packages/rig/tests/test_mc6_sysex.py` — FOUND (modified)
- Commit `14bd8a9` — FOUND in git log
- `uv run pytest packages/ -q` — 392 passed, 0 failed
