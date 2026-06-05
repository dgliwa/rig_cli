# Roadmap: rig-cli — I/O Decoupling & Core Architecture

## Overview

Five-phase milestone: clean CBA tech-debt (done), decouple apply engine I/O (done), then rebuild the domain around a graph-based device model with a plugin registry, migrate existing appliers to plugins, and ship a trustworthy `rig plan` command driven by the dependency graph.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: CBA Tech-Debt Cleanup** - Remove private-symbol leakage and raw dict mutation in ChaseBlissApplier before protocol work begins (completed 2026-06-04)
- [x] **Phase 2: Engine I/O Decoupling** - Introduce three narrow Protocol ports so the apply engine is fully testable without MIDI hardware (completed 2026-06-05)
- [ ] **Phase 3: Core Domain Refactor** - Rebuild the domain around a graph-based device model with a Controller type, config/behavior separation, and a plugin registry interface
- [ ] **Phase 4: Plugin Migration** - Migrate existing appliers (CBA, MC6, HX Stomp, Analog) to the plugin architecture; CLI and engine route through registry
- [ ] **Phase 5: Dependency Graph & Plan Command** - Build apply ordering from graph topology, detect unused/missing presets, ship `rig plan` driven by dependency-sorted actions

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

- [x] 02-01-PLAN.md — Create ports.py (Protocols + adapters), fakes.py, update ApplyContext + appliers (DEC-01/02/03/04)
- [x] 02-02-PLAN.md — Wire adapters into apply_plan and CLI, fix scene-write bug, rewrite patched tests (DEC-05/06/07)

### Phase 3: Core Domain Refactor

**Goal**: The rig is modeled as a directed graph of `Device` nodes with `Controller` as a special root type; config objects are pure data; behavior (plan/diff/apply) lives in plugin services registered against a `DevicePlugin` protocol; no existing behavior regresses
**Depends on**: Phase 2
**Requirements**: TBD (gather in discuss phase)
**Success Criteria** (what must be TRUE):

  1. A `DeviceGraph` type models devices as nodes with directed edges; `Controller` is a root-node subtype that owns `scenes`; a device can satisfy both roles (e.g. HX Stomp references its own presets in scenes)
  2. A `DevicePlugin` protocol defines `plan(device, context)`, `diff(device, context)`, `apply(device, context)` — no behavior lives on domain models
  3. A `PluginRegistry` maps device config type strings to `DevicePlugin` implementations; existing appliers are not yet migrated (that is Phase 4), but the registry exists and is wirable
  4. All existing tests pass; the loader produces the new graph structure from existing YAML without requiring config-repo changes

**Plans**: 4 plans

Plans:

- [ ] 03-P1-PLAN.md — Add ControllerConfig + DeviceType.CONTROLLER to device.py; controller.py compat shim; migrate sample_rig fixture (D-04, D-06)
- [x] 03-P2-PLAN.md — Remove controller/scenes fields from Rig; add apply_order() + compat properties; fix test_models + test_mc6_generator (D-01, D-02, D-03, D-05)
- [ ] 03-P3-PLAN.md — Update loader to route controller YAML through _parse_device; inject scenes into ControllerConfig; fix test_loader (D-06, D-07)
- [x] 03-P4-PLAN.md — Create engine/plugin.py (DevicePlugin Protocol + PluginContext); engine/plugin_registry.py (PluginRegistry empty); tests/test_plugin.py (D-08, D-09, D-10)

### Phase 4: Plugin Migration

**Goal**: All existing appliers (AnalogApplier, MidiApplier, ChaseBlissApplier, MC6Applier) are re-registered as `DevicePlugin` implementations; the engine routes exclusively through the registry; no direct applier imports remain in CLI or engine
**Depends on**: Phase 3
**Requirements**: TBD
**Success Criteria** (what must be TRUE):

  1. Each applier module exports a `DevicePlugin`-compliant class registered under its config type key
  2. `apply.py` calls `registry.get(device.config.type).apply(...)` — no `isinstance` dispatch
  3. All existing apply behavior is preserved end-to-end; test suite passes

**Plans**: TBD

### Phase 5: Dependency Graph & Plan Command

**Goal**: `rig plan` outputs a dependency-sorted, read-only preview of required changes; apply ordering respects graph topology; unused and missing preset references are surfaced
**Depends on**: Phase 4
**Requirements**: TBD
**Success Criteria** (what must be TRUE):

  1. `DeviceGraph.apply_order()` returns devices in topological order (controllers after their dependencies); cycle detection raises a clear error
  2. `rig plan` identifies unused presets (defined but never referenced in any scene) and missing presets (referenced in scenes but not defined)
  3. `rig plan` exits non-zero when changes are detected, `0` when up to date; `--format json` emits stable output; cold-start warning when `.rig/state.json` absent
  4. `rig plan` human-readable output uses visual markers (`~` configure, `✓` verify, `⚠` analog, `·` no change) with a summary line

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CBA Tech-Debt Cleanup | 1/1 | Complete    | 2026-06-04 |
| 2. Engine I/O Decoupling | 2/2 | Complete    | 2026-06-05 |
| 3. Core Domain Refactor | 2/4 | In Progress|  |
| 4. Plugin Migration | 0/TBD | Not started | - |
| 5. Dependency Graph & Plan Command | 0/TBD | Not started | - |
