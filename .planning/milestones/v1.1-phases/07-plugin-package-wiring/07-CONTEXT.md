# Phase 7: Plugin Package Wiring & Device-Level MIDI — Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Move each device plugin to own its Device class end-to-end — MIDI connection lifecycle, setup, and apply logic. The engine no longer orchestrates MIDI connections; each device plugin manages its own via the shared `MidiManager` utility in core.

Deliverables:
- All 4 entry points point to plugin-specific Device classes (not core)
- Each plugin Device class has a real `setup()` that handles MIDI port connection + device-specific initialization
- Engine `apply_plan()` removes Phase -1 (MIDI connection prompt loop) — every device owns MIDI in `setup()`
- Core `rig.engine.devices.py` deleted — all Device classes live in plugin packages
- Formal `Device` Protocol class defined in core for plugin authors
- `MidiManager` stays in core as a shared utility — plugins import and use it

</domain>

<decisions>
## Implementation Decisions

### Plugin Device Class Ownership (D-P7-01)
- **D-P7-01:** Each plugin package owns its own Device class. Entry points point to plugin-specific classes:
  - `manual = "rig_analog.device:AnalogDevice"` — exists, keep
  - `chase_bliss = "rig_chasebliss.device:ChaseBlissDevice"` — needs creation (core class + cba_setup merged into plugin)
  - `controller = "rig_morningstar.device:MC6Device"` — exists, keep
  - `midi = "rig_hx.device:HXStompDevice"` — needs creation (PC sender, same behavior as MidiDevice)
  Core has zero Device classes. Old `rig.engine.devices.py` is deleted.

### MIDI Connection Ownership (D-P7-02)
- **D-P7-02:** Every device that needs MIDI handles its own port connection in `setup()`. Each device's `setup()` prompts the user for port selection, caches the port name in state (via `update_device_state`), and adds itself to `ctx.connected_devices`. The engine's Phase -1 MIDI connection loop is removed entirely.

### Engine `setup()` → `apply()` Flow (D-P7-03)
- **D-P7-03:** Engine flow becomes:
  1. **setup()** — iterates all devices, calls `device.setup()`. Each device connects its own MIDI, does one-time initialization (e.g., CBA 3-phase). Cancellable per device.
  2. **Phase 1: Scene apply** — same as current, devices use `ctx.connected_devices` and `ctx.midi` for MIDI sends
  3. **Phase 2: MC6 programming** — same as current, MC6Device uses its own MIDI connection from setup()
  Phase -1 is deleted. No dedicated MIDI connection prompt loop in the engine.

### Device Protocol (D-P7-04)
- **D-P7-04:** An explicit `Device` Protocol class is added to `rig.engine.plugin` (or `rig.engine.appliers.base`). Every plugin Device class structurally implements it. This gives IDE autocomplete, error messages on missing methods, and a clear contract for plugin authors. No ABC inheritance — structural subtyping.

### Shared Helpers Stay in Core (D-P7-05)
- **D-P7-05:** `DeviceApplyResult`, `update_device_state`, `SetupResult`, `SetupContext`, `DeviceApplyContext` remain in `rig.engine.appliers.base` / `rig.engine.plugin`. Plugins import them as needed. `MidiManager` stays in `rig.midi.adapter`.

### rig-hx Device Class (D-P7-06)
- **D-P7-06:** `rig_hx.device.HXStompDevice` extends the same pattern — PC-message-based apply, MIDI connection in `setup()`. Named for the specific device to leave room for future HX-specific logic (preset management, SysEx, etc.). Class body is simple to start.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase foundations
- `.planning/phases/06-core-package-entry-point-discovery/06-CONTEXT.md` — Phase 6 decisions (entry point schema D-01, MIDI ownership D-05)
- `.planning/REQUIREMENTS.md` §ANLG-01, §CHASE-01, §MC6-01, §HX-01 — Requirements this phase satisfies

### Existing code to modify or remove
- `packages/rig/src/rig/engine/apply.py` — Remove Phase -1 MIDI connection loop; setup() is now the sole MIDI connection mechanism
- `packages/rig/src/rig/engine/devices.py` — Delete entirely; all Device classes move to plugin packages
- `packages/rig/src/rig/engine/plugin.py` — Add explicit `Device` Protocol class
- `packages/rig-*/pyproject.toml` — Update entry points to point to plugin-specific Device classes
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — Add `ChaseBlissDevice` class merging core class + cba_setup logic
- `packages/rig-hx/src/rig_hx/device.py` — Create `HXStompDevice` class
- `packages/rig-morningstar/src/rig_morningstar/device.py` — MC6Device already exists; verify `setup()` handles MIDI connection cleanly

### MIDI infrastructure (stays in core)
- `packages/rig/src/rig/midi/adapter.py` — `MidiManager` shared utility
- `packages/rig/src/rig/engine/plugin.py` — `DeviceApplyContext`, `SetupContext`, `SetupResult` (Protocol types)
- `packages/rig/src/rig/engine/appliers/base.py` — `DeviceApplyResult`, `update_device_state`

### Existing plugin device implementations (reference for pattern consistency)
- `packages/rig-analog/src/rig_analog/device.py` — Reference for minimal Device class
- `packages/rig-morningstar/src/rig_morningstar/device.py` — Reference for Device class with setup() + apply()

### Test fixtures
- `packages/rig/tests/fakes.py` — `InMemoryStateAdapter`, `InMemoryPromptAdapter`, `InMemoryMidiConnectionIO`
- `packages/rig/tests/test_devices.py` — Device tests; update imports after class moves
- `packages/rig-analog/tests/test_analog_device.py` — Analog device tests
- `packages/rig/tests/fixtures/sample_rig/` — Test rig config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MidiManager` in `packages/rig/src/rig/midi/adapter.py` — Port discovery, PC/CC/SysEx send; stays in core
- `DeviceApplyResult`, `update_device_state` in `packages/rig/src/rig/engine/appliers/base.py` — Shared helpers
- `SetupContext`, `SetupResult`, `DeviceApplyContext` in `packages/rig/src/rig/engine/plugin.py` — Already provide ctx for setup()/apply()
- `in_prompt_midi_connect` in `packages/rig/src/rig/interaction/midi.py` — Port selection prompt (reusable)

### Established Patterns
- Protocol-first structural subtyping — No ABC inheritance; `Device` Protocol follows existing pattern
- Lazy import for optional plugin dependencies — Already used in core `ChaseBlissDevice.setup()` (try/except ImportError)
- Each device owns its model — Pydantic `BaseModel` with `ConfigDict(extra="allow")` for YAML compatibility

### Integration Points
- `apply_plan()` in `packages/rig/src/rig/engine/apply.py` — Phase -1 removal; setup() loop preceeds scene apply
- `collect_midi_devices()` in `packages/rig/src/rig/interaction/midi.py` — May become unused after Phase -1 removal
- `get_registry()` in `packages/rig/src/rig/engine/plugin_registry.py` — Discovery works, entry points just need class path updates
- `load_rig()` in `packages/rig/src/rig/config/loader.py` — Uses `get_registry().get_model(config_type)` to parse device YAML; should continue working after entry point updates

</code_context>

<specifics>
## Specific Ideas

- "The ideal state is clean separation: core is the framework, plugins are the devices."
- "Ship the ideal state, no backward compat baggage."
- "We'll eventually hopefully be managing HX preset configuration rather than just sending PC messages" — hence `HXStompDevice` naming with room for future capability
- Analog devices have no MIDI — `AnalogDevice.setup()` returns no-op `SetupResult()`

</specifics>

<deferred>
## Deferred Ideas

- **HX Stomp preset block parsing** — Managing HX patch internals (blocks, routing, etc.). Not yet needed; belongs in a future phase when `.hlx` content management is tackled.
- **MIDI port sharing / connection pooling** — If multiple devices share a USB port, deduplication could avoid redundant connection prompts. Defer until it becomes a problem.
- **Plugin version compatibility checking** — Checking core version constraints at discovery time. Pip handles this via dependencies.
- **MC6 bank JSON generation** — Already in `rig-morningstar` as a separate generator. No change needed in this phase.

</deferred>

---

*Phase: 7-plugin-package-wiring*
*Context gathered: 2026-06-07*
