# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- ✅ **v1.2 Cleaner Core** — Phases 9-13 (shipped 2026-06-08)
- ✅ **v1.3 Chase Bliss Pedal Support** — Phases 14-19 (shipped 2026-06-10)
- ✅ **v1.4 Architecture & Type Integrity** — Phases 20-24 (shipped 2026-06-17)
- 🔄 **v1.5 Interactive Preset Management** — Phases 25-28 (in progress)

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
<summary>🔄 v1.5 Interactive Preset Management (Phases 25-28) — IN PROGRESS</summary>

- [ ] **Phase 25: I/O Parity** - Thread ConfirmationIO through AnalogApplier; update tests to use InMemoryPromptAdapter
- [ ] **Phase 26: Isolated Preset Apply** - `rig apply --device <id> --preset <id>` applies one device's preset without full scene setup
- [ ] **Phase 27: Editor Protocol, CLI Surface & YAML Writer** - `rig edit` command, save/discard lifecycle, and rig.yaml preset writer
- [ ] **Phase 28: Editor Plugin Implementations** - CC-based live MIDI editing (CBA/MIDI/HX) and analog prompt-per-control flow

</details>

## Phase Details

### Phase 25: I/O Parity
**Goal**: Analog device prompts flow through the same ConfirmationIO abstraction as all other prompts — no raw `input()` calls remain in any applier
**Depends on**: Phase 24 (ConfirmationIO Protocol and InMemoryPromptAdapter already exist in v1.4)
**Requirements**: IO-01, IO-02
**Success Criteria** (what must be TRUE):
  1. Running `rig apply` with an analog device never calls `builtins.input` directly — all prompts go through `ConfirmationIO.prompt()`
  2. AnalogApplier tests pass without monkeypatching `builtins.input` — they instantiate `InMemoryPromptAdapter` and pass it through context
  3. The test suite passes with no stdin-capture flags required for analog tests
**Plans**: TBD

### Phase 26: Isolated Preset Apply
**Goal**: Users can apply a single device's preset without triggering full scene setup — useful for mid-session tweaks and targeted reapplies
**Depends on**: Phase 25
**Requirements**: PRESET-01, PRESET-02, PRESET-03
**Success Criteria** (what must be TRUE):
  1. User can run `rig apply --device <id> --preset <id>` and only that device is activated — all other devices are skipped
  2. After a targeted apply, `state.json` reflects the updated preset for the targeted device only — other device states are unchanged
  3. Running `rig apply --device <id> --preset <id>` with an unknown device or preset ID produces a clear error message
  4. Running `rig apply` without `--device`/`--preset` flags behaves exactly as before (no regression)
**Plans**: TBD

### Phase 27: Editor Protocol, CLI Surface & YAML Writer
**Goal**: Users can enter editor mode for a device's preset via `rig edit`, and the save/discard lifecycle writes changes back to rig.yaml atomically
**Depends on**: Phase 26
**Requirements**: EDIT-01, EDIT-02, EDIT-04, EDIT-05
**Success Criteria** (what must be TRUE):
  1. `rig edit <device-id> <preset-id>` launches editor mode for the named preset — the command exists and routes correctly
  2. When the user confirms a save, the updated preset values are written back to `rig.yaml` and can be loaded by `rig validate` without error
  3. When the user discards, `rig.yaml` is bit-for-bit identical to its state before `rig edit` was run
  4. The Device Protocol (or companion EditorProtocol) declares `edit(preset_id, ctx)` — plugins can implement it without touching core
**Plans**: TBD

### Phase 28: Editor Plugin Implementations
**Goal**: Each device plugin delivers its own interactive editing behavior — CC-based plugins stream live values; analog plugin presents a prompt-per-control flow
**Depends on**: Phase 27
**Requirements**: EDIT-03, EDIT-06
**Success Criteria** (what must be TRUE):
  1. During CBA/MIDI editor mode, changing a control value immediately sends the corresponding CC message to the device — the user hears the change live
  2. Analog plugin editor mode walks the user through each control with a prompt — no MIDI is sent (manual set); the plugin owns this loop entirely
  3. After any plugin's editor session saves, `rig validate` confirms the written values are valid preset parameters
**Plans**: TBD

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
| 25. I/O Parity | v1.5 | 0/? | Not started | - |
| 26. Isolated Preset Apply | v1.5 | 0/? | Not started | - |
| 27. Editor Protocol, CLI Surface & YAML Writer | v1.5 | 0/? | Not started | - |
| 28. Editor Plugin Implementations | v1.5 | 0/? | Not started | - |
