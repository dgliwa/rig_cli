# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- ✅ **v1.2 Cleaner Core** — Phases 9-13 (shipped 2026-06-08)
- ✅ **v1.3 Chase Bliss Pedal Support** — Phases 14-19 (shipped 2026-06-10)
- ✅ **v1.4 Architecture & Type Integrity** — Phases 20-24 (shipped 2026-06-17)
- ✅ **v1.5 Interactive Preset Management** — Phases 25-28 (shipped 2026-06-17)
- 🔴 **v1.6 Correctness & State Reliability** — Phases 29-33 (in progress)
- ⬜ **v2.0 Platform Foundations** — Phases 34-39 (planned)

## Phases

<details>
<summary>✅ v1.0 I/O Decoupling & Plugin Architecture (Phases 1-5) — SHIPPED 2026-06-07</summary>

- [x] Phase 1: CBA Tech-Debt Cleanup (1/1 plans) — completed 2026-06-04
- [x] Phase 2: Engine I/O Decoupling (2/2 plans) — completed 2026-06-05
- [x] Phase 3: Core Domain Refactor (4/4 plans) — completed 2026-06-05
- [x] Phase 4: Plugin Migration (4/4 plans) — completed 2026-06-06
- [x] Phase 5: Dependency Graph & Plan Command (6/6 plans) — completed 2026-06-07

</details>

<details>
<summary>✅ v1.1 Package Extraction & Plugin Isolation (Phases 6-8) — SHIPPED 2026-06-07</summary>

- [x] Phase 6: Core Package & Entry Point Discovery (2/2 plans) — completed 2026-06-07
- [x] Phase 7: Plugin Package Wiring & Device-Level MIDI (3/3 plans) — completed 2026-06-07
- [x] Phase 8: Core Cleanup — Dead Code & Plugin Isolation (3/3 plans) — completed 2026-06-07

</details>

<details>
<summary>✅ v1.2 Cleaner Core (Phases 9-13) — SHIPPED 2026-06-08</summary>

- [x] Phase 9: Core Model Cleanup (4/4 plans) — completed 2026-06-08
- [x] Phase 10: Schema & Loader Rewrite (1/1 plans) — completed 2026-06-08
- [x] Phase 11: Dead Code & Compat Removal (1/1 plans) — completed 2026-06-08
- [x] Phase 12: Clean Up Deferred Items (1/1 plans) — completed 2026-06-08
- [x] Phase 13: Resolve Remaining TODO:1.2 Markers (1/1 plans) — completed 2026-06-08

</details>

<details>
<summary>✅ v1.3 Chase Bliss Pedal Support (Phases 14-19) — SHIPPED 2026-06-10</summary>

- [x] Phase 14: CBA Catalog Expansion (1/1 plans) — completed 2026-06-08
- [x] Phase 15: Preset Parameter Validation (1/1 plans) — completed 2026-06-08
- [x] Phase 16: Reset-to-Defaults (1/1 plans) — completed 2026-06-08
- [x] Phase 17: Fix stale Mood MkII catalog tests (1/1 plans) — completed 2026-06-08
- [x] Phase 18: Close gap: CBA-01/CBA-02 — auto-populate controls from catalog (1/1 plans) — completed 2026-06-10
- [x] Phase 19: Close v1.3 verification gaps — add VERIFICATION.md and VALIDATION.md (1/1 plans) — completed 2026-06-10

</details>

<details>
<summary>✅ v1.4 Architecture & Type Integrity (Phases 20-24) — SHIPPED 2026-06-17</summary>

- [x] Phase 20: Quick Wins & Dead Code (1/1 plans) — completed 2026-06-15
- [x] Phase 21: Concrete Types at the Plugin Boundary (1/1 plans) — completed 2026-06-15
- [x] Phase 22: Retire the Legacy Device Model (1/1 plans) — completed 2026-06-15
- [x] Phase 23: ApplyContext Consolidation & Test Capture Fixes (1/1 plans) — completed 2026-06-16
- [x] Phase 24: Close v1.4 gaps: Phase 21 verification, MC6 preset typing, QUAL-01 DeviceAction (1/1 plans) — completed 2026-06-17

</details>

<details open>
<summary>✅ v1.5 Interactive Preset Management (Phases 25-28) — SHIPPED 2026-06-17</summary>

- [x] **Phase 25: I/O Parity** - Thread ConfirmationIO through AnalogApplier; update tests to use InMemoryPromptAdapter — Completed 2026-06-17
- [x] **Phase 26: Isolated Preset Apply** - `rig apply --device <id> --preset <id>` applies one device's preset without full scene setup — Completed 2026-06-17
- [x] **Phase 27: Editor Protocol, CLI Surface & YAML Writer** - `rig edit` command, save/discard lifecycle, and rig.yaml preset writer — Completed 2026-06-17
- [x] **Phase 28: Editor Plugin Implementations** - CC-based live MIDI editing (CBA/MIDI/HX) and analog prompt-per-control flow — Completed 2026-06-17

</details>

<details open>
<summary>🔴 v1.6 Correctness & State Reliability (Phases 29-33) — IN PROGRESS</summary>

- [ ] **Phase 29: Catalog Integrity** — fix wet_bypass/loop_bypass CC mismatch; establish catalog as the single source of truth with CI-enforced tests
- [ ] **Phase 30: State Tracking Completeness** — `state.json` tracks actual preset changes per device, not just scene-level apply events (#22)
- [ ] **Phase 31: MC6 Clear SysEx Fix** — emulate the "clear" message sent by MC6 web UI when clearing a preset slot (#17)
- [ ] **Phase 32: Per-Parameter Plan Diffs (PLAN-01/02)** — `rig plan` shows before/after CC values and knob positions per device-action, not just "changed"
- [ ] **Phase 33: Apply-01/02 Completions** — skip analog prompt when state already shows desired preset; `--device` flag applies single device across all scenes

</details>

<details>
<summary>⬜ v2.0 Platform Foundations (Phases 34-39) — PLANNED</summary>

- [ ] **Phase 34: First-Class Scenes** — decouple scenes from controller device config; scenes defined at top level in `rig.yaml`; rigs without a controller can have scenes
- [ ] **Phase 35: State Schema Versioning** — `state.json` carries `schema_version`; migration on load; silent field additions no longer silently corrupt plan diffs
- [ ] **Phase 36: Plugin Authoring Guide (PKG-07)** — `PLUGIN-AUTHORING.md` covering Device Protocol, entry points, `from_raw_yaml`, setup/apply/edit lifecycle; example minimal plugin skeleton committed to repo
- [ ] **Phase 37: PyPI Publishing + CI** — GitHub Actions workflow publishes all 5 packages to PyPI on tag; version matrix; `pip install rig rig-chasebliss` works
- [ ] **Phase 38: YAML Config Schema Documentation** — formal `rig.yaml` reference: every key, type, required/optional, validation rules, example snippets
- [ ] **Phase 39: Reference Third-Party Plugin (rig-neuraldsp)** — stub Neural DSP Quad Cortex plugin that demonstrates the full plugin contract; lives in its own repo; linked from authoring guide as "hello world"

</details>

## Phase Details

### Phase 29: Catalog Integrity

**Goal**: The CBA control catalog is the single authoritative source for CC numbers; all tests derive expectations from the catalog, not hard-coded magic numbers
**Depends on**: —
**Requirements**: CAT-01
**Success Criteria** (what must be TRUE):

  1. `make test` passes with 0 failures — the wet_bypass/loop_bypass CC mismatch is resolved
  2. Test assertions reference catalog constants, not duplicated literal CC numbers
  3. The correct CC value (102 or 103) is verified against the official Mood MkII MIDI spec

**Plans**: 1 plan

Plans:

- [x] 29-01-PLAN.md — Fix CC swap in catalog.py; add named constants; update both test files to reference constants

### Phase 30: State Tracking Completeness

**Goal**: `state.json` accurately reflects what preset is active on each device after every apply; `rig plan` diffs reflect actual device state rather than scene-level snapshots
**Depends on**: Phase 29
**Requirements**: STATE-01
**Success Criteria** (what must be TRUE):

  1. After `rig apply`, each device's `last_preset` in `state.json` matches the preset that was applied
  2. `rig plan` reports "unchanged" for a device when `state.json` already records the desired preset — no false positives
  3. Applying the same scene twice does not re-prompt for analog devices whose state already matches

**Plans**: 1 plan

### Phase 31: MC6 Clear SysEx Fix

**Goal**: `rig apply` sends the correct SysEx sequence when clearing an MC6 switch slot — matching what the MC6 web UI sends
**Depends on**: Phase 29
**Requirements**: MC6-01
**Success Criteria** (what must be TRUE):

  1. Captured SysEx from MC6 web UI "clear" action is documented and reproduced in `rig-morningstar`
  2. `rig apply` clearing a switch slot sends the identical byte sequence
  3. Existing MC6 SysEx tests updated to cover the clear case

**Plans**: 1 plan

### Phase 32: Per-Parameter Plan Diffs

**Goal**: `rig plan` output shows the specific CC values or knob positions that will change, not just a "changed" label at the scene level
**Depends on**: Phase 30
**Requirements**: PLAN-01, PLAN-02
**Success Criteria** (what must be TRUE):

  1. `rig plan` output per device-action lists each parameter with `before:` and `after:` values when changed
  2. Parameters that are unchanged within a "changed" scene are not listed
  3. Analog devices list knob/switch names and positions, not CC numbers
  4. JSON output (`--format json`) includes the parameter diff structure

**Plans**: 1 plan

### Phase 33: Apply-01/02 Completions

**Goal**: Apply skips analog prompts for devices already in the desired state; `--device <id>` applies a single device across all scenes without a `--preset` flag
**Depends on**: Phase 30
**Requirements**: APPLY-01, APPLY-02
**Success Criteria** (what must be TRUE):

  1. `rig apply` with an analog device whose state matches the scene preset skips the manual prompt
  2. `rig apply --device <id>` applies that device's preset for every scene in the plan without touching other devices
  3. Both behaviors have tests using `InMemoryPromptAdapter`

**Plans**: 1 plan

### Phase 34: First-Class Scenes

**Goal**: Scenes are defined at the top level of `rig.yaml`, not embedded inside the controller device's config; a rig without a controller device can still define and apply scenes
**Depends on**: —
**Requirements**: SCENE-01
**Success Criteria** (what must be TRUE):

  1. `rig.yaml` schema supports a top-level `scenes:` key; loader populates `Rig.scenes` directly from it
  2. Controller config no longer owns scene definitions; scenes referenced in MC6 bank/switch config are resolved from `Rig.scenes`
  3. A rig with no controller device but a `scenes:` key validates and applies correctly
  4. `Rig.scenes` property removed in favor of a real field; `controller` remains for MC6-specific routing
  5. Existing sample fixtures and tests updated; no regressions

**Plans**: 2 plans

### Phase 35: State Schema Versioning

**Goal**: `state.json` carries a schema version field; the loader migrates older state files forward on read; new fields added to `DeviceState` do not silently corrupt plan diffs
**Depends on**: Phase 30
**Requirements**: STATE-02
**Success Criteria** (what must be TRUE):

  1. `state.json` written by `rig apply` includes `"schema_version": 1`
  2. `read_state()` detects missing/older schema version and applies a migration function before returning `RigState`
  3. A state file with no `schema_version` field (legacy) loads without error and is treated as version 0
  4. Tests cover: fresh file, version-0 legacy file, current version file

**Plans**: 1 plan

### Phase 36: Plugin Authoring Guide

**Goal**: A third party can write and publish a `rig-mypedal` plugin without reading the core source — the guide is the complete contract
**Depends on**: Phase 34 (scene decoupling stabilizes the contract)
**Requirements**: PKG-07
**Success Criteria** (what must be TRUE):

  1. `PLUGIN-AUTHORING.md` in repo root covers: Device Protocol methods, entry point registration, `from_raw_yaml` contract, setup/apply/edit lifecycle, example `pyproject.toml`
  2. A minimal working example plugin is committed to the repo under `examples/rig-example-plugin/`
  3. `rig validate` with the example plugin installed passes against the example fixture

**Plans**: 1 plan

### Phase 37: PyPI Publishing + CI

**Goal**: All 5 packages are published to PyPI; a GitHub Actions workflow publishes on git tag; `pip install rig rig-chasebliss` works from scratch
**Depends on**: Phase 36
**Requirements**: PKG-08
**Success Criteria** (what must be TRUE):

  1. GitHub Actions workflow triggers on `v*` tags and publishes all 5 packages to PyPI
  2. `pip install rig rig-chasebliss` installs a working CLI with CBA support in a clean venv
  3. Package versions are kept in sync via a single version bump script
  4. CI runs `make test` and `make lint` on every push; publishes only on tag

**Plans**: 1 plan

### Phase 38: YAML Config Schema Documentation

**Goal**: Every key in `rig.yaml` is documented with type, required/optional status, validation rules, and an example; a newcomer can build a valid config from the doc alone
**Depends on**: Phase 34 (scene schema stable)
**Requirements**: DOC-01
**Success Criteria** (what must be TRUE):

  1. `docs/rig-yaml-reference.md` documents every field at device, preset, scene, and top-level scope
  2. Each plugin package contributes its own `config` block reference (analog, midi, chase_bliss, mc6)
  3. A newcomer fixture built from the doc alone passes `rig validate`

**Plans**: 1 plan

### Phase 39: Reference Third-Party Plugin (rig-neuraldsp)

**Goal**: A minimal Neural DSP Quad Cortex plugin in its own repo demonstrates the full plugin authoring contract and serves as a "hello world" for third-party authors
**Depends on**: Phase 36, Phase 37
**Requirements**: PKG-09
**Success Criteria** (what must be TRUE):

  1. `rig-neuraldsp` repo is published to GitHub with a complete `pyproject.toml` entry point registration
  2. Installing `rig-neuraldsp` alongside `rig` makes `neural_dsp` a valid `config.type` for a device
  3. The plugin implements setup/apply for basic MIDI PC message send with QC-specific channel/preset-number config
  4. `rig validate` and `rig apply --dry-run` work against a sample QC rig config

**Plans**: 2 plans

### Phase 25: I/O Parity

**Goal**: Analog device prompts flow through the same ConfirmationIO abstraction as all other prompts — no raw `input()` calls remain in any applier
**Depends on**: Phase 24 (ConfirmationIO Protocol and InMemoryPromptAdapter already exist in v1.4)
**Requirements**: IO-01, IO-02
**Success Criteria** (what must be TRUE):

  1. Running `rig apply` with an analog device never calls `builtins.input` directly — all prompts go through `ConfirmationIO.prompt()`
  2. AnalogApplier tests pass without monkeypatching `builtins.input` — they instantiate `InMemoryPromptAdapter` and pass it through context
  3. The test suite passes with no stdin-capture flags required for analog tests

**Plans**: 1 plan

Plans:

- [x] 25-01-PLAN.md — Thread ConfirmationIO through AnalogDevice.apply(), delete prompt_analog(), migrate 3 tests

### Phase 26: Isolated Preset Apply

**Goal**: Users can apply a single device's preset without triggering full scene setup — useful for mid-session tweaks and targeted reapplies
**Depends on**: Phase 25
**Requirements**: PRESET-01, PRESET-02, PRESET-03
**Success Criteria** (what must be TRUE):

  1. User can run `rig apply --device <id> --preset <id>` and only that device is activated — all other devices are skipped
  2. After a targeted apply, `state.json` reflects the updated preset for the targeted device only — other device states are unchanged
  3. Running `rig apply --device <id> --preset <id>` with an unknown device or preset ID produces a clear error message
  4. Running `rig apply` without `--device`/`--preset` flags behaves exactly as before (no regression)

**Plans**: 1 plan

Plans:

- [ ] 25-01-PLAN.md — Thread ConfirmationIO through AnalogDevice.apply(), delete prompt_analog(), migrate 3 tests

### Phase 27: Editor Protocol, CLI Surface & YAML Writer

**Goal**: Users can enter editor mode for a device's preset via `rig edit`, and the save/discard lifecycle writes changes back to rig.yaml atomically
**Depends on**: Phase 26
**Requirements**: EDIT-01, EDIT-02, EDIT-04, EDIT-05
**Success Criteria** (what must be TRUE):

  1. `rig edit <device-id> <preset-id>` launches editor mode for the named preset — the command exists and routes correctly
  2. When the user confirms a save, the updated preset values are written back to `rig.yaml` and can be loaded by `rig validate` without error
  3. When the user discards, `rig.yaml` is bit-for-bit identical to its state before `rig edit` was run
  4. The Device Protocol (or companion EditorProtocol) declares `edit(preset_id, ctx)` — plugins can implement it without touching core

**Plans**: 1 plan

Plans:

- [ ] 25-01-PLAN.md — Thread ConfirmationIO through AnalogDevice.apply(), delete prompt_analog(), migrate 3 tests

### Phase 28: Editor Plugin Implementations

**Goal**: Each device plugin delivers its own interactive editing behavior — CC-based plugins stream live values; analog plugin presents a prompt-per-control flow
**Depends on**: Phase 27
**Requirements**: EDIT-03, EDIT-06
**Success Criteria** (what must be TRUE):

  1. During CBA/MIDI editor mode, changing a control value immediately sends the corresponding CC message to the device — the user hears the change live
  2. Analog plugin editor mode walks the user through each control with a prompt — no MIDI is sent (manual set); the plugin owns this loop entirely
  3. After any plugin's editor session saves, `rig validate` confirms the written values are valid preset parameters

**Plans**: 1 plan

Plans:

- [x] 28-01-PLAN.md — CBA live editor (CC send), Analog key-value editor, HX stub, EditContext.midi field

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. CBA Tech-Debt Cleanup | v1.0 | 1/1 | Complete | 2026-06-04 |
| 2. Engine I/O Decoupling | v1.0 | 2/2 | Complete | 2026-06-05 |
| 3. Core Domain Refactor | v1.0 | 4/4 | Complete | 2026-06-05 |
| 4. Plugin Migration | v1.0 | 4/4 | Complete | 2026-06-06 |
| 5. Dependency Graph & Plan Command | v1.0 | 6/6 | Complete | 2026-06-07 |
| 6. Core Package & Entry Point Discovery | v1.1 | 2/2 | Complete | 2026-06-07 |
| 7. Plugin Package Wiring & Device-Level MIDI | v1.1 | 3/3 | Complete | 2026-06-07 |
| 8. Core Cleanup — Dead Code & Plugin Isolation | v1.1 | 3/3 | Complete | 2026-06-07 |
| 9. Core Model Cleanup | v1.2 | 4/4 | Complete | 2026-06-08 |
| 10. Schema & Loader Rewrite | v1.2 | 1/1 | Complete | 2026-06-08 |
| 11. Dead Code & Compat Removal | v1.2 | 1/1 | Complete | 2026-06-08 |
| 12. Clean Up Deferred Items | v1.2 | 1/1 | Complete | 2026-06-08 |
| 13. Resolve Remaining TODO:1.2 Markers | v1.2 | 1/1 | Complete | 2026-06-08 |
| 14. CBA Catalog Expansion | v1.3 | 1/1 | Complete | 2026-06-08 |
| 15. Preset Parameter Validation | v1.3 | 1/1 | Complete | 2026-06-08 |
| 16. Reset-to-Defaults | v1.3 | 1/1 | Complete | 2026-06-08 |
| 17. Fix stale Mood MkII catalog tests | v1.3 | 1/1 | Complete | 2026-06-08 |
| 18. Close gap: CBA-01/CBA-02 auto-populate controls | v1.3 | 1/1 | Complete | 2026-06-10 |
| 19. Close v1.3 verification gaps | v1.3 | 1/1 | Complete | 2026-06-10 |
| 20. Quick Wins & Dead Code | v1.4 | 1/1 | Complete | 2026-06-15 |
| 21. Concrete Types at the Plugin Boundary | v1.4 | 1/1 | Complete | 2026-06-15 |
| 22. Retire the Legacy Device Model | v1.4 | 1/1 | Complete | 2026-06-15 |
| 23. ApplyContext Consolidation & Test Capture Fixes | v1.4 | 1/1 | Complete | 2026-06-16 |
| 24. Close v1.4 gaps: Phase 21 verification, MC6 preset typing, QUAL-01 DeviceAction | v1.4 | 1/1 | Complete | 2026-06-17 |
| 25. I/O Parity | v1.5 | 1/1 | Complete   | 2026-06-17 |
| 26. Isolated Preset Apply | v1.5 | 1/1 | Complete   | 2026-06-17 |
| 27. Editor Protocol, CLI Surface & YAML Writer | v1.5 | 1/1 | Complete   | 2026-06-18 |
| 28. Editor Plugin Implementations | v1.5 | 1/1 | Complete | 2026-06-17 |
| 29. Catalog Integrity | v1.6 | 1/1 | Complete   | 2026-06-22 |
| 30. State Tracking Completeness | v1.6 | 0/1 | Pending | — |
| 31. MC6 Clear SysEx Fix | v1.6 | 0/1 | Pending | — |
| 32. Per-Parameter Plan Diffs | v1.6 | 0/1 | Pending | — |
| 33. Apply-01/02 Completions | v1.6 | 0/1 | Pending | — |
| 34. First-Class Scenes | v2.0 | 0/2 | Pending | — |
| 35. State Schema Versioning | v2.0 | 0/1 | Pending | — |
| 36. Plugin Authoring Guide | v2.0 | 0/1 | Pending | — |
| 37. PyPI Publishing + CI | v2.0 | 0/1 | Pending | — |
| 38. YAML Config Schema Documentation | v2.0 | 0/1 | Pending | — |
| 39. Reference Third-Party Plugin (rig-neuraldsp) | v2.0 | 0/2 | Pending | — |

## Next Milestone: v1.6 — Correctness & State Reliability

**Goal:** Fix all known correctness issues before the codebase is shared with anyone. The test suite must pass clean; `rig plan` must be trustworthy; the MC6 must behave correctly.

**Phases:** 29 (Catalog Integrity) → 30 (State Tracking) → 31 (MC6 Clear) → 32 (Per-Parameter Diffs) → 33 (Apply completions)

**After v1.6:** v2.0 Platform Foundations — scene decoupling, state schema versioning, plugin authoring guide, PyPI publishing, YAML schema docs, reference third-party plugin (rig-neuraldsp).

## Current State

Phases 1–28 shipped across v1.0–v1.5 (6 milestones). v1.6 is next — 5 phases planned (29-33).

**Milestone v1.5 shipped 2026-06-17:** 4 phases (25-28), 4 plans, 2,261 LOC Python in `packages/rig/src/`.

**Known issues entering v1.6:** 2 test failures (wet_bypass CC mismatch in catalog); `state.json` does not track preset-level changes; MC6 clear SysEx sends wrong bytes; `rig plan` shows "changed" without parameter detail.
