# Phase 3: Core Domain Refactor - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the domain model so that `Rig` IS the device graph, `Controller` becomes a first-class device type (with `scenes` as a property), and a `DevicePlugin` protocol + `PluginRegistry` are introduced as the structural foundation for Phase 4 (plugin migration) and Phase 5 (plan command).

Deliverables:
- `Rig` gains `apply_order()` — DFS traversal from Controller root, children in signal chain order
- `Controller` becomes a special Device type with `scenes` property; scenes move off `Rig`
- `DevicePlugin` Protocol defined: `plan(device, ctx)`, `diff(device, ctx)`, `apply(device, ctx)`
- `PluginContext` base dataclass: `state: RigState`, `rig: Rig`, `dry_run: bool`
- `PluginRegistry` exists and is wirable; existing appliers NOT yet migrated (Phase 4)
- YAML config-repo layout changes to accommodate Controller-as-device
- All existing tests pass against the new structure

</domain>

<decisions>
## Implementation Decisions

### Rig as DeviceGraph (D-01 through D-03)
- **D-01:** `Rig` IS the DeviceGraph — no separate `DeviceGraph` type. `Rig` gains graph methods directly. The existing public API shape is preserved where possible; callers see `Rig` before and after.
- **D-02:** Phase 3 adds only `apply_order()` to `Rig`. No `edges`, `nodes`, or `device_at()` methods in this phase — those are added when a consuming phase proves they're needed.
- **D-03:** `apply_order()` is a DFS from the Controller root. Children of Controller are visited in signal chain order at each level. This is not a simple list sort — it's a proper tree traversal that respects the Controller → child-device hierarchy.

### Controller as a Special Device Type (D-04 through D-07)
- **D-04:** Controller is a special subtype of Device (not a peer class). `DeviceType` enum gains `CONTROLLER`. Controller's config type joins the `DeviceConfig` discriminated union.
- **D-05:** `scenes` move from `Rig` to Controller's model. `Rig` no longer owns scenes directly — it owns the device graph, and scenes are on the Controller device node.
- **D-06:** YAML config-repo layout changes are required and expected. The user is NOT concerned about breaking the companion rig config repo. The current `controller.yaml` / `mc6.yaml` layout will be restructured so Controller is defined as a device (alongside `devices/mc6.yaml` or similar).
- **D-07:** Signal chain edges only in Phase 3. The Controller→device trigger relationship (PC messages to change presets) is implicit — Controller applies last, sends PC to each child. A formal trigger-registration protocol is deferred to a later phase.

### DevicePlugin Protocol (D-08 through D-10)
- **D-08:** `DevicePlugin` Protocol defines three methods: `plan(device, ctx)`, `diff(device, ctx)`, `apply(device, ctx)`. All three receive the same base `PluginContext`.
- **D-09:** `PluginContext` base dataclass has exactly three fields: `state: RigState`, `rig: Rig`, `dry_run: bool`. Plugins that need more (e.g. MC6 needing MIDI context) define their own context subclass / decorator that wraps `PluginContext`.
- **D-10:** `PluginRegistry` maps device config type strings → `DevicePlugin` implementations. It exists and is wirable in Phase 3 but existing appliers are NOT registered in it — migration happens in Phase 4.

### Graph Edge Semantics (D-11)
- **D-11:** Graph edges represent the signal chain only (audio/data flow path: guitar → device → amp, controller → child devices). No separate ownership or dependency edge types in Phase 3.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §Phase 3 and §Phase 4 — Phase 3 success criteria and what Phase 4 expects to consume; planner must not build Phase 4 work into Phase 3
- `.planning/REQUIREMENTS.md` — No Phase 3 requirements are formally written here yet (TBD); planner should derive tasks from this CONTEXT.md and the ROADMAP success criteria

### Prior phase artifacts (structural patterns to preserve)
- `.planning/phases/02-engine-i-o-decoupling/02-CONTEXT.md` — Protocol-first decisions (D-01 through D-07 from Phase 2); `DevicePlugin` follows the same Protocol pattern as `ConfirmationIO`, `StateWriter`, `MidiConnectionIO`
- `src/rig/engine/ports.py` — Production Protocol + adapter pattern established here; `DevicePlugin` and `PluginRegistry` should follow the same style
- `src/rig/engine/appliers/base.py` — `DeviceApplier` Protocol and `ApplyContext` dataclass; `PluginContext` is a lighter version of `ApplyContext` (state + rig + dry_run only)

### Files being modified / created
- `src/rig/models/rig.py` — Gains `apply_order()` method; loses `scenes` field (moves to Controller)
- `src/rig/models/device.py` — `DeviceType` gains `CONTROLLER`; Controller config joins `DeviceConfig` union
- `src/rig/models/controller.py` — Current `Controller` model restructured or replaced to be a Device subtype with `scenes`
- `src/rig/models/scene.py` — `Scene` model itself unchanged; only where it's owned changes
- `src/rig/config/loader.py` — Updated to load Controller-as-device from new YAML layout; produces updated `Rig` with graph structure
- `src/rig/engine/plugin.py` — **new file**: `DevicePlugin` Protocol + `PluginContext` dataclass
- `src/rig/engine/plugin_registry.py` — **new file**: `PluginRegistry` (empty registry, wirable, no appliers registered yet)
- `tests/fixtures/sample_rig/` — YAML fixtures updated to new Controller-as-device layout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeviceApplier` Protocol in `src/rig/engine/appliers/base.py` — exact pattern for `DevicePlugin` Protocol; copy the structural subtyping approach
- `ApplyContext` dataclass in `src/rig/engine/appliers/base.py` — `PluginContext` is a subset of this; `state: RigState`, `dry_run: bool` already exist here
- `_SCENE_APPLIERS: dict[str, DeviceApplier]` in `src/rig/engine/appliers/registry.py` — the dict-dispatch pattern `PluginRegistry` formalizes; registry.py becomes the implementation target in Phase 4
- `ManualConfig | MidiConfig | ChaseBlissConfig` discriminated union in `src/rig/models/device.py` — Controller config will join this union with a `type: Literal["controller"]` discriminator
- `DeviceType` StrEnum in `src/rig/models/device.py` — gains `CONTROLLER = "controller"` value

### Established Patterns
- `Protocol` classes for structural subtyping — no ABC inheritance; `DevicePlugin` follows the same pattern as `DeviceApplier` and the Phase 2 IO Protocols
- `@dataclass` for context objects (not Pydantic) — `PluginContext` is a dataclass like `ApplyContext`
- `Literal` type discriminators on configs — `type: Literal["controller"] = "controller"` on the new controller config
- No module-level singletons beyond shared applier instances — `PluginRegistry` should follow the same pattern as `registry.py`

### Integration Points
- `src/rig/config/loader.py::load_rig()` — must be updated to load Controller from new YAML layout and build the updated `Rig` (with Controller as a device node, scenes on Controller)
- `src/rig/cli.py` — currently reads `rig.scenes` in several commands; will need updates when scenes move to Controller; scope these changes to Phase 4 if possible, or do minimal wiring here
- `tests/test_models.py`, `tests/test_loader.py` — primary test files that will need updates for the new Controller-as-device shape and `Rig.apply_order()`
- `tests/fixtures/sample_rig/` — YAML fixtures are the source of truth for the new layout; update these first, then update loader, then fix tests

</code_context>

<specifics>
## Specific Ideas

- The user described `apply_order()` as "DFS style apply where every child node of a controller gets applied in the signal chain order of the controller's devices." This is the key behavioral requirement for `Rig.apply_order()`.
- Controller → child devices data flow: Controller sends PC messages to change presets on child devices. This is why Controller is the root — it orchestrates the others. Eventually devices will "register" how they want to be triggered (a future plugin capability), but for Phase 3 the relationship is just structural (signal chain edges).
- Plugins can define their own context subclasses that wrap `PluginContext`. The MC6 plugin (Phase 4) will define a `MC6PluginContext` that adds MIDI fields. The base protocol always receives `PluginContext`; plugins cast to their extension type internally.

</specifics>

<deferred>
## Deferred Ideas

- **Device trigger registration protocol** — Devices eventually "register" how they want to be triggered by the Controller (PC, CC, SysEx, etc.). Deferred post-Phase 3.
- **Ownership/dependency edges** — A second edge type (Controller→scene→device ownership) was considered but deferred. Signal chain edges are sufficient for Phase 3.
- **Rig.edges / Rig.device_at()** — Graph traversal helpers beyond `apply_order()` are deferred until a consuming phase proves they're needed.
- **scenes on Rig CLI wiring** — When `cli.py` reads `rig.scenes`, those reads need to be updated to go through Controller. Full CLI migration is Phase 4 scope; Phase 3 should do the minimum needed to keep existing commands working.

</deferred>

---

*Phase: 3-core-domain-refactor*
*Context gathered: 2026-06-04*
