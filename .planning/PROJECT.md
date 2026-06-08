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

### Active

- [ ] **PKG-07**: Plugin authoring docs — how to write a new plugin package

### Out of Scope

| Feature | Reason |
|---------|--------|
| Full HX SysEx read/write via MIDI (#3) | Requires MIDI SysEx parsing complexity — future milestone |
| HX MIDI channel configurability (#4) | Current hardcoded channel works — defer |
| Complex MC6 workflows (next page, MIDI clock, etc.) (#6) | Low-priority — defer |
| Module-level READMEs (#9) | Nice to have, not blocking |
| CBA Mood MkII / Wombtone / Brothers MIDI catalog (#16) | Separate device-support work |
| MC6 clear message emulation (#17) | Deferred bug fix |
| Default preset values (#19) | Low-priority tech task |
| UI (#18) | Speculative — not planned |
| CI independent package publishing | Low-priority infra — local `uv` workflow sufficient for now |

## Context

- **v1.1 shipped 2026-06-07**: 3 phases (6–8), 8 plans, ~20,658 LOC Python across all packages
- **v1.0 shipped 2026-06-07**: 5 phases, 17 plans, 3,625 LOC Python
- Config repo layout: `rig.yaml`, `signal-chain.yaml`, `pedals/<id>.yaml`, `pedals/<id>/presets/<preset>.yaml`, `scenes/<name>.yaml`, `mc6.yaml`, `hlx/<name>.hlx`
- State persisted at `.rig/state.json` in the config repo — tracks what has been applied to physical devices
- Plugin discovery: `importlib.metadata.entry_points('rig.devices')` — install a package, it appears; uninstall, it disappears
- `rig plan` is the read-only preview step; `rig apply` is the commit step — clean separation enforced by no-MIDI-in-plan constraint
- Known tech debt: `Device.plan()` / `Device.diff()` stubs raise NotImplementedError — dead code from Phase 4 forward stubs; plan is computed via `compute_plan`, not device methods

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
| Entry points as sole discovery path (no code-level fallback) | Eliminates import-time coupling; enables third-party plugins without core changes | ✓ Good — v1.1 |
| Device-level MIDI lifecycle (`Device.setup()` owns connection) | Cleaner separation; engine doesn't need to know which devices need MIDI setup | ✓ Good — v1.1 |
| `MidiConnectionIO` Protocol removed entirely | Once devices own MIDI setup, the Protocol has no remaining purpose — remove rather than leave empty | ✓ Good — v1.1 |

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
*Last updated: 2026-06-07 after v1.1 milestone — Package Extraction & Plugin Isolation*
