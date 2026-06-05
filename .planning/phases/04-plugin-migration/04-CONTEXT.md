# Phase 4: Plugin Migration - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all existing appliers (AnalogApplier, MidiApplier, ChaseBlissApplier, MC6Applier) to a first-class plugin architecture where `Device` is a Protocol, each concrete device type satisfies it, and the core engine (apply.py, CLI) routes exclusively through `PluginRegistry` — no direct applier imports remain.

Deliverables:
- `Device` becomes a Protocol with `plan()`, `diff()`, `apply()` plus `id` and metadata getters
- Concrete device types (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device`) satisfy the Device Protocol
- `PluginRegistry` maps `config_type` string → concrete model class; loader uses registry-driven dispatch to parse YAML
- `apply.py` routes through `registry.get(device.config.type).apply(...)` — no `isinstance` dispatch, no direct applier imports
- All existing apply behavior preserved end-to-end; test suite passes

</domain>

<decisions>
## Implementation Decisions

### Device Protocol Architecture (D-01 through D-04)
- **D-01:** `Device` becomes a Protocol. Concrete device types (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device`) are Pydantic models that satisfy the Protocol structurally. No ABC inheritance — same Protocol-first pattern as `DeviceApplier` and the Phase 2 IO Protocols.
- **D-02:** The Device Protocol defines: `plan(ctx)`, `diff(ctx)`, `apply(ctx)` plus `id` and metadata getters (e.g. `name`, `config`). The core architecture calls these methods on any Device instance without knowing the concrete type.
- **D-03:** `plan()` and `diff()` raise `NotImplementedError` on all concrete types in Phase 4. Phase 5 fills them in. This makes it obvious the methods are unimplemented and will blow up clearly if called accidentally.
- **D-04:** Registering a plugin declares both the config schema (Pydantic model class for YAML parsing) AND the behavior. The framework becomes aware of new device types through registration alone.

### Loader Integration (D-05)
- **D-05:** Loader uses registry-driven dispatch: `loader.py` reads the `type` field from device YAML, calls `registry.get_model(config_type)` to get the concrete Pydantic model class, then parses the YAML dict into it. The discriminated union in `device.py` is replaced by (or augmented with) registry-driven parsing.

### MC6 Scope (D-06)
- **D-06:** MC6 is migrated in Phase 4 as a first-class plugin. `MC6Device` implements the Device Protocol; its `apply()` wraps the current `apply_banks` logic. MC6 is not deferred.

### apply.py Routing (D-07)
- **D-07:** `apply.py` routes exclusively through `PluginRegistry.get(device.config.type).apply(...)`. No direct applier imports (`get_scene_applier`, `get_cba_applier`, `get_mc6_applier`) remain in `apply.py` or CLI after this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 3 scaffold (this phase builds on it)
- `.planning/phases/03-core-domain-refactor/03-CONTEXT.md` — Decisions D-08 through D-10: DevicePlugin Protocol shape, PluginContext design, PluginRegistry scaffold; Phase 4 builds directly on these
- `src/rig/engine/plugin.py` — `DevicePlugin` Protocol + `PluginContext` dataclass from Phase 3; Phase 4 either extends or replaces the Protocol with the Device-as-Protocol approach
- `src/rig/engine/plugin_registry.py` — Empty `PluginRegistry` scaffold from Phase 3; Phase 4 populates it

### Existing appliers being migrated
- `src/rig/engine/appliers/analog.py` — `AnalogApplier.apply_scene(action, ctx)` logic moves to `AnalogDevice.apply(ctx)`
- `src/rig/engine/appliers/midi_device.py` — `MidiApplier.apply_scene(action, ctx)` logic moves to `MidiDevice.apply(ctx)`
- `src/rig/engine/appliers/chase_bliss.py` — `ChaseBlissApplier.apply_scene` + `apply_setup` logic moves to `ChaseBlissDevice.apply(ctx)`
- `src/rig/engine/appliers/mc6.py` — `MC6Applier.apply_banks(banks, ctx)` logic moves to `MC6Device.apply(ctx)`
- `src/rig/engine/appliers/registry.py` — Old dispatch dict (`_SCENE_APPLIERS`) superseded by `PluginRegistry`; can be removed when migration is complete

### Domain model and engine routing
- `src/rig/models/device.py` — Current `Device` Pydantic model with discriminated config union; the Device Protocol replaces or wraps this
- `src/rig/engine/apply.py` — Primary consumer; routing changes from `get_scene_applier()` to `registry.get(device.config.type).apply(...)`
- `src/rig/engine/appliers/base.py` — `DeviceApplier` Protocol and `ApplyContext` dataclass; check whether `DeviceApplier` survives or is superseded
- `src/rig/config/loader.py` — Must be updated to use registry-driven YAML dispatch (D-05)

### Roadmap
- `.planning/ROADMAP.md` §Phase 4 — Success criteria: 3 items (appliers registered, apply.py routes through registry, behavior preserved)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeviceApplier` Protocol in `src/rig/engine/appliers/base.py` — structural Protocol pattern; Device Protocol follows the same style
- `ApplyContext` dataclass in `src/rig/engine/appliers/base.py` — carries `state`, `rig`, `dry_run`, `midi`, `connected_devices`, `confirmation_io`; `PluginContext` is a subset; concrete device types that need MIDI context define their own extension (per D-09 from Phase 3)
- `_SCENE_APPLIERS` dict in `src/rig/engine/appliers/registry.py` — the dict-dispatch pattern `PluginRegistry` formalizes; this file becomes obsolete after migration
- `DeviceType.CONTROLLER` + `ControllerConfig` discriminated union — MC6 is already typed as controller; `MC6Device` builds on this

### Established Patterns
- Protocol-first structural subtyping (no ABC inheritance) — `Device` Protocol follows the same pattern as `DeviceApplier`, `ConfirmationIO`, `StateWriter`, `MidiConnectionIO`
- `@dataclass` for context objects (not Pydantic) — `PluginContext` and any context extensions remain dataclasses
- `Literal` type discriminators on configs — concrete device types keep `type: Literal["midi"]` etc.
- No module-level singletons beyond shared instances — `PluginRegistry` should be a single shared instance similar to `registry.py`

### Integration Points
- `src/rig/engine/apply.py` — biggest change: routing swaps from `appliers/registry.py` to `plugin_registry`
- `src/rig/config/loader.py` — YAML parsing switches from discriminated union to registry-driven dispatch
- `src/rig/cli.py` — may still import device models; check if any applier imports remain after migration
- `tests/` — existing apply tests should pass unchanged; new plugin-registration tests needed

</code_context>

<specifics>
## Specific Ideas

- The user's vision: "upon registering the plugin, the framework is aware of new registered types and knows how to parse new device types — core architecture only cares about calling apply/plan/diff on Device instances." This is the key extensibility requirement: adding a new device type means registering a plugin, not touching core apply/loader logic.
- `Device` Protocol must expose `id` and metadata getters so core code never needs to downcast to a concrete type to get basic info.
- Concrete types (`MidiDevice`, `AnalogDevice`, etc.) remain Pydantic models so YAML parsing stays declarative.

</specifics>

<deferred>
## Deferred Ideas

- **Full `plan()` / `diff()` implementations** — Phase 5 fills these in; Phase 4 stubs them with `raise NotImplementedError`
- **Plugin context subclassing for MIDI** — D-09 from Phase 3 allows plugins to define `MC6PluginContext`, `MidiPluginContext` etc.; Phase 4 wires the minimum context needed for apply; richer context extensions happen when Phase 5 needs them
- **Device trigger registration protocol** — from Phase 3 deferred list; still deferred post-Phase 4

</deferred>

---

*Phase: 4-plugin-migration*
*Context gathered: 2026-06-05*
