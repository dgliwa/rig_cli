# Phase 4: Plugin Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 04-plugin-migration
**Areas discussed:** Plugin adapter strategy, MC6 scope, plan/diff stubs

---

## Plugin Adapter Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| DeviceAction in PluginContext | PluginContext gains action: DeviceAction field for apply() calls | |
| Keep DeviceApplier, bridge at registry | Old appliers keep apply_scene(); thin PluginAdapter wraps each one | |
| Apply() signature takes both | Widen to apply(device, action, ctx) — breaks Protocol | |
| Device becomes a Protocol, plugins provide concrete types | Each concrete device type satisfies the Device Protocol structurally | ✓ |

**User's choice:** Device becomes a Protocol. "I want to leverage polymorphism here — upon registering the plugin, the framework is aware of new registered types and knows how to parse new device types. Core architecture only cares about calling apply, plan, etc. on Device instances."

**Notes:** User clarified that plugin registration declares both the config schema (Pydantic model class for YAML parsing) AND the behavior. Loader uses registry-driven dispatch: `registry.get_model(config_type)` returns the concrete class, loader parses YAML into it. This replaces the current Pydantic discriminated union dispatch in loader.py.

---

## MC6 Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — MC6Device is a first-class plugin in Phase 4 | MC6Device implements Device Protocol; apply() wraps apply_banks logic | ✓ |
| Defer MC6 to Phase 5 | MC6 stays special-cased in apply.py; Phase 4 only migrates Analog/MIDI/CBA | |
| You decide | Let the planner make the call based on complexity | |

**User's choice:** MC6Device is a first-class plugin in Phase 4.

**Notes:** MC6 is migrated alongside the other appliers. No exceptions.

---

## plan/diff Stubs

| Option | Description | Selected |
|--------|-------------|----------|
| Stub them out: raise NotImplementedError | plan() and diff() raise NotImplementedError — obvious that Phase 5 must fill them in | ✓ |
| Return sensible defaults | plan() returns empty list; diff() returns 'changed' | |
| Remove plan/diff from Protocol for now | Trim DevicePlugin to apply()-only; re-add when Phase 5 needs them | |

**User's choice:** Raise NotImplementedError.

**Notes:** Stubs blow up clearly if called accidentally before Phase 5 implements them.

---

## Claude's Discretion

None — user provided clear direction on all three areas.

## Deferred Ideas

- Full `plan()` / `diff()` implementations — Phase 5
- Plugin context subclasses for MIDI (MC6PluginContext, MidiPluginContext) — Phase 4 wires minimum apply context; extensions when Phase 5 needs them
- Device trigger registration protocol — still deferred from Phase 3
