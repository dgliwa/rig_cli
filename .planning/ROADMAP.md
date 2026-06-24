# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- ✅ **v1.2 Cleaner Core** — Phases 9-13 (shipped 2026-06-08)
- ✅ **v1.3 Chase Bliss Pedal Support** — Phases 14-19 (shipped 2026-06-10)
- ✅ **v1.4 Architecture & Type Integrity** — Phases 20-24 (shipped 2026-06-17)
- ✅ **v1.5 Interactive Preset Management** — Phases 25-28 (shipped 2026-06-17)
- ✅ **v1.6 Correctness & State Reliability** — Phases 29-33 (shipped 2026-06-24)
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

<details>
<summary>✅ v1.5 Interactive Preset Management (Phases 25-28) — SHIPPED 2026-06-17</summary>

- [x] Phase 25: I/O Parity — Thread ConfirmationIO through AnalogApplier; update tests to use InMemoryPromptAdapter (1/1 plans) — completed 2026-06-17
- [x] Phase 26: Isolated Preset Apply — `rig apply --device <id> --preset <id>` applies one device's preset without full scene setup (1/1 plans) — completed 2026-06-17
- [x] Phase 27: Editor Protocol, CLI Surface & YAML Writer — `rig edit` command, save/discard lifecycle, and rig.yaml preset writer (1/1 plans) — completed 2026-06-18
- [x] Phase 28: Editor Plugin Implementations — CC-based live MIDI editing (CBA/MIDI/HX) and analog prompt-per-control flow (1/1 plans) — completed 2026-06-17

</details>

<details>
<summary>✅ v1.6 Correctness & State Reliability (Phases 29-33) — SHIPPED 2026-06-24</summary>

- [x] Phase 29: Catalog Integrity — fix wet_bypass/loop_bypass CC mismatch; named constants; catalog as single source of truth (1/1 plans) — completed 2026-06-22
- [x] Phase 30: State Tracking Completeness — `state.json` tracks actual preset changes per device; `rig plan` suppresses false-positive CHANGED (1/1 plans) — completed 2026-06-22
- [x] Phase 31: MC6 Clear SysEx Fix — `clear_preset_messages()` defaults to `save=True` for flash persistence, matching MC6 web UI (1/1 plans) — completed 2026-06-22
- [x] Phase 32: Per-Parameter Plan Diffs — `rig plan` shows before/after CC values and knob positions per device-action (1/1 plans) — completed 2026-06-22
- [x] Phase 33.1: Apply-01/02 Completions — skip analog prompt when state matches; `--device` alone applies cross-scene (1/1 plans) — completed 2026-06-24

</details>

<details open>
<summary>⬜ v2.0 Platform Foundations (Phases 34-39) — PLANNED</summary>

- [ ] **Phase 34: First-Class Scenes** — decouple scenes from controller device config; scenes defined at top level in `rig.yaml`; rigs without a controller can have scenes
- [ ] **Phase 35: State Schema Versioning** — `state.json` carries `schema_version`; migration on load; silent field additions no longer silently corrupt plan diffs
- [ ] **Phase 36: Plugin Authoring Guide (PKG-07)** — `PLUGIN-AUTHORING.md` covering Device Protocol, entry points, `from_raw_yaml`, setup/apply/edit lifecycle; example minimal plugin skeleton committed to repo
- [ ] **Phase 37: PyPI Publishing + CI** — GitHub Actions workflow publishes all 5 packages to PyPI on tag; version matrix; `pip install rig rig-chasebliss` works
- [ ] **Phase 38: YAML Config Schema Documentation** — formal `rig.yaml` reference: every key, type, required/optional, validation rules, example snippets
- [ ] **Phase 39: Reference Third-Party Plugin (rig-neuraldsp)** — stub Neural DSP Quad Cortex plugin that demonstrates the full plugin contract; lives in its own repo; linked from authoring guide as "hello world"

</details>

## Phase Details

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
| 25. I/O Parity | v1.5 | 1/1 | Complete | 2026-06-17 |
| 26. Isolated Preset Apply | v1.5 | 1/1 | Complete | 2026-06-17 |
| 27. Editor Protocol, CLI Surface & YAML Writer | v1.5 | 1/1 | Complete | 2026-06-18 |
| 28. Editor Plugin Implementations | v1.5 | 1/1 | Complete | 2026-06-17 |
| 29. Catalog Integrity | v1.6 | 1/1 | Complete | 2026-06-22 |
| 30. State Tracking Completeness | v1.6 | 1/1 | Complete | 2026-06-22 |
| 31. MC6 Clear SysEx Fix | v1.6 | 1/1 | Complete | 2026-06-22 |
| 32. Per-Parameter Plan Diffs | v1.6 | 1/1 | Complete | 2026-06-22 |
| 33.1. Apply-01/02 Completions | v1.6 | 1/1 | Complete | 2026-06-24 |
| 34. First-Class Scenes | v2.0 | 0/2 | Pending | — |
| 35. State Schema Versioning | v2.0 | 0/1 | Pending | — |
| 36. Plugin Authoring Guide | v2.0 | 0/1 | Pending | — |
| 37. PyPI Publishing + CI | v2.0 | 0/1 | Pending | — |
| 38. YAML Config Schema Documentation | v2.0 | 0/1 | Pending | — |
| 39. Reference Third-Party Plugin (rig-neuraldsp) | v2.0 | 0/2 | Pending | — |

## Current State

Phases 1–33.1 shipped across v1.0–v1.6 (7 milestones). Next: v2.0 Platform Foundations — 6 phases planned (34-39).

**Milestone v1.6 shipped 2026-06-24:** 5 phases (29-33.1), 5 plans, ~10,961 LOC Python, 399 tests pass, 0 failures.

**Next milestone v2.0:** scene decoupling, state schema versioning, plugin authoring guide, PyPI publishing, YAML schema docs, reference third-party plugin (rig-neuraldsp).
