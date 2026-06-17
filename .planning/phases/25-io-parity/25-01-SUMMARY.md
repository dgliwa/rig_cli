---
phase: 25-io-parity
plan: 01
subsystem: testing
tags: [ConfirmationIO, InMemoryPromptAdapter, analog, prompt_analog, io-parity]

# Dependency graph
requires: []
provides:
  - AnalogDevice.apply() threaded through ConfirmationIO Protocol with retry loop
  - prompt_device() in rig.interaction.midi shows correct message for analog (midi_channel=None)
  - prompt_analog() deleted — interaction.py removed, __init__.py cleaned
  - 3 analog tests migrated from patch(builtins.input) to InMemoryPromptAdapter
affects:
  - 25-io-parity (subsequent plans in this phase)
  - Any future plan modifying analog device apply behavior

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ConfirmationIO Protocol threading: all device appliers receive prompt behavior via ctx.confirmation_io"
    - "InMemoryPromptAdapter: deterministic test doubles for ConfirmationIO without stdin patching"
    - "Retry loop pattern in appliers: while True with explicit confirm/quit/retry/skip branches"

key-files:
  created: []
  modified:
    - packages/rig/src/rig/interaction/midi.py
    - packages/rig-analog/src/rig_analog/device.py
    - packages/rig-analog/src/rig_analog/__init__.py
    - packages/rig/tests/test_devices.py
  deleted:
    - packages/rig-analog/src/rig_analog/interaction.py

key-decisions:
  - "Unbounded retry loop in AnalogDevice.apply() matches original prompt_analog() behavior — no max-retry limit added"
  - "Empty __all__ = [] left in __init__.py rather than deleting (Python package marker)"
  - "prompt_device() analog branch uses midi_channel is None as discriminator — clean, matches Protocol signature"

patterns-established:
  - "ConfirmationIO threading pattern: all device apply() methods use ctx.confirmation_io, never raw input()"
  - "InMemoryPromptAdapter(default=...) in _make_apply_ctx(): no monkeypatching for analog tests"

requirements-completed: [IO-01, IO-02]

# Metrics
duration: 3min
completed: 2026-06-17
---

# Phase 25 Plan 01: I/O Parity — AnalogDevice ConfirmationIO Threading Summary

**ConfirmationIO fully threaded through AnalogDevice.apply() — last raw input() call eliminated from all applier paths; prompt_analog() deleted; 3 tests migrated to InMemoryPromptAdapter**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-17T14:03:48Z
- **Completed:** 2026-06-17T14:06:22Z
- **Tasks:** 5 (4 with commits, 1 verification-only)
- **Files modified:** 4 (1 deleted)

## Accomplishments
- Fixed `prompt_device()` in `rig.interaction.midi` to display "Set {device} manually (knobs/switches)" when `midi_channel is None` (analog path), instead of the MIDI-specific "Connect MIDI to {device}"
- Replaced `prompt_analog()` call in `AnalogDevice.apply()` with `ctx.confirmation_io.prompt_device()` in a while-True retry loop — matching original unbounded retry behavior
- Deleted `packages/rig-analog/src/rig_analog/interaction.py` (prompt_analog() is now dead code) and cleaned `__init__.py`
- Migrated 3 analog tests (confirm/quit/skip) from `patch("rig_analog.device.prompt_analog")` to `InMemoryPromptAdapter(default=...)` — no stdin patching required

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix prompt_device() display for analog** - `c9f03a9` (feat)
2. **Task 2: Thread ConfirmationIO through AnalogDevice.apply()** - `8f8bcd7` (feat)
3. **Task 3: Delete prompt_analog() and clean __init__.py** - `d0bec5c` (refactor)
4. **Task 4: Migrate 3 analog tests to InMemoryPromptAdapter** - `06052da` (test)
5. **Task 5: Full test suite verification** — no commit (verification only)

## Files Created/Modified
- `packages/rig/src/rig/interaction/midi.py` — Added `if midi_channel is None` branch in else block of prompt_device()
- `packages/rig-analog/src/rig_analog/device.py` — Removed prompt_analog import; replaced apply() body with ConfirmationIO retry loop
- `packages/rig-analog/src/rig_analog/__init__.py` — Removed prompt_analog export; now contains only empty `__all__`
- `packages/rig/tests/test_devices.py` — Migrated 3 test functions to InMemoryPromptAdapter
- `packages/rig-analog/src/rig_analog/interaction.py` — DELETED (dead code)

## Decisions Made
- Used unbounded `while True` retry loop in `AnalogDevice.apply()` to match original `prompt_analog()` behavior (which also looped on invalid input) — per plan D-03 directive
- Left `__init__.py` with `__all__: list[str] = []` rather than deleting (Python package marker convention)
- Used `midi_channel is None` as discriminator in `prompt_device()` to distinguish analog from MIDI devices — matches the Protocol's existing signature semantics

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all changes were straightforward refactors. The 3 migrated tests passed immediately after migration with no debugging required. All 309 tests passed on first `make test` run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- IO parity fully achieved for analog device path — no raw `input()` calls remain in any applier package src directory
- `ConfirmationIO` Protocol is the sole path for all device confirmation prompts
- All 309 tests pass with no regressions
- Ready for subsequent plans in phase 25-io-parity

---
*Phase: 25-io-parity*
*Completed: 2026-06-17*
