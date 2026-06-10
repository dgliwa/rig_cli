# rig-cli

## What This Is

Infrastructure-as-Code CLI for a guitar rig. Reads a YAML config repo describing pedals, presets, and scenes, then validates, plans, diffs, and applies those configurations to physical MIDI devices. Designed for one user (the rig owner) who wants repeatable, git-tracked rig state.

## Core Value

A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## Requirements

### Validated

- ✓ YAML config loading and cross-reference validation (`validate` command) — existing
- ✓ Domain models: Pedal, Preset (Analog/Digital/HXStomp), Scene, Rig, SignalChain — existing
- ✓ HX Stomp preset management (PC messages + `.hlx` file references) — existing
- ✓ MC6 bank/switch JSON generation (`generate mc6` command) — existing
- ✓ Apply engine: sends MIDI PC/CC, prompts for analog-only presets, updates state — existing
- ✓ MIDI adapter (Mido + rtmidi, port sharing, PC/CC/SysEx send) — existing
- ✓ CLI commands: `validate`, `apply`, `status`, `diff`, `generate mc6` — existing
- ✓ CBA (Chase Bliss Audio) multi-phase apply flow (channel → preset → scene) — existing
- ✓ **`mark_preset_saved` helper extracted** — all `presets_saved` dict mutations now flow through `update_device_state` via this named helper; no raw dict assignments remain (#11) — v1.0
- ✓ **`detect_cba_setup` promoted to public API** — renamed from `_detect_cba_setup`, `_is_cba` inlined and removed; no cross-module private symbol imports in engine package (#12) — v1.0
- ✓ **Decouple apply engine from I/O** — `ConfirmationIO`, `StateWriter`, `MidiConnectionIO` Protocols in `ports.py`; all appliers route through `ApplyContext.confirmation_io`; zero `builtins.input` patches in tests — v1.0
- ✓ **Controller as first-class Device** — `DeviceType.CONTROLLER` + `ControllerConfig` in discriminated union; `Rig.apply_order()` DFS; loader drops legacy controller path; `DevicePlugin` Protocol + `PluginRegistry` scaffold — v1.0
- ✓ **Plugin architecture** — all appliers (Analog, MIDI, ChaseBliss, MC6) migrated to `Device` Protocol + `PluginRegistry`; engine routes exclusively through registry; adding a new device type requires only plugin registration — v1.0
- ✓ **`rig plan` command** — graph-ordered diff against `state.json`, typed action list (configure / verify / analog / no_change), text + JSON output, exit codes, cold-start warning, `--scene` filter, `--show-unchanged` flag — v1.0
- ✓ **CBA single-apply convergence** — `detect_cba_setup` is forward-looking; a single `rig apply` converges a fresh CBA device through all 3 phases without re-detection — v1.0
- ✓ **Plugin package extraction** — `rig.devices` entry point group; `rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar` as independent pip packages; `rig` core has zero hard plugin dependencies — v1.1
- ✓ **Device-level MIDI lifecycle** — `Device.setup()` is sole MIDI connection mechanism; Phase -1 engine loop removed; engine has no plugin-specific MIDI logic — v1.1
- ✓ **Dead code elimination** — 7 core files deleted (mc6.py, chase_bliss.py, appliers/chase_bliss.py, catalog, controller model, interaction modules); plugins own their full implementations — v1.1

- ✓ **Single-file `rig.yaml` schema** — device list order defines signal chain; `SignalChainPosition` removed; presets inline; plugin dispatch by `config.type` entry point key — v1.2
- ✓ **Core model fully decoupled from plugins** — `Device.config: Any`; `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig`, `Control`, `ControlType` evicted from core — v1.2
- ✓ **Loader rewritten for single-file layout** — `load_rig()` parses one `rig.yaml`; multi-file paths removed; scenes extracted from controller device config — v1.2
- ✓ **Dead code sweep** — `rig generate mc6` command removed; `composes` validation removed; all `TODO: 1.2` markers cleared; multi-file compat paths deleted — v1.2
- ✓ **`Rig.scenes` as computed property** — scenes aggregated from controller devices, not stored as a flat field; `compute.py` `is_hx` branch removed; all preset lookups unified through `_get_preset_number` — v1.2
- ✓ **CBA-04: Control model default field** — `Control.default: float | None = None` added; footswitches/utilities get `None`, knobs get numeric defaults — v1.3
- ✓ **CBA-01: Wombtone MkII catalog** — 12 controls (CC14-21) with ranges and defaults — v1.3
- ✓ **CBA-02: Brothers AM catalog** — 28 controls (8 knobs, 3 toggles, 15 dipswitches, 2 footswitches) with ranges and defaults — v1.3
- ✓ **CBA-03: Mood MkII catalog backfill** — 47 controls; CC24-29, CC31-33, CC52 added; CC102=wet_bypass, CC103=loop_bypass — v1.3
- ✓ **CBA-05: Preset parameter validation** — unknown names and out-of-range values raise `ValidationError` before pedal interaction — v1.3
- ✓ **CBA-06: Reset-to-defaults** — per-preset CC reset of all resettable controls before preset CC sends — v1.3

### Active

- [ ] **PKG-07**: Plugin authoring docs — how to write a new plugin package

### Out of Scope

| Feature | Reason |
|---------|--------|
| Full HX SysEx read/write via MIDI (#3) | Requires MIDI SysEx parsing complexity — future milestone |
| HX MIDI channel configurability (#4) | Current hardcoded channel works — defer |
| Complex MC6 workflows (next page, MIDI clock, etc.) (#6) | Low-priority — defer |
| Module-level READMEs (#9) | Nice to have, not blocking |
| MC6 clear message emulation (#17) | Deferred bug fix |
| Default preset values (#19) | Low-priority tech task |
| UI (#18) | Speculative — not planned |
| CI independent package publishing | Low-priority infra — local `uv` workflow sufficient for now |

## Current State

Phases 1–19 shipped across v1.0–v1.3 (4 milestones). v1.3 Chase Bliss Pedal Support milestone complete.

**Milestone v1.3 shipped 2026-06-10:** 6 phases (14-19), 6 plans, 1,023 LOC in `rig_chasebliss/` package. Full CBA catalog support (Mood MkII, Wombtone MkII, Brothers AM), preset parameter validation, reset-to-defaults flow, and catalog auto-population from device model name. All 6 CBA requirements satisfied.

## Context

- **v1.3 shipped 2026-06-10**: 6 phases (14–19), 6 plans, 1,023 LOC in `rig_chasebliss/` package
- **v1.2 shipped 2026-06-08**: 5 phases (9–13), 8 plans, 7,349 LOC Python across all packages
- **v1.1 shipped 2026-06-07**: 3 phases (6–8), 8 plans
- **v1.0 shipped 2026-06-07**: 5 phases, 17 plans
- Config repo layout (current): single `rig.yaml` with inline devices, presets, and scenes
- State persisted at `.rig/state.json` in the config repo — tracks what has been applied to physical devices
- Plugin discovery: `importlib.metadata.entry_points('rig.devices')` — install a package, it appears; uninstall, it disappears
- `rig plan` is the read-only preview step; `rig apply` is the commit step — clean separation enforced by no-MIDI-in-plan constraint
- Known tech debt: `Device.plan()` / `Device.diff()` stubs raise NotImplementedError — dead code from Phase 4 forward stubs; plan is computed via `compute_plan`, not device methods
- CBA catalog auto-population: device YAML with `config.model: <Model Name>` (e.g., "Wombtone MkII", "Brothers AM", "Mood MkII") auto-populates controls from the catalog; explicit YAML controls take precedence

## Constraints

- **Tech stack**: Python 3.13, uv, Typer, Pydantic, Mido + rtmidi — no changes to core dependencies
- **MIDI**: No MIDI interaction in the `plan` command — plan is read-only against state.json
- **Protocol-first**: New abstractions use `Protocol` classes, not ABC inheritance
- **Side project velocity**: Ship working features; avoid over-engineering for hypothetical future frontends

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HXStompPreset has no block-level detail | Block parsing is a future concern; PC message + .hlx reference is sufficient for scenes | ✓ Good |
| Decouple engine before adding plan command | Clean seam makes plan testable and apply testable independently | ✓ Good — Phase 5 plan tests run without hardware |
| Plan command is read-only (no MIDI) | Separation of concerns; apply is the explicit commit step | ✓ Good |
| Three narrow Protocols over one fat interface | `ConfirmationIO`, `StateWriter`, `MidiConnectionIO` are each independently swappable | ✓ Good |
| `DeviceGraph` for topology ordering in `rig plan` | MC6 must be configured after all scenes it references | ✓ Good |
| `detect_cba_setup` forward-looking (all 3 phases in one call) | Single `rig apply` converges fresh CBA device; no re-detection loop | ✓ Good |
| `Device.plan()` / `Device.diff()` as forward stubs (NotImplementedError) | Phase 4 laid the Protocol; Phase 5 wires plan through `compute_plan`, not device methods | ⚠️ Revisit — stubs are dead code in current architecture |
| `Rig.scenes` as property not field | Scenes live in controller config; flat field was a historical compat shim — property aggregates from controllers, cleaner domain model | ✓ Good — v1.3 |
| Single `_get_preset_number` for all preset types | HX-specific branch in `compute.py` was dead code — `HXStompPreset.preset_number` works the same way as `DigitalPreset`; unified lookup reduces branching | ✓ Good — v1.3 |
| Entry points as sole discovery path (no code-level fallback) | Eliminates import-time coupling; enables third-party plugins without core changes | ✓ Good — v1.1 |
| Device-level MIDI lifecycle (`Device.setup()` owns connection) | Cleaner separation; engine doesn't need to know which devices need MIDI setup | ✓ Good — v1.1 |
| `MidiConnectionIO` Protocol removed entirely | Once devices own MIDI setup, the Protocol has no remaining purpose — remove rather than leave empty | ✓ Good — v1.1 |
| CBA-04 + CBA-01 + CBA-02 + CBA-03 grouped in Phase 14 | Single phase avoids partial state — `Control.default` field is prerequisite for complete catalogs | ✓ Good — v1.3 |
| Validation (Phase 15) before reset (Phase 16) | Both consume catalog controls; validation precedes any action that touches the device | ✓ Good — v1.3 |
| Imperative validation in apply(), not Pydantic model_validator | Catalog lookup at construction time would couple model layer to plugin | ✓ Good — v1.3 |
| Auto-populate only when controls list is empty | Explicit YAML controls always take precedence over catalog lookup | ✓ Good — v1.3 |
| Manufacturer hardcoded as "Chase Bliss Audio" in from_raw_yaml() | This is the CBA plugin — model is the only variable discriminator needed | ✓ Good — v1.3 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-10 — v1.3 Chase Bliss Pedal Support milestone shipped*
