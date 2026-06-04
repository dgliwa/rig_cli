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

### Active

- [ ] **Decouple apply engine from I/O** — separate prompt, state-write, and MIDI calls from engine logic so engine can be tested without hardware and reused by alternative frontends (#1)
- [ ] **Fix inconsistent ctx.state mutation in ChaseBlissApplier** — replace direct dict assignment with `update_device_state` helper for consistent auditable state writes (#11)
- [ ] **Promote `_detect_cba_setup` to public API** — rename to `detect_cba_setup` or move to shared module; remove cross-module private symbol dependency (#12)
- [ ] **Rig planning engine (`plan` command)** — diff desired scene/preset config against persisted device state and emit a typed, structured action list (configure / verify / analog / no_change) in text and JSON formats (#13)

### Out of Scope

- Full HX SysEx read/write via MIDI (#3) — future milestone; requires MIDI SysEx parsing complexity
- HX MIDI channel configurability (#4) — deferred; current hardcoded channel works
- Complex MC6 workflows (next page, MIDI clock, etc.) (#6) — future; low-priority
- Module-level READMEs (#9) — nice to have; not blocking any feature
- Sub-packages per device type (#10) — future refactor; not urgent
- Isolated preset management mode (#14) — future feature
- CBA Mood MkII / Wombtone / Brothers MIDI catalog (#16) — separate device-support work
- MC6 clear message emulation (#17) — deferred bug fix
- Default preset values (#19) — tech-task; low priority
- UI (#18) — speculative; not planned

## Context

- Config repo layout: `rig.yaml`, `signal-chain.yaml`, `pedals/<id>.yaml`, `pedals/<id>/presets/<preset>.yaml`, `scenes/<name>.yaml`, `mc6.yaml`, `hlx/<name>.hlx`
- State persisted at `.rig/state.json` in the config repo — tracks what has been applied to physical devices
- Apply engine currently calls `prompt()` (interactive confirmation), writes state, and sends MIDI inline — this coupling is the target of issue #1
- CBA applier has two known tech-debt items (#11, #12) that will be cleaned up alongside the decoupling work
- The `plan` command (#13) reads persisted state but does NOT apply — it only produces the action list

## Constraints

- **Tech stack**: Python 3.13, uv, Typer, Pydantic, Mido + rtmidi — no changes to core dependencies
- **MIDI**: No MIDI interaction in the `plan` command — plan is read-only against state.json
- **Protocol-first**: New abstractions use `Protocol` classes, not ABC inheritance
- **Side project velocity**: Ship working features; avoid over-engineering for hypothetical future frontends

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HXStompPreset has no block-level detail | Block parsing is a future concern; PC message + .hlx reference is sufficient for scenes | — Pending |
| Decouple engine before adding plan command | Clean seam makes plan testable and apply testable independently | — Pending |
| Plan command is read-only (no MIDI) | Separation of concerns; apply is a separate step | — Pending |

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
*Last updated: 2026-06-04 after initialization*
