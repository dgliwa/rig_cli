# Requirements: rig-cli

**Defined:** 2026-06-04
**Core Value:** A single command brings the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## v1 Requirements

### CBA Tech-Debt (#11, #12)

- [x] **CBA-01**: `ChaseBlissApplier._build_preset` uses a named `mark_preset_saved(state, device, preset_id)` helper in `base.py` instead of raw dict construction — all `presets_saved` updates go through one auditable path
- [x] **CBA-02**: `_detect_cba_setup` is renamed to `detect_cba_setup` (public) in `plan.py` so `ChaseBlissApplier` no longer imports a private symbol across module boundaries
- [x] **CBA-03**: `_is_cba` is renamed to `is_cba` (public) or inlined if only used internally — no private symbols leaking across module boundaries

### Engine Decoupling (#1)

- [x] **DEC-01**: `ConfirmationIO` Protocol defined — captures user-confirmation calls (`prompt_*`) so appliers can call through an interface rather than directly invoking `interaction.py`
- [x] **DEC-02**: `StateWriter` Protocol defined — captures `read_state`/`write_state` calls so `apply_plan` can work against an in-memory fake in tests
- [x] **DEC-03**: `MidiConnectionIO` Protocol defined — captures the Phase -1 MIDI port selection prompt in `apply_plan`
- [x] **DEC-04**: `ApplyContext` gains a `confirmation_io: ConfirmationIO` field; all three appliers (`AnalogApplier`, `MidiApplier`, `ChaseBlissApplier`) call through it instead of calling `interaction.py` directly
- [x] **DEC-05**: `apply_plan` accepts `state_writer: StateWriter` and `midi_connection_io: MidiConnectionIO` parameters; production adapters (`FileStateWriter`, `InteractiveMidiConnectionIO`) wired at CLI boundary in `cli.py`
- [x] **DEC-06**: Scene state is only written when at least one device action returned `status == "confirmed"` — eliminates silent `{}` write for skipped-device scenes
- [x] **DEC-07**: `tests/fakes.py` provides `InMemoryStateAdapter` and `InMemoryPromptAdapter` that satisfy the Protocols structurally; existing tests that `patch("builtins.input")` are updated to use fakes

### Plan Command (#13)

- [ ] **PLAN-01**: `compute_diff` correctly marks a scene as `unchanged` when no preset assignments have drifted — fixes the always-`changed` bug in `diff.py:35`
- [ ] **PLAN-02**: `DeviceAction` gains `before` and `after` fields (`{preset: str}`) representing the state transition; `compute_plan` populates them from actual vs. desired state
- [ ] **PLAN-03**: `rig plan` produces human-readable text output with visual action markers (`~` configure, `✓` verify, `⚠` analog/manual, `·` no change)
- [ ] **PLAN-04**: `rig plan --format json` emits stable JSON matching `Plan.model_dump_json()` schema with `summary`, `scenes`, and `cba_setup` keys
- [ ] **PLAN-05**: `rig plan` prints a summary line: `Plan: N to configure, M manual, K already set` (or `No changes. Rig is up to date.` when nothing to do)
- [ ] **PLAN-06**: `rig plan` exits non-zero when changes are detected, exits `0` when rig is up to date — enables CI/CD scripting
- [ ] **PLAN-07**: `rig plan` prints a cold-start warning when no `.rig/state.json` exists — treats all scenes as new without silently assuming fresh install
- [ ] **PLAN-08**: `rig plan` hides `no_change` scenes by default; `--show-unchanged` flag reveals them
- [ ] **PLAN-09**: `rig plan --scene <name>` filters output to a single scene
- [ ] **PLAN-10**: `ChaseBlissApplier` does not re-call `detect_cba_setup` during apply — the plan output is the canonical action list; apply executes it without regeneration

## v2 Requirements

### Future Device Support

- **FEAT-01**: CBA Mood MkII / Wombtone / Brothers AM full MIDI CC map (#16)
- **FEAT-02**: HX MIDI channel configurable per device (#4)
- **FEAT-03**: MC6 complex workflows — next page, MIDI clock (#6)
- **FEAT-04**: Full HX SysEx preset read/write via MIDI (#3)
- **FEAT-05**: Isolated preset management mode without full rig setup (#14)

### DX / Housekeeping

- **DX-01**: Module-level READMEs for each `src/rig/` sub-package (#9)
- **DX-02**: Sub-packages per device type/family (#10)
- **DX-03**: Default preset values for every control (#19)
- **DX-04**: MC6 clear message emulation matching web UI behavior (#17)

### Speculative

- **UI-01**: Web or TUI frontend (#18) — depends on engine decoupling from this milestone

## Out of Scope

| Feature | Reason |
|---------|--------|
| Plan file output (`--out plan.json`) | Terraform feature without value for single-user rig; pipe workflow adds complexity |
| `rig plan \| rig apply --plan-file` pipe workflow | Over-engineered for the use case; apply already reads from plan |
| `--auto-approve` / `plan --apply` shortcut | Violates read-only preview contract; apply is the explicit commit step |
| Device connectivity check during plan | Belongs in apply pre-flight only; plan must be runnable without hardware |
| CBA `before`/`after` on `CbaSetupAction` | Deferred — placement (flat vs integrated into `ScenePlan`) needs design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CBA-01 | Phase 1 | Complete |
| CBA-02 | Phase 1 | Complete |
| CBA-03 | Phase 1 | Complete |
| DEC-01 | Phase 2 | Complete |
| DEC-02 | Phase 2 | Complete |
| DEC-03 | Phase 2 | Complete |
| DEC-04 | Phase 2 | Complete |
| DEC-05 | Phase 2 | Complete |
| DEC-06 | Phase 2 | Complete |
| DEC-07 | Phase 2 | Complete |
| PLAN-01 | Phase 3 | Pending |
| PLAN-02 | Phase 3 | Pending |
| PLAN-03 | Phase 3 | Pending |
| PLAN-04 | Phase 3 | Pending |
| PLAN-05 | Phase 3 | Pending |
| PLAN-06 | Phase 3 | Pending |
| PLAN-07 | Phase 3 | Pending |
| PLAN-08 | Phase 3 | Pending |
| PLAN-09 | Phase 3 | Pending |
| PLAN-10 | Phase 3 | Pending |
