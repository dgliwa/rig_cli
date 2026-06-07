# Roadmap: rig-cli

## Milestones

- ✅ **v1.0 I/O Decoupling & Plugin Architecture** — Phases 1-5 (shipped 2026-06-07)
- 🔄 **v1.1 Package Extraction & Plugin Isolation** — Phases 6-8 (started 2026-06-07)

## Phases

<details>
<summary>✅ v1.0 I/O Decoupling & Plugin Architecture (Phases 1-5) — SHIPPED 2026-06-07</summary>

- [x] Phase 1: CBA Tech-Debt Cleanup (1/1 plans) — completed 2026-06-04
- [x] Phase 2: Engine I/O Decoupling (2/2 plans) — completed 2026-06-05
- [x] Phase 3: Core Domain Refactor (4/4 plans) — completed 2026-06-05
- [x] Phase 4: Plugin Migration (4/4 plans) — completed 2026-06-06
- [x] Phase 5: Dependency Graph & Plan Command (6/6 plans) — completed 2026-06-07

</details>

<details open>
<summary>🔄 v1.1 Package Extraction & Plugin Isolation (Phases 6-8) — IN PROGRESS</summary>

- [x] **Phase 6: Core Package & Entry Point Discovery** (2/2 plans) — completed 2026-06-07
  - Goal: `rig` discovers devices via `importlib.metadata.entry_points('rig.devices')` with zero hard imports
  - Requirements: CORE-01, CORE-02, CORE-03, CORE-04
  - Success criteria achieved:
    1. `rig` CLI works without any device plugins installed ✓
    2. Installing `rig-analog` makes analog devices available to `rig` ✓
    3. `PluginRegistry` loads from entry points (single path per D-03) ✓
    4. All 302 tests pass under new package structure ✓

- [ ] **Phase 7: Plugin Package Wiring & Device-Level MIDI** — Ensure all 4 plugin packages register correctly via entry points; move MIDI connection management to device level for Chase Bliss and Morningstar
  - Goal: Each device plugin is independently installable and manages its own MIDI lifecycle
  - Requirements: ANLG-01, CHASE-01, MC6-01, HX-01
  - Success criteria:
    1. `pip install rig-analog && rig ...` discovers analog device without importing core
    2. `pip install rig-chasebliss && rig ...` discovers Chase Bliss device, setup phases use device-level MIDI
    3. `pip install rig-morningstar && rig ...` discovers MC6 device, bank/switch config uses device-level MIDI
    4. `pip install rig-hx && rig ...` discovers HX Stomp device
    5. Engine no longer manages MIDI connections for plugin devices — devices handle their own
  - **Context:** WIP has `packages/rig-*/pyproject.toml` with entry point stubs — needs proper MIDI lifecycle in ChaseBlissDevice and MC6Device

- [ ] **Phase 8: Build, CI & Plugin Authoring Docs** — Independent versioning, editable installs, CI pipeline per package, plugin authoring documentation
  - Goal: Each package independently releasable; clear docs for adding new device plugins
  - Requirements: BUILD-01, BUILD-02, BUILD-03, DOCS-01
  - Success criteria:
    1. `pip install -e packages/rig-*` works for each package
    2. CI builds and lint-tests each package independently
    3. CI publishes each package to PyPI on tag
    4. Plugin authoring guide exists at `docs/plugin-authoring.md`
    5. A new "hello world" device plugin can be written following the guide in < 10 minutes

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. CBA Tech-Debt Cleanup | v1.0 | 1/1 | Complete | 2026-06-04 |
| 2. Engine I/O Decoupling | v1.0 | 2/2 | Complete | 2026-06-05 |
| 3. Core Domain Refactor | v1.0 | 4/4 | Complete | 2026-06-05 |
| 4. Plugin Migration | v1.0 | 4/4 | Complete | 2026-06-06 |
| 5. Dependency Graph & Plan Command | v1.0 | 6/6 | Complete | 2026-06-07 |
| 6. Core Package & Entry Point Discovery | v1.1 | 2/2 | Complete | 2026-06-07 |
| 7. Plugin Package Wiring & Device-Level MIDI | v1.1 | 3/0 | Planned | — |
| 8. Build, CI & Plugin Authoring Docs | v1.1 | 0/0 | Not started | — |
