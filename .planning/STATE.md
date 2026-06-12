---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Architecture & Type Integrity
status: Phase 20 complete, Phase 21 next
last_updated: "2026-06-12"
last_activity: "2026-06-12 — Phase 20 (quick-wins-dead-code) complete"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 1
  completed_plans: 1
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-10)

**Core value:** A single command brings the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.
**Current focus:** v1.4 Architecture & Type Integrity — roadmap defined, Phase 20 next

## Current Position

Phase: 20 (not started)
Plan: —
Status: Roadmap defined, ready for Phase 20
Last activity: 2026-06-12 — v1.4 roadmap created (4 phases: 20-23)

Progress: [░░░░░░░░░░░░░░░░░░░░] 0% (0/4 phases)

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

## Accumulated Context

### Milestones

- **v1.0** (Phases 1-5): I/O Decoupling & Plugin Architecture — shipped 2026-06-07
- **v1.1** (Phases 6-8): Package Extraction & Plugin Isolation — shipped 2026-06-07
- **v1.2** (Phases 9-13): Cleaner Core — shipped 2026-06-08
- **v1.3** (Phases 14-19): Chase Bliss Pedal Support — shipped 2026-06-10 — CBA catalog expansion (Mood MkII, Wombtone MkII, Brothers AM), preset parameter validation, reset-to-defaults flow, catalog auto-population from device model name

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
