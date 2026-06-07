# rig-cli

## What This Is

Infrastructure-as-Code CLI for a guitar rig. Reads a YAML config repo describing pedals, presets, and scenes, then validates, plans, diffs, and applies those configurations to physical MIDI devices. Designed for one user (the rig owner) who wants repeatable, git-tracked rig state.

## Core Value

A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## Current Milestone: Shipped

**v1.0** I/O Decoupling & Plugin Architecture — Shipped 2026-06-07 (Phases 1-5)
**v1.1** Package Extraction & Plugin Isolation — Shipped 2026-06-07 (Phases 6-7)

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

### Validated

(All v1.0 requirements remain validated)
- ✓ **PKG-01**: `rig` core publishes `rig.devices` entry point group and discovers plugins via `importlib.metadata.entry_points()` at runtime — v1.1
- ✓ **PKG-02**: `rig-analog` is a separate pip package registering an AnalogDevice via entry point — v1.1
- ✓ **PKG-03**: `rig-chasebliss` is a separate pip package registering a ChaseBlissDevice via entry point, with MIDI connection managed at device level for setup phases — v1.1
- ✓ **PKG-04**: `rig-morningstar` is a separate pip package registering an MC6Device via entry point, with MIDI connection managed at device level for bank/switch config — v1.1
- ✓ **PKG-05**: `rig-hx` is a separate pip package registering an HXStompDevice via entry point — v1.1
- ✓ **PKG-06**: Each plugin has independent `pyproject.toml`, version pinning, and release cycle — v1.1
- ✓ **PKG-07**: Plugin authoring docs — how to write a new plugin package — v1.1
- ✓ **PKG-08**: `rig` has zero hard dependencies on any device plugin (pure runtime discovery) — v1.1

### Active

None — all requirements shipped.

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
| CI pipelines per package | Deferred from v1.1 — Phase 8 removed from roadmap |
| PyPI publishing | Deferred from v1.1 — Phase 8 removed from roadmap |
| Plugin authoring guide | Deferred from v1.1 — Phase 8 removed from roadmap |

## Context

- **v1.0 shipped 2026-06-07**: 5 phases, 17 plans, 3,625 LOC Python
- **v1.1 shipped 2026-06-07**: 2 phases, 5 plans, additional ~1,000 LOC across plugin packages
- v1.1 deferred: CI pipelines, PyPI publishing, plugin authoring guide (Phase 8 removed from roadmap)
- Config repo layout: `rig.yaml`, `signal-chain.yaml`, `pedals/<id>.yaml`, `pedals/<id>/presets/<preset>.yaml`, `scenes/<name>.yaml`, `mc6.yaml`, `hlx/<name>.hlx`
- State persisted at `.rig/state.json` in the config repo — tracks what has been applied to physical devices
- Engine I/O is fully decoupled via Protocol ports — `apply_plan` is testable without hardware
- Plugin registry (`PluginRegistry`) routes device config type → `Device` implementation; new device types require only registration
- `rig plan` is the read-only preview step; `rig apply` is the commit step — clean separation enforced by no-MIDI-in-plan constraint
- Known tech debt: several TODO markers in `apply.py` (pre-existing), `Device.plan()` / `Device.diff()` stub NotImplementedError on all 4 device types (forward stubs from Phase 4, not yet wired)

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
*Last updated: 2026-06-07 after shipping v1.1 milestone — Package Extraction & Plugin Isolation*
