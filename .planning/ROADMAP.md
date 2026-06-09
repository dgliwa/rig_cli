# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- ✅ **v1.2 Cleaner Core** — Phases 9-13 (shipped 2026-06-08)
- **v1.3 Chase Bliss Pedal Support** — Phases 14-16 (active)

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

### v1.3 Chase Bliss Pedal Support (Phases 14-16)

- [x] **Phase 14: CBA Catalog Expansion** (1/1 plans) — completed 2026-06-08
- [x] **Phase 15: Preset Parameter Validation** (1/1 plans) — completed 2026-06-08
- [x] **Phase 16: Reset-to-Defaults** (1/1 plans) — completed 2026-06-08 - Send all resettable controls to default CC values before applying preset CCs

## Phase Details

### Phase 14: CBA Catalog Expansion

**Goal**: The Control model carries a default value and all three CBA pedal catalogs are complete and correct
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: CBA-04, CBA-01, CBA-02, CBA-03
**Success Criteria** (what must be TRUE):

  1. `Control` instances can be constructed with a `default` float or `None`; existing Control construction without `default` continues to work unchanged
  2. Footswitch and utility controls in all catalogs have `default=None`; parameter controls have a numeric default matching the pedal's factory setting
  3. `WOMBTONE_MKII_CONTROLS` is present in the catalog module with all 8 parameter controls (CC14-21) populated with correct CC numbers, ranges, and defaults
  4. `BROTHERS_AM_CONTROLS` is present with all 24 controls (8 knobs, 3 toggles, 15 dip switches) populated with correct CC numbers, ranges, and defaults
  5. Mood MkII catalog contains CC24-29, CC31-33, and CC52; CC102 maps to `wet_bypass` and CC103 to `loop_bypass`; all existing controls have `default=` values

**Plans**: 1 (01)

### Phase 15: Preset Parameter Validation

**Goal**: Applying a CBA preset with an unknown or out-of-range parameter fails immediately with a clear error, before any physical device interaction
**Depends on**: Phase 14
**Requirements**: CBA-05
**Success Criteria** (what must be TRUE):

  1. Applying a preset with a parameter name not in the device catalog raises `ValidationError` with a message that names the offending parameter
  2. Applying a preset with a parameter value outside the control's `min`/`max` range raises `ValidationError` with a message that includes the value and the allowed range
  3. Validation runs before the user is prompted to navigate to a preset slot on the pedal — no physical interaction is required before an error is surfaced
  4. Validation runs in dry-run mode, not only on live apply

**Plans**: 1 (01)

### Phase 16: Reset-to-Defaults

**Goal**: Before each preset's CC values are sent to a CBA pedal, all resettable controls are first driven to their catalog default, ensuring clean preset creation
**Depends on**: Phase 15
**Requirements**: CBA-06
**Success Criteria** (what must be TRUE):

  1. When applying a CBA preset, a batch of CC messages for all controls with a non-None default is sent before the preset's own CC messages
  2. Footswitch and utility controls (those with `default=None`) are excluded from the reset batch — no spurious CC messages are sent for them
  3. Reset fires per-preset, immediately before that preset's CC messages, not once per apply session

**Plans**: 1 (01)

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

### Phase 17: Fix stale Mood MkII catalog tests

**Goal:** Two stale assertions in `TestMoodMkiiCatalog` updated to match the Phase 14 Mood MkII catalog expansion (13 knobs; wet_bypass=CC102, loop_bypass=CC103)
**Requirements**: CBA-03
**Depends on:** Phase 16
**Plans:** 1 plan

Plans:

- [ ] 17-01: Fix stale TestMoodMkiiCatalog assertions and verify full suite green

### Phase 18: Close gap: CBA-01/CBA-02 — auto-populate controls from catalog in device loading

**Goal:** When a CBA device YAML specifies `config.model: <Model Name>`, controls are auto-populated from the catalog — no manual inlining required
**Requirements**: CBA-01, CBA-02
**Depends on:** Phase 17
**Plans:** 1 plan

Plans:

- [ ] 18-01: Add `model` field to ChaseBlissConfig and wire get_controls() into from_raw_yaml()
