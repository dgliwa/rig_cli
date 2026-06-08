# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- 🔲 **v1.2 Cleaner Core** — Phases 9-11 (in progress)

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

- [x] **Phase 6: Core Package & Entry Point Discovery** (2/2 plans) — completed 2026-06-07
  - Goal: `rig` discovers devices via `importlib.metadata.entry_points('rig.devices')` with zero hard imports
  - Requirements: CORE-01, CORE-02, CORE-03, CORE-04
  - Success criteria achieved:
    1. `rig` CLI works without any device plugins installed ✓
    2. Installing `rig-analog` makes analog devices available to `rig` ✓
    3. `PluginRegistry` loads from entry points (single path per D-03) ✓
    4. All 302 tests pass under new package structure ✓

- [x] **Phase 7: Plugin Package Wiring & Device-Level MIDI** — Ensure all 4 plugin packages register correctly via entry points; move MIDI connection management to device level for Chase Bliss and Morningstar (completed 2026-06-07)
  - Goal: Each device plugin is independently installable and manages its own MIDI lifecycle
  - Requirements: ANLG-01, CHASE-01, MC6-01, HX-01
  - Success criteria:
    1. `pip install rig-analog && rig ...` discovers analog device without importing core
    2. `pip install rig-chasebliss && rig ...` discovers Chase Bliss device, setup phases use device-level MIDI
    3. `pip install rig-morningstar && rig ...` discovers MC6 device, bank/switch config uses device-level MIDI
    4. `pip install rig-hx && rig ...` discovers HX Stomp device
    5. Engine no longer manages MIDI connections for plugin devices — devices handle their own
  - **Context:** WIP has `packages/rig-*/pyproject.toml` with entry point stubs — needs proper MIDI lifecycle in ChaseBlissDevice and MC6Device

- [x] **Phase 8: Core Cleanup — Dead Code & Plugin Isolation** (3/3 plans) — completed 2026-06-07
  - Goal: Core has zero hard dependencies on plugin-specific code; no dead code in `packages/rig`
  - Requirements: CLEANUP-01, CLEANUP-02, CLEANUP-03, CLEANUP-04
  - Success criteria achieved:
    1. `rig/midi/mc6.py` deleted — tests use `rig_morningstar.sysex` ✓
    2. `rig/generators/mc6_presets.py` deleted — tests use `rig_morningstar.generator` ✓
    3. `rig/catalog/chase_bliss.py` deleted — tests use `rig_chasebliss.catalog` ✓
    4. `rig/engine/appliers/chase_bliss.py` deleted — tests use `rig_chasebliss.applier` ✓
    5. `rig/interaction/cba.py` moved to `rig-chasebliss` — plugin owns CBA prompts ✓
    6. `rig/interaction/analog.py` moved to `rig-analog` — plugin owns analog prompts ✓
    7. `rig/models/controller.py` deleted — `ControllerConfig` stays in `device.py` ✓
    8. All 300+ tests pass (300 passing) with zero hard plugin deps from core ✓

</details>

### v1.2 Cleaner Core (Phases 9-11)

- [ ] **Phase 9: Core Model Cleanup** - Strip all plugin-specific types and compat shims from core models
- [ ] **Phase 10: Schema & Loader Rewrite** - Implement single-file rig.yaml schema and rewrite the loader
- [ ] **Phase 11: Dead Code & Compat Removal** - Sweep all TODO:1.2 markers and remove multi-file config support

## Phase Details

### Phase 9: Core Model Cleanup
**Goal**: Core models contain no plugin-specific types, no compat shims, and no deprecated fields — the domain is expressed purely through `type`-keyed device identity and the new schema primitives
**Depends on**: Phase 8 (v1.1 dead code eliminated)
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, SCHEMA-03, SCHEMA-06
**Success Criteria** (what must be TRUE):
  1. `device.py` imports contain no `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, or `ControllerConfig` — grep returns zero hits
  2. `Control` and `ControlType` classes are absent from `packages/rig/src/rig/models/`
  3. `Rig` model has no `pedals`, `digital_presets`, `hx_presets`, `analog_presets`, `mc6`, or `_controller_device` attributes
  4. `Scene` model has no `mc6_bank` or `mc6_switch` fields
  5. `SignalChainPosition` class is absent from `packages/rig/src/rig/models/signal_chain.py` (file may be deleted or emptied)
**Plans**: TBD

### Phase 10: Schema & Loader Rewrite
**Goal**: Users can run `rig validate` against a single `rig.yaml` where device list order defines the signal chain, controller devices compose other devices by ID, and scenes live inside the controller
**Depends on**: Phase 9
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-04, SCHEMA-05, LOADER-01, LOADER-02
**Success Criteria** (what must be TRUE):
  1. `rig validate path/to/rig.yaml` succeeds when `rig.yaml` is a single file with a flat `devices` list
  2. Device list order in `rig.yaml` is treated as the signal chain — no `signal-chain.yaml` file is read or required
  3. A controller device with `composes: [device_id_1, device_id_2]` correctly references the devices it controls
  4. Scenes defined inside a controller device with `bank`, `switch`, and `presets: {device_id: preset_id}` are loaded and accessible via `Rig.scenes`
  5. Device construction is dispatched to the matching plugin using the `type` field as the entry point lookup key — unknown `type` values produce a clear error
**Plans**: TBD
**UI hint**: no

### Phase 11: Dead Code & Compat Removal
**Goal**: The codebase contains no `TODO: 1.2` markers, no multi-file config parsing paths, and no code that was retained solely for backwards compatibility with the pre-v1.2 config layout
**Depends on**: Phase 10
**Requirements**: CLEANUP-01, CLEANUP-02
**Success Criteria** (what must be TRUE):
  1. `grep -r "TODO.*1\.2" packages/rig/src/` returns zero results
  2. `load_rig()` has no code paths that read `signal-chain.yaml`, `scenes/*.yaml`, `pedals/*.yaml`, or `mc6.yaml` — the function accepts only a single `rig.yaml` path
  3. All tests pass after removal — no test fixture depends on multi-file layout
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
| 9. Core Model Cleanup | v1.2 | 0/? | Not started | - |
| 10. Schema & Loader Rewrite | v1.2 | 0/? | Not started | - |
| 11. Dead Code & Compat Removal | v1.2 | 0/? | Not started | - |
