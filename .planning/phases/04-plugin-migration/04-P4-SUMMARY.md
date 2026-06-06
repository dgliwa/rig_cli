---
phase: 4
plan: P4
subsystem: engine/devices
tags: [gap-closure, mc6, banks, bug-fix]
dependency_graph:
  requires: [P1, P2, P3]
  provides: [correct-mc6-banks-path]
  affects: [src/rig/engine/devices.py, tests/test_devices.py]
tech_stack:
  added: []
  patterns: [getattr-safe-guard]
key_files:
  modified:
    - src/rig/engine/devices.py
    - tests/test_devices.py
decisions:
  - Use getattr(self.config, "banks", None) for the guard so prototype registry instances (config=None) remain safe
metrics:
  duration: "~5 minutes"
  completed: "2026-06-06"
  tasks_completed: 3
  tasks_total: 3
---

# Phase 4 Plan P4: MC6Device Banks Disconnect Gap Closure Summary

## One-liner

Fixed MC6Device.apply() to read banks from self.config.banks instead of the unused self.banks field, and added fixture-backed test coverage to prove the code path.

## What Was Built

Closed the bug identified by Phase 4 verification (score 11/12): `MC6Device.apply()` was iterating `self.banks` (always `[]`) rather than `self.config.banks` (where the loader actually stores bank data). In production this caused MC6 programming to silently return `"skipped"` on every apply.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| P4-T1 | a6c58ea | Remove `banks` field from `MC6Device`; fix guard + both loops to use `self.config.banks` |
| P4-T2 | 818e7a8 | Update two existing tests to construct `MC6Device` with `ControllerConfig(banks=...)` |
| P4-T3 | 9d4c09e | Add fixture-loaded test proving `mc6.config.banks` is populated and `apply()` enters the correct code path |

## Key Changes

### src/rig/engine/devices.py

- Removed `banks: list[dict] = []` field (was never populated by the loader; only `config.banks` is)
- Guard on line 300: `if not getattr(self.config, "banks", None) or ctx.midi is None:`
- Dry-run loop (line 306): `for bank in self.config.banks:`
- Live-apply loop (line 326): `for bank in self.config.banks:`

### tests/test_devices.py

- Added `from pathlib import Path` and `FIXTURE_PATH` constant
- Updated `test_mc6_device_apply_no_banks_is_noop`: constructs with `ControllerConfig(midi_channel=1, banks=[])`
- Updated `test_mc6_device_apply_dry_run_with_banks_returns_skipped`: constructs with `ControllerConfig(midi_channel=1, banks=[...])`
- Added `test_mc6_device_apply_dry_run_uses_config_banks`: loads sample_rig fixture, asserts `mc6.config.banks` is non-empty, verifies `apply()` returns with correct device id

## Verification

- `make test` (239 tests, all pass — 1 new test added)
- `self.banks` absent from `devices.py` (grep confirms)
- `self.config.banks` used in all three locations
- New test exercises the fixture-loaded MC6Device banks path

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- [x] `src/rig/engine/devices.py` modified — `banks` field removed, three `self.config.banks` references present
- [x] `tests/test_devices.py` modified — two tests updated, one new test added
- [x] Commits a6c58ea, 818e7a8, 9d4c09e all exist in git log
- [x] 239 tests pass
