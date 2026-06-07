---
phase: 02-engine-i-o-decoupling
verified: 2026-06-04T18:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 02: Engine I/O Decoupling Verification Report

**Phase Goal:** The apply engine is fully testable without MIDI hardware via three narrow Protocol-typed I/O ports
**Verified:** 2026-06-04T18:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ConfirmationIO, StateWriter, and MidiConnectionIO Protocols exist in src/rig/engine/ports.py; all three appliers call through ApplyContext.confirmation_io instead of importing interaction.py directly | VERIFIED | ports.py defines all three Protocols with `...` bodies; analog.py line 29, midi_device.py line 52, chase_bliss.py lines 98/121/181/232 all route through ctx.confirmation_io; no direct interaction imports in any applier |
| 2 | apply_plan accepts state_writer and midi_connection_io parameters; production adapters are wired at the CLI boundary in cli.py | VERIFIED | apply.py lines 50-51 show required params; cli/commands/apply.py lines 39-45 construct FileStateWriter() and InteractiveMidiConnectionIO() and pass them |
| 3 | tests/fakes.py provides InMemoryStateAdapter and InMemoryPromptAdapter; existing tests that patched builtins.input are rewritten to use fakes and pass without hardware | VERIFIED | tests/fakes.py provides all three fakes; grep for `patch("builtins.input"` returns zero results; 167 tests pass |
| 4 | Scene state is only written when at least one device returned status == "confirmed" — no silent {} write for skipped scenes | VERIFIED | apply.py line 176: `if any(r.status == "confirmed" for r in device_results)` guards the scene write; test_apply_skip_does_not_write_device_state confirms this behavior |

**Score:** 4/4 ROADMAP truths verified

### Must-Have Truths (from PLAN frontmatter — combined DEC-01 through DEC-07)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ConfirmationIO, StateWriter, and MidiConnectionIO Protocols exist in ports.py with production adapters | VERIFIED | All six names (ConfirmationIO, StateWriter, MidiConnectionIO, RichConfirmationIO, FileStateWriter, InteractiveMidiConnectionIO) import cleanly; Protocol bodies use `...` not pass |
| 2 | ApplyContext has a required confirmation_io field of type ConfirmationIO | VERIFIED | base.py line 29: `confirmation_io: ConfirmationIO` — no default, required positional |
| 3 | AnalogApplier, MidiApplier, and ChaseBlissApplier route all interaction calls through ctx.confirmation_io | VERIFIED | analog.py line 29, midi_device.py line 52, chase_bliss.py lines 98/121/181/232 all use ctx.confirmation_io.*; no interaction imports remain |
| 4 | tests/fakes.py provides InMemoryPromptAdapter, InMemoryStateAdapter, InMemoryMidiConnectionIO | VERIFIED | All three classes exist in tests/fakes.py with correct side_effect queue logic, in-memory state, and configurable return values |
| 5 | No applier imports directly from rig.interaction.* for prompts that belong to ConfirmationIO | VERIFIED | grep for interaction imports in appliers returns zero results |
| 6 | apply_plan accepts required state_writer: StateWriter and midi_connection_io: MidiConnectionIO parameters; apply_plan no longer calls read_state, write_state, or prompt_midi_connect directly | VERIFIED | apply.py lines 50-51 show required params; grep for read_state/write_state/prompt_midi_connect in apply.py returns zero results |
| 7 | cli/commands/apply.py constructs production adapters and passes to apply_plan; test files use InMemoryPromptAdapter not patch(builtins.input); all tests pass without MIDI hardware | VERIFIED | CLI lines 39-45 confirmed; zero patch("builtins.input") in tests; 167 passed, 0 failed |

**Score:** 7/7 must-have truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/rig/engine/ports.py` | ConfirmationIO, StateWriter, MidiConnectionIO Protocols + production adapters | VERIFIED | 130 lines; all 6 exports present; Protocol bodies use `...` |
| `tests/fakes.py` | In-memory test doubles for all three Protocols | VERIFIED | 119 lines; InMemoryPromptAdapter with side_effect deque; InMemoryStateAdapter with in-memory RigState; InMemoryMidiConnectionIO with midi.connect() on confirm |
| `src/rig/engine/appliers/base.py` | ApplyContext with confirmation_io field | VERIFIED | Line 29: `confirmation_io: ConfirmationIO` required field after dry_run |
| `src/rig/engine/appliers/analog.py` | Routes to ctx.confirmation_io | VERIFIED | Line 29: `ctx.confirmation_io.prompt_analog(...)` |
| `src/rig/engine/appliers/midi_device.py` | Routes to ctx.confirmation_io | VERIFIED | Line 52: `ctx.confirmation_io.prompt_device(...)` |
| `src/rig/engine/appliers/chase_bliss.py` | Routes to ctx.confirmation_io | VERIFIED | Lines 98, 121, 181, 232: all CBA prompt calls via ctx.confirmation_io |
| `src/rig/engine/apply.py` | apply_plan with StateWriter and MidiConnectionIO params | VERIFIED | Lines 50-51 required params; delegates to state_writer.read/write and midi_connection_io.prompt_connect |
| `src/rig/cli/commands/apply.py` | CLI wires production adapters | VERIFIED | Lines 39-45: FileStateWriter() and InteractiveMidiConnectionIO() constructed and passed |
| `tests/test_appliers.py` | Uses InMemoryPromptAdapter, no builtins.input patches | VERIFIED | Line 13 imports from tests.fakes; _make_ctx uses InMemoryPromptAdapter |
| `tests/test_apply.py` | Uses InMemoryStateAdapter, InMemoryMidiConnectionIO, no patches | VERIFIED | Line 11 imports all three fakes; apply_plan called with fake adapters throughout |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `analog.py` | `ctx.confirmation_io.prompt_analog` | ApplyContext.confirmation_io | WIRED | Line 29 confirmed |
| `midi_device.py` | `ctx.confirmation_io.prompt_device` | ApplyContext.confirmation_io | WIRED | Line 52 confirmed |
| `chase_bliss.py` | `ctx.confirmation_io.prompt_cba_channel/preset/register` | ApplyContext.confirmation_io | WIRED | Lines 98, 121, 181, 232 confirmed |
| `apply.py` | `state_writer.read/write` | StateWriter protocol param | WIRED | Lines 67, 199 confirmed |
| `apply.py` | `midi_connection_io.prompt_connect` | MidiConnectionIO protocol param | WIRED | Line 111 confirmed |
| `cli/commands/apply.py` | `apply_plan` | FileStateWriter + InteractiveMidiConnectionIO | WIRED | Lines 39-51 confirmed |

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers Protocol seams and test infrastructure, not dynamic data-rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ports.py exports clean | `uv run python -c "from rig.engine.ports import ConfirmationIO, StateWriter, MidiConnectionIO, RichConfirmationIO, FileStateWriter, InteractiveMidiConnectionIO; print('OK')"` | `ports.py imports OK` | PASS |
| fakes.py exports clean | `uv run python -c "from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter, InMemoryMidiConnectionIO; print('OK')"` | `fakes.py imports OK` | PASS |
| No interaction imports in appliers | `grep -rn "from rig.interaction" src/rig/engine/appliers/` | zero results | PASS |
| No builtins.input patches in tests | `grep -rn 'patch("builtins.input"' tests/` | zero results | PASS |
| Full test suite | `uv run pytest tests/ -q` | `167 passed in 0.36s` | PASS |
| Ruff lint | `uv run ruff check src/` | `All checks passed!` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEC-01 | 02-01-PLAN.md | ConfirmationIO Protocol defined | SATISFIED | ports.py lines 26-52 |
| DEC-02 | 02-01-PLAN.md | StateWriter Protocol defined | SATISFIED | ports.py lines 55-60 |
| DEC-03 | 02-01-PLAN.md | MidiConnectionIO Protocol defined | SATISFIED | ports.py lines 63-72 |
| DEC-04 | 02-01-PLAN.md | ApplyContext gains confirmation_io; appliers call through it | SATISFIED | base.py line 29; all three appliers verified |
| DEC-05 | 02-02-PLAN.md | apply_plan accepts state_writer and midi_connection_io; adapters wired at CLI | SATISFIED | apply.py lines 50-51; cli/commands/apply.py lines 39-51 |
| DEC-06 | 02-02-PLAN.md | Scene state only written when at least one confirmed | SATISFIED | apply.py line 176; test_apply_skip_does_not_write_device_state |
| DEC-07 | 02-02-PLAN.md | tests/fakes.py provides fakes; input-patching tests rewritten | SATISFIED | tests/fakes.py; zero patch("builtins.input") in tests |

All 7 requirements (DEC-01 through DEC-07) are satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/rig/engine/apply.py` | 47 | `TODO: i think this is too big a function` | INFO | Pre-existing marker (present in commit 2377c93 before phase 02); not introduced by this phase |
| `src/rig/engine/apply.py` | 82 | `TODO: We probably should identify the controller first` | INFO | Pre-existing marker (present in commit 2377c93 before phase 02); not introduced by this phase |
| `src/rig/engine/apply.py` | 122 | `TODO: again, don't like this being on the plan...` | INFO | Pre-existing marker (present in commit 2377c93 before phase 02); not introduced by this phase |

All three TODO markers predate phase 02 (confirmed via `git show 2377c93:src/rig/engine/apply.py`). They are architectural observations left intentionally per the Side Project Mode convention in CLAUDE.md ("Leave TODO/FIXME/HACK markers for things to revisit"). No new debt markers were introduced by this phase.

### Human Verification Required

None. All success criteria are verifiable programmatically. No visual, real-time, or external-service-dependent behaviors.

### Gaps Summary

No gaps. All 7 requirements verified, all artifacts substantive and wired, all tests pass, no new debt introduced.

---

_Verified: 2026-06-04T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
