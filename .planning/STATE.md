---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Chase Bliss Pedal Support
status: planning
last_updated: "2026-06-09T02:30:00.000Z"
last_activity: 2026-06-08 — Phase 14 complete, Phase 15 complete; Phase 16 context gathered
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 3
  completed_plans: 2
  percent: 66
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-08)

**Core value:** A single command brings the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.
**Current focus:** v1.3 Chase Bliss Pedal Support — Phase 16 (Reset-to-Defaults) — context captured, ready for planning

## Current Position

Phase: 16 — Reset-to-Defaults
Plan: None
Status: Not started
Last activity: 2026-06-08 — Phase 14 and Phase 15 complete; Phase 16 pending

```
Progress: ████████░░ 66% (2/3 phases)
```

## Performance Metrics

**Velocity:**

- Total plans completed: 26
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
| 13 | 0 | - | - |
| 14 | 1 | - | - |
| 15 | 1 | - | - |

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

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Plugin | `generate_mc6` should read scenes from MC6 config instead of `Rig.scenes` | resolved — removed in Phase 12 | Phase 10 |
| Plugin | MC6 apply could leverage `composes` data | resolved — removed in Phase 12 | Phase 10 |
