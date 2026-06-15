# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- ✅ **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (shipped 2026-06-07)
- ✅ **v1.2 Cleaner Core** — Phases 9-13 (shipped 2026-06-08)
- ✅ **v1.3 Chase Bliss Pedal Support** — Phases 14-19 (shipped 2026-06-10)
- 🔄 **v1.4 Architecture & Type Integrity** — Phases 20-23 (in progress)

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

### v1.4 Architecture & Type Integrity

- [ ] **Phase 20: Quick Wins & Dead Code** - Remove dead stubs, delete stale tests, and lock in enum and documentation decisions with no dependencies on other work
- [ ] **Phase 21: Concrete Types at the Plugin Boundary** - Each plugin carries a typed config and typed preset list; Preset Protocol lives in core
- [x] **Phase 22: Retire the Legacy Device Model** - The legacy Device(BaseModel) is gone; Rig.devices is typed against the Protocol end-to-end (completed 2026-06-15)
- [ ] **Phase 23: ApplyContext Consolidation & Test Capture Fixes** - Single ApplyContext flows through apply.py; all tests pass without flags

## Phase Details

### Phase 20: Quick Wins & Dead Code

**Goal**: The codebase has no dead stubs, no broken test infrastructure, and a recorded decision on the Enums-vs-Literals question — all independent changes with zero cross-phase risk
**Depends on**: Phase 19 (v1.3 complete)
**Requirements**: TYPE-04, TEST-01, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):

  1. `plan()` and `diff()` methods no longer appear in the Device Protocol or any plugin implementation; a grep for these method names in non-test source returns zero hits
  2. `make test` completes collection with no import errors — the stale root `tests/` directory is gone
  3. A grep for `== "analog"`, `== "digital"`, `== "controller"`, `== "modeler"` in `src/` returns zero hits; all comparisons use `DeviceType` enum members
  4. The Enums-vs-Literals TODO comment is replaced with an inline explanation: `Literal` is required by Pydantic discriminated unions; `DeviceType` StrEnum is for runtime comparisons; they coexist intentionally

**Plans**: TBD

### Phase 21: Concrete Types at the Plugin Boundary

**Goal**: Every plugin device class carries a concrete, named config type and a typed preset list; the `Preset` Protocol exists in core so the engine never sees `list[Any]`
**Depends on**: Phase 20
**Requirements**: TYPE-02, TYPE-03
**Success Criteria** (what must be TRUE):

  1. Each plugin device class (`ChaseBlissDevice`, `HXStompDevice`, `AnalogDevice`, `MC6Device`) declares `config: <ConcreteConfig>` — no `config: Any` annotations remain in plugin source
  2. A `Preset` Protocol is defined in `rig.engine.plugin` (or equivalent core module) with the minimal interface the engine requires
  3. Each plugin device class declares `presets: list[Preset]`; mypy or grep confirms no `list[Any]` in plugin preset fields
  4. YAML construction for each device type validates against the concrete config type — a YAML with an invalid field raises a validation error, not an `AttributeError` at runtime

**Plans**: TBD

### Phase 22: Retire the Legacy Device Model

**Goal**: The legacy `Device(BaseModel)` in `models/device.py` is gone; `Rig.devices` is typed `dict[str, Device]` against the Protocol; all code paths touching `rig.devices` are type-safe without `Any` or `hasattr` guards
**Depends on**: Phase 21
**Requirements**: TYPE-01
**Success Criteria** (what must be TRUE):

  1. `models/device.py` no longer contains a Pydantic `BaseModel` subclass named `Device`; the file is removed or repurposed
  2. `Rig.devices` is typed `dict[str, Device]` where `Device` is the Protocol from `rig.engine.plugin`
  3. A grep for `hasattr` and `cast(Any` in engine and loader source returns zero hits introduced by this change
  4. `make test` passes with no regressions after the legacy model is removed

**Plans**: TBD

### Phase 23: ApplyContext Consolidation & Test Capture Fixes

**Goal**: `apply.py` flows one `ApplyContext` type end-to-end; the 3 failing stdin-capture tests pass without `-s` by routing interaction through the `ConfirmationIO` Protocol
**Depends on**: Phase 22
**Requirements**: TYPE-05, TEST-02
**Success Criteria** (what must be TRUE):

  1. `appliers/base.py` no longer exports a legacy `ApplyContext` dataclass; `apply.py` imports and uses `DeviceApplyContext` from `engine.plugin` exclusively
  2. No function in `apply.py` or any applier accepts both context types; a grep for the old `ApplyContext` import in engine source returns zero hits
  3. `test_build_preset_confirm_…`, `test_midi_connect_and_send`, and `test_cba_channel_establishment_…` all pass when run with `make test` (no `-s` flag)
  4. The interaction functions that previously called `input()` directly now delegate to the `ConfirmationIO` Protocol; test doubles can inject a fake implementation without monkeypatching builtins

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
| 20. Quick Wins & Dead Code | v1.4 | 0/? | Not started | - |
| 21. Concrete Types at the Plugin Boundary | v1.4 | 0/? | Not started | - |
| 22. Retire the Legacy Device Model | v1.4 | 1/1 | Complete   | 2026-06-15 |
| 23. ApplyContext Consolidation & Test Capture Fixes | v1.4 | 0/? | Not started | - |
