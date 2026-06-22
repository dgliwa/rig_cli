---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: — Correctness & State Reliability
status: planning
last_updated: "2026-06-22T12:02:34.471Z"
last_activity: 2026-06-21 — v1.6 and v2.0 milestones planned from critical assessment of codebase
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 5
  completed_plans: 5
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-17)

**Core value:** A single command brings the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.
**Current focus:** Phase 28 complete — milestone finished

## Current Position

Phase: v1.6 — Phase 30: State Tracking (not started)
Plan: —
Status: In progress — Phase 29 complete; ready to plan Phase 30
Last activity: 2026-06-22 — Phase 29 (Catalog Integrity) complete; 367 tests pass; named CC constants added to CBA catalog

## Performance Metrics

**Velocity:**

- Total plans completed: 32
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 1 | - | - |
| 02 | 2 | - | - |
| 03 | 4 | - | - |
| 04 | 4 | - | - |
| 05 | 6 | - | - |
| 06 | 2 | - | - |
| 07 | 3 | - | - |
| 08 | 3 | - | - |
| 09 | 4 | - | - |
| 10 | 1 | - | - |
| 11 | 1 | - | - |
| 12 | 1 | - | - |
| 14 | 1 | - | - |
| 15 | 1 | - | - |
| 16 | 1 | - | - |
| 17 | 1 | - | - |
| 18 | 1 | - | - |
| 19 | 1 | - | - |
| Phase 27-editor-protocol-cli-yaml-writer P01 | 420 | 4 tasks | 13 files |

## Decisions

### Phase 10 decisions

- **Device list order = signal chain** — no separate signal-chain.yaml; the devices list position defines chain order
- **Presets inline** — each device entry carries its own presets; parsed to correct model type
- **Scenes extracted from controller config** — controller holds scenes with bank/switch; loader extracts `presets`/`description`/`tags` to `Scene` model; controller-specific fields stay in device config
- **`config.type` is the entry point key** — plugin dispatch uses `config.type` (e.g. `"midi"`, `"chase_bliss"`), while device-level `type` is the `DeviceType` enum (`"digital"`, `"analog"`, `"modeler"`, `"controller"`)
- **`composes` is optional controller metadata** — validated against device IDs; not used for graph ordering (yet)

### v1.3 roadmap decisions

- **CBA-04 + CBA-01 + CBA-02 + CBA-03 grouped in Phase 14** — the `default` field on `Control` is a prerequisite for all catalog data to be complete; writing catalogs before the field exists would require an immediate follow-up pass; single phase avoids partial state
- **Validation (Phase 15) before reset (Phase 16)** — both phases consume catalog controls; validation naturally precedes any action that touches the device; convention from research
- **All three phases live in rig-chasebliss package** — no core changes; `Control` model change is additive and backward-compatible
- **Imperative validation in apply(), not Pydantic model_validator** — catalog lookup at model construction time would couple the model layer to the plugin; validation at apply time is correct

### v1.4 roadmap decisions

- **Phase 20 bundles all zero-dependency quick wins** — TYPE-04, TEST-01, QUAL-01, QUAL-02 share no intra-group dependencies and each is individually reversible; batching reduces phase count without coupling risk
- **TYPE-02 and TYPE-03 in same phase (Phase 21)** — concrete plugin config types and the Preset Protocol are co-dependent at the boundary; plugins need the Protocol to declare their preset lists, and the Protocol needs to be defined before the engine can reference it; doing them separately would leave the codebase in a half-typed state
- **TYPE-01 (retire legacy Device model) is its own phase (Phase 22)** — it is the most impactful change and depends on Phase 21 being complete; isolating it reduces blast radius and makes the phase easy to verify independently
- **TEST-02 bundled with TYPE-05 in Phase 23** — stdin-capture test failures are likely entangled with the dual ApplyContext types; resolving the context first gives the correct foundation for the ConfirmationIO Protocol fix

### v1.5 roadmap decisions

- **IO-01/IO-02 in their own phase (Phase 25)** — the v1.4 MILESTONES.md explicitly notes AnalogApplier bypasses ConfirmationIO as a deferred item; it is an isolated, low-risk fix with its own verification criterion (no `builtins.input` in any applier); folding it into Phase 26 would obscure the cleanup and make rollback harder
- **PRESET-01/02/03 grouped in Phase 26** — the three requirements are a single coherent feature: `--device`/`--preset` flags on `rig apply`; they cannot be partially delivered and verified independently
- **EDIT-01 folded into Phase 27 (not its own phase)** — the Protocol extension has no observable user behavior on its own; it is only verifiable when the CLI command exists to exercise it; keeping Protocol + CLI + YAML writer together makes Phase 27 the first phase where `rig edit` can be run end-to-end
- **EDIT-04/05 (save/discard) kept in Phase 27 with the CLI** — the YAML writer is the most novel piece of v1.5 (no existing write-back path), but it is inseparable from the CLI save/discard lifecycle; delivering the CLI without save/discard would leave an unusable stub
- **EDIT-03/06 in their own phase (Phase 28)** — plugin implementations depend on Phase 27's Protocol and CLI frame being stable; isolating them makes the blast radius of plugin-side changes smaller and keeps each plugin's behavior independently verifiable

## Accumulated Context

### Milestones

- **v1.0** (Phases 1-5): I/O Decoupling & Plugin Architecture — shipped 2026-06-07
- **v1.1** (Phases 6-8): Package Extraction & Plugin Isolation — shipped 2026-06-07
- **v1.2** (Phases 9-13): Cleaner Core — shipped 2026-06-08
- **v1.3** (Phases 14-19): Chase Bliss Pedal Support — shipped 2026-06-10 — CBA catalog expansion (Mood MkII, Wombtone MkII, Brothers AM), preset parameter validation, reset-to-defaults flow, catalog auto-population from device model name
- **v1.4** (Phases 20-24): Architecture & Type Integrity — shipped 2026-06-17 — retired legacy Device model, concrete plugin types, Preset Protocol, deleted dead plan()/diff() stubs, ConfirmationIO threaded through CBA, ActionStatus enum

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260610-vae | Remove controls from ChaseBlissConfig, resolve from catalog at call sites | 2026-06-10 | 63ddd9d | [260610-vae-remove-controls-from-chaseblissconfig](.planning/quick/260610-vae-remove-controls-from-chaseblissconfig/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Plugin | `generate_mc6` should read scenes from MC6 config instead of `Rig.scenes` | resolved — removed in Phase 12 | Phase 10 |
| Plugin | MC6 apply could leverage `composes` data | resolved — removed in Phase 12 | Phase 10 |
| Validation | CBA validation skips already-saved presets (state-gating) — edited YAML params not re-validated until state reset | 🟡 Acknowledged | v1.3 |
| Reset | `_send_reset_ccs()` lacks `connected_devices` gate — asymmetric with `_send_ccs()` (non-blocking, exceptions caught) | 🟡 Acknowledged | v1.3 |
| I/O | AnalogApplier bypasses `ConfirmationIO` — `prompt_analog()` still calls `input()` directly | ✅ Scheduled Phase 25 | v1.4 |

## Operator Next Steps

- Run `/gsd-plan-phase 29` to create the Phase 29 (Catalog Integrity) plan — first thing that unblocks everything else
- Phase 29 is the unlock: 2 test failures must be clean before v1.6 is credible
- v1.6 goal: correctness and trustworthy state before sharing the tool with anyone
- v2.0 goal: scene decoupling + PyPI + plugin authoring guide = shareable platform
