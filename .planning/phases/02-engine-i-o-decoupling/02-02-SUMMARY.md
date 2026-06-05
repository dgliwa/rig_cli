---
phase: 02-engine-i-o-decoupling
plan: "02"
subsystem: engine/apply + cli/commands/apply + tests
tags:
  - decoupling
  - testing
  - apply-engine
  - io-ports
dependency_graph:
  requires:
    - 02-01  # I/O port Protocols and production adapters
  provides:
    - apply_plan with required StateWriter and MidiConnectionIO params
    - cli/commands/apply.py wired with production adapters
    - test_appliers.py and test_apply.py using fakes (no builtins.input patches)
  affects:
    - src/rig/engine/apply.py
    - src/rig/cli/commands/apply.py
    - tests/test_appliers.py
    - tests/test_apply.py
    - tests/fakes.py
    - conftest.py
tech_stack:
  added: []
  patterns:
    - InMemoryPromptAdapter replaces patch("builtins.input") in applier tests
    - InMemoryStateAdapter replaces filesystem state.json assertions
    - InMemoryMidiConnectionIO replaces MIDI port selection input patches
    - conftest.py sys.path fix for worktree shadow with global editable install
key_files:
  created:
    - conftest.py  # worktree sys.path guard
  modified:
    - src/rig/engine/apply.py
    - src/rig/cli/commands/apply.py
    - tests/test_appliers.py
    - tests/test_apply.py
    - tests/fakes.py
decisions:
  - "apply_plan has required state_writer and midi_connection_io params; confirmation_io is optional (defaults to RichConfirmationIO) so CLI need not pass it"
  - "InMemoryMidiConnectionIO.prompt_connect calls midi.connect() on confirm to enable MIDI send assertions in integration tests"
  - "conftest.py inserted to fix sys.path ordering when global editable install shadows worktree source during pytest"
  - "test_apply.py tests that need pre-established CBA state still write state to disk for compute_plan, then use InMemoryStateAdapter for apply_plan assertions"
metrics:
  duration: "~30 minutes"
  completed: "2026-06-04"
  tasks_completed: 4
  files_modified: 6
---

# Phase 02 Plan 02: Protocol Wiring and Test Rewrite Summary

Wire the Protocols from plan 02-01 into apply_plan and the CLI, fix the DEC-06 scene-write bug, then rewrite all builtins.input-patching tests to use the fakes from 02-01.

## What Was Built

Apply engine fully decoupled from direct I/O calls (read_state, write_state, prompt_midi_connect) via required protocol params. Test suite converted from builtins.input monkey-patching to in-memory fakes — no MIDI hardware or filesystem reads needed to run tests.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | c5102e4 | add StateWriter/MidiConnectionIO required params to apply_plan, fix DEC-06 scene-write bug |
| Task 2 | c8c9812 | wire FileStateWriter and InteractiveMidiConnectionIO into CLI apply command |
| Task 3 | 6ff592e | rewrite test_appliers.py and test_apply.py to use InMemoryPromptAdapter, InMemoryStateAdapter, InMemoryMidiConnectionIO |
| Task 4 | (this) | SUMMARY.md |

## Verification

- `grep -rn 'patch("builtins.input"' tests/` → 0 results
- `uv run pytest tests/ -q` → 167 passed, 0 failed
- `uv run ruff check src/` → All checks passed
- `apply_plan` signature has `state_writer: StateWriter` and `midi_connection_io: MidiConnectionIO` as required params
- `cli/commands/apply.py` constructs `FileStateWriter()` and `InteractiveMidiConnectionIO()` and passes them

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Global editable install shadows worktree source during pytest**
- **Found during:** Task 3 — all test_apply.py tests failed with `TypeError: apply_plan() got an unexpected keyword argument 'state_writer'`
- **Issue:** The system Python (used by the globally-installed pytest binary) had a `.pth` file at `/Users/derekgliwa/.local/share/mise/installs/python/3.12.13/lib/python3.12/site-packages/__editable__.rig_cli-0.1.0.pth` pointing to the main repo's `src/`. This caused `rig.engine.apply` to be imported from the main repo rather than the worktree, despite the worktree's `.venv` having the correct editable install. The global `.pth` was earlier in `sys.path` during pytest collection.
- **Fix:** Added `conftest.py` at the worktree root that inserts the worktree's `src` at `sys.path[0]` during test collection, ensuring the worktree's version of the `rig` package is used in all tests.
- **Files modified:** `conftest.py` (new file)
- **Commit:** 6ff592e

**2. [Rule 1 - Bug] InMemoryMidiConnectionIO did not open MIDI port on confirm**
- **Found during:** Task 3 — `test_midi_connect_and_send` failed because MIDI sends to the mock port failed with "Device has no open MIDI connection"
- **Issue:** `InMemoryMidiConnectionIO.prompt_connect` returned `("confirm", port_name)` but did not call `midi.connect(port_name, device)`. The production `prompt_midi_connect` function calls `midi.connect()` before returning, so the protocol contract implies the connection is opened when `"confirm"` is returned.
- **Fix:** Updated `InMemoryMidiConnectionIO.prompt_connect` to call `midi.connect(port_name, device)` when returning `"confirm"`, mirroring the production contract.
- **Files modified:** `tests/fakes.py`
- **Commit:** 6ff592e

**3. [Rule 1 - Bug] test_cba_preset_build_writes_state and test_cba_registration_writes_state used wrong compute_plan call**
- **Found during:** Task 3 — tests failed because `compute_plan(rig)` (no `root_path`) produced a plan for empty state, not for the pre-established CBA state being tested
- **Issue:** Tests that set pre-state on `InMemoryStateAdapter` were calling `compute_plan(rig)` without `root_path`, so the plan didn't include the expected CBA action (`build_preset` or `register_scenes`)
- **Fix:** Updated tests to write pre-state to disk with `_write_state_file` and call `compute_plan(rig, root_path=str(tmp_path))` so the plan correctly reflects the desired CBA setup stage. `InMemoryStateAdapter` is still used for `apply_plan` state assertions.
- **Files modified:** `tests/test_apply.py`
- **Commit:** 6ff592e

## Self-Check: PASSED

- `src/rig/engine/apply.py` — FOUND
- `src/rig/cli/commands/apply.py` — FOUND
- `tests/test_appliers.py` — FOUND
- `tests/test_apply.py` — FOUND
- `conftest.py` — FOUND
- `02-02-SUMMARY.md` — FOUND (written to main `.planning` dir, same as worktree's)
- commits c5102e4, c8c9812, 6ff592e — FOUND in worktree git history
