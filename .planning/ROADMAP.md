# Roadmap: rig-cli — I/O Decoupling & Plan Command

## Overview

Three-phase milestone: clean CBA tech-debt first, then introduce Protocol-typed I/O ports to make the apply engine testable without hardware, then ship a trustworthy `rig plan` command that previews required changes before apply.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: CBA Tech-Debt Cleanup** - Remove private-symbol leakage and raw dict mutation in ChaseBlissApplier before protocol work begins (completed 2026-06-04)
- [ ] **Phase 2: Engine I/O Decoupling** - Introduce three narrow Protocol ports so the apply engine is fully testable without MIDI hardware
- [ ] **Phase 3: Plan Command** - Ship a trustworthy `rig plan` command with correct no_change detection, exit codes, and stable JSON output

## Phase Details

### Phase 1: CBA Tech-Debt Cleanup

**Goal**: All state writes in ChaseBlissApplier go through a named helper and no module imports a private symbol from another module
**Depends on**: Nothing (first phase)
**Requirements**: CBA-01, CBA-02, CBA-03
**Success Criteria** (what must be TRUE):

  1. `_build_preset` calls `mark_preset_saved(state, device, preset_id)` — no raw `state["presets_saved"][...]` dict assignments remain in ChaseBlissApplier
  2. `detect_cba_setup` is a public symbol in `plan.py`; `ChaseBlissApplier` imports it without a leading underscore
  3. No private symbol (`_name`) is referenced across module boundaries anywhere in the engine package

**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Extract mark_preset_saved helper, make detect_cba_setup public, inline _is_cba (CBA-01/02/03)

### Phase 2: Engine I/O Decoupling

**Goal**: The apply engine is fully testable without MIDI hardware via three narrow Protocol-typed I/O ports
**Depends on**: Phase 1
**Requirements**: DEC-01, DEC-02, DEC-03, DEC-04, DEC-05, DEC-06, DEC-07
**Success Criteria** (what must be TRUE):

  1. `ConfirmationIO`, `StateWriter`, and `MidiConnectionIO` Protocols exist in `src/rig/engine/ports.py`; all three appliers call through `ApplyContext.confirmation_io` instead of importing `interaction.py` directly
  2. `apply_plan` accepts `state_writer` and `midi_connection_io` parameters; production adapters are wired at the CLI boundary in `cli.py`
  3. `tests/fakes.py` provides `InMemoryStateAdapter` and `InMemoryPromptAdapter`; existing tests that patched `builtins.input` are rewritten to use fakes and pass without hardware
  4. Scene state is only written when at least one device returned `status == "confirmed"` — no silent `{}` write for skipped scenes

**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Create ports.py (Protocols + adapters), fakes.py, update ApplyContext + appliers (DEC-01/02/03/04)
- [ ] 02-02-PLAN.md — Wire adapters into apply_plan and CLI, fix scene-write bug, rewrite patched tests (DEC-05/06/07)

### Phase 3: Plan Command

**Goal**: `rig plan` is a trustworthy, read-only preview of required rig changes with correct no_change detection, CI-friendly exit codes, and stable JSON output
**Depends on**: Phase 2
**Requirements**: PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, PLAN-06, PLAN-07, PLAN-08, PLAN-09, PLAN-10
**Success Criteria** (what must be TRUE):

  1. `rig plan` correctly identifies scenes with no drifted preset assignments as unchanged; `compute_diff` no longer marks every scene as changed
  2. `rig plan` exits non-zero when changes are detected and exits `0` when the rig is up to date; a cold-start warning is printed when `.rig/state.json` does not exist
  3. `rig plan` prints human-readable output with visual markers (`~` configure, `✓` verify, `⚠` analog, `·` no change) and a summary line; `--format json` emits stable `Plan.model_dump_json()` output; `--show-unchanged` and `--scene <name>` flags work correctly
  4. `apply` does not re-call `detect_cba_setup` mid-execution — the plan output is the canonical action list consumed by apply without regeneration

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CBA Tech-Debt Cleanup | 1/1 | Complete    | 2026-06-04 |
| 2. Engine I/O Decoupling | 0/2 | Not started | - |
| 3. Plan Command | 0/TBD | Not started | - |
