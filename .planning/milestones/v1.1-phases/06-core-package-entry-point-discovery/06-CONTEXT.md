# Phase 6: Core Package & Entry Point Discovery — Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire up the `rig` core package to discover device plugins at runtime via Setuptools Entry Points (`importlib.metadata.entry_points('rig.devices')`), with zero hard dependencies on any device plugin package. Migrate from the current code-internal `PluginRegistry` to entry-point-driven discovery. The `rig` command-line interface works with zero plugins installed; device capabilities come from whatever plugins are present in the environment.

Deliverables:
- `rig` core `pyproject.toml` declares the `rig.devices` entry point group (initially empty)
- `PluginRegistry` discovers and loads plugins via `importlib.metadata.entry_points('rig.devices')` at startup
- Entry points resolve to Device model classes directly (not `register()` callbacks)
- `rig` CLI works with zero device plugins installed (graceful degradation)
- Old hard-coded registrations in `engine/devices.py` removed — entry points are the single path
- Backward-compatible: existing test suite passes, existing rig config repos work unchanged
- All 4 plugin package entry points updated to point to Device classes instead of `register()` functions

</domain>

<decisions>
## Implementation Decisions

### Entry Point Schema (D-01)
- **D-01:** Entry points resolve directly to the Device Pydantic model class (e.g., `analog = "rig_analog.device:AnalogDevice"`). Core reads the class from the entry point, calls the class constructor with config data from YAML, and registers the instance. No `register()` callback functions — the callback pattern adds unnecessary indirection and creates a circular import pattern (rig calls plugin, plugin calls rig). This is the idiomatic Setuptools Entry Points usage: entry point → importable reference → core uses it.

### Discovery Timing (D-02)
- **D-02:** Plugin discovery happens at `PluginRegistry` instantiation time (which occurs at CLI startup). All `rig.devices` entry points are iterated and loaded before the first command runs. Failures to load a plugin produce a log warning but do not crash the CLI — `rig validate`, `rig status`, and `rig --help` work even when no plugins are installed. Errors surface later only when a configuration references a device type with no registered plugin.

### Backward Compatibility & `devices.py` Removal (D-03)
- **D-03:** The old hard-coded registrations in `engine/devices.py` (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device` as module-level registrations) are removed. Entry points are the single registration path. The workspace (`[tool.uv.sources]`) means `pip install -e packages/rig-*` makes all plugins available during local development — no fallback needed. Keeps the architecture simple: one way to register a device, not two.

### Plugin Authoring Interface (D-04)
- **D-04:** A new device plugin must provide:
  1. A Pydantic BaseModel subclass satisfying the `Device` Protocol (structural — no ABC inheritance)
  2. A `pyproject.toml` with `[project.entry-points."rig.devices"]` pointing the config type key to the Device class
  3. The Device class is instantiated by core with `id`, `name`, and `config` from the rig YAML
  No `register()` function, no explicit `PluginRegistry` import in plugin code.

### Device-Level MIDI Ownership (D-05)
- **D-05:** Device plugins that need MIDI (ChaseBliss, Morningstar) manage their own MIDI connections in their `setup()` method. The engine provides `rig.midi.adapter.MidiManager` as an importable utility, but devices call it directly — the engine does not manage MIDI port lifecycle for plugins. (Phase 6 doesn't optimize MIDI port sharing; that can be added later if port conflicts arise.)

### Core Package Entry Point Declaration (D-06)
- **D-06:** `rig` core's `pyproject.toml` declares the `rig.devices` entry point group with an empty mapping. This ensures `importlib.metadata.entry_points(group='rig.devices')` returns a valid (possibly empty) list even when no plugins are installed, rather than raising `KeyError`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase foundations (this phase builds on these)
- `.planning/phases/04-plugin-migration/04-CONTEXT.md` — Device Protocol architecture (D-01–D-04), loader dispatch (D-05), apply.py routing (D-07)
- `.planning/phases/05-dependency-graph-plan-command/05-CONTEXT.md` — Plan computation (D-10–D-11), CBA setup detection in compute_plan
- `.planning/REQUIREMENTS.md` §CORE-01 through §CORE-04 — Requirements this phase satisfies

### Existing code to modify
- `packages/rig/src/rig/engine/plugin_registry.py` — Current `PluginRegistry` with `register()`/`get()` pattern; must add entry-point-based discovery
- `packages/rig/src/rig/engine/devices.py` — Hard-coded `default_registry` with 4 devices; remove in favor of entry points
- `packages/rig/pyproject.toml` — Needs `[project.entry-points."rig.devices"]` group declaration
- `packages/rig-*/pyproject.toml` — Entry points currently point to `register` functions; update to point to Device classes directly
- `packages/rig-*/src/*/__init__.py` — Remove `register()` functions; no longer needed

### Test fixtures and state
- `packages/rig/tests/fakes.py` — `InMemoryStateAdapter`, `InMemoryPromptAdapter` for testing without hardware
- `packages/rig/tests/test_plugin.py` — Plugin discovery tests; extend for entry-point-based discovery tests
- `packages/rig/tests/test_devices.py` — Device registration tests; update after removing `devices.py` hard-coded registrations

### Roadmap
- `.planning/ROADMAP.md` §Phase 6 — Goal, requirements, success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PluginRegistry` in `packages/rig/src/rig/engine/plugin_registry.py` — Already has `register()`/`get()`/`register_model()`/`get_model()`; needs `discover()` method and startup auto-discovery
- `get_registry()` in the same file — Returns the shared default registry; callers already use this
- Each plugin's `__init__.py` has a `register()` function — These become unnecessary after D-01, but the Device classes are well-structured and reusable

### Established Patterns
- Protocol-first structural subtyping (no ABC inheritance) — Device Protocol established in Phase 4, maintained here
- `from __future__ import annotations` + `TYPE_CHECKING` guard for circular imports — Entry-point discovery breaks the circular import chain anyway (core reads class names from metadata, no import-time module loading)
- Workspace pattern (`[tool.uv.sources]`) for local development — Already in place across all packages

### Integration Points
- `PluginRegistry` constructor or `discover()` method — Must iterate `entry_points(group='rig.devices')`, load the resolved class, and register it
- `engine/devices.py` `default_registry` — Remove the 4 hard-coded registrations; CLI startup entry-point discovery replaces them
- Each plugin `__init__.py` — Remove `register()`; move entry point to point at Device class directly
- `packages/rig/src/rig/__init__.py` — Check if anything imports from `devices.py` that would break when registrations move to entry points
- `tests/test_plugin.py` — Current tests likely use the hard-coded registry; add entry-point discovery tests plus monkey-patch fixtures

</code_context>

<specifics>
## Specific Ideas

- The user's vision is clear: "the entry points way, with separate packages." Entry points → Device class directly, no callback indirection.
- MIDI at device level: "if a device's plan requires a MIDI connection to configure, that should be handled at the device setup level. Then when actually running the configuration, it should use that connection." Phase 6 establishes the pattern; Phase 7 wires it fully per device.
- The WIP already shows good package structure — this phase's job is to make entry points actually drive the discovery, and remove the old code-registered path.

</specifics>

<deferred>
## Deferred Ideas

- **MIDI port sharing/connection pooling** — If multiple device plugins need MIDI to the same port, a connection pool pattern could be added. Defer — not yet needed.
- **Plugin version compatibility checking** — Checking `requires-python` or core version constraints at discovery time. Defer — plugins declare `dependencies = ["rig"]` which pip enforces at install time.
- **Plugin discovery caching** — Caching entry point results to speed up subsequent CLI invocations. Defer — startup overhead is negligible.
- **Hot-reload of plugins** — Re-discovering plugins without restarting the CLI. Defer — not needed for CLI usage pattern.

</deferred>

---

*Phase: 6-core-package-entry-point-discovery*
*Context gathered: 2026-06-07*
