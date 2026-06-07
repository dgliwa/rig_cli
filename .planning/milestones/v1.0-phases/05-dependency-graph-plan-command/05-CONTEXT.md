# Phase 5: Dependency Graph & Plan Command - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Formalize apply ordering via a `DeviceGraph` type with topological sort and cycle detection; surface unused and missing preset references from `rig plan`; ship a complete, trustworthy `rig plan` command with correct exit codes, cold-start warning, visual markers, summary line, and two-section output (setup actions then scenes); make apply execute from a pre-computed Plan rather than regenerating actions.

Deliverables:
- `DeviceGraph` in `src/rig/models/graph.py` — standalone type wrapping Rig; `apply_order()` returns devices topologically sorted; raises `ConfigError` on cycles
- `rig plan` output: Setup Actions section (CBA setup in device order) + Scenes section (scene-by-scene with devices in apply_order within each scene)
- Visual markers: `~` configure, `✓` verify, `⚠` analog, `·` no change, `~` for CBA setup actions
- Summary line: `Plan: N to configure, M manual, K already set` (CBA setup counted as "to configure")
- Exit codes: non-zero when changes detected OR missing preset refs found; 0 when clean
- Cold-start warning when `.rig/state.json` absent
- Unused/missing preset detection with warnings section at bottom of output
- `apply_plan()` accepts a pre-computed `Plan`; falls back to `compute_plan()` internally if none passed
- All existing requirements PLAN-01 through PLAN-10 satisfied

</domain>

<decisions>
## Implementation Decisions

### DeviceGraph Type (D-01 through D-03)
- **D-01:** `DeviceGraph` is a new standalone class in `src/rig/models/graph.py`. It is NOT embedded in `Rig` — it wraps a `Rig` instance and is constructed from it when ordering is needed. `Rig.apply_order()` can delegate to it or be superseded by it.
- **D-02:** Edges are derived from `signal_chain` position order only. No new `depends_on` YAML field. Controller device (`DeviceType.CONTROLLER`) always appears last — no explicit edge needed. This mirrors the current `Rig.apply_order()` logic, formalized with cycle detection.
- **D-03:** Cycle detection raises `rig.config.errors.ConfigError` with a message naming the cycle participants. Consistent with how loader raises `ConfigError` for bad cross-references.

### Unused/Missing Preset Detection (D-04 through D-06)
- **D-04:** "Missing" = a scene references a `(device_id, preset_id)` pair where EITHER the device doesn't exist in `rig.devices` OR the device exists but has no preset with that `id`. Both cases are flagged.
- **D-05:** "Unused" = a `DigitalPreset` or `HXStompPreset` defined on a device whose `id` is never referenced in any scene's `presets` dict. `AnalogPreset`s are excluded — they document knob positions, not activated by scene refs.
- **D-06:** Warnings appear in a "Warnings" section at the bottom of `rig plan` text output. Missing preset refs cause a non-zero exit code. Unused presets are informational only (exit code 0 when clean otherwise).

### Plan Output Structure (D-07 through D-09)
- **D-07:** Two-section output: (1) "Setup Actions" section showing CBA setup steps in device apply_order; (2) "Scenes" section showing each scene with its devices listed in apply_order within the scene. Setup section only appears when CBA setup actions exist.
- **D-08:** CBA setup action types (`establish_channel`, `build_preset`, `register_scenes`) all use the `~` configure marker. Visual weight is the same as a configure action — user sees the action label to distinguish type.
- **D-09:** Summary line counts CBA setup actions as "to configure": `Plan: N to configure, M manual, K already set`. When nothing to do: `No changes. Rig is up to date.`

### Apply.py Scope (D-10 through D-11)
- **D-10:** `apply_plan()` consumes a pre-computed `Plan`. `detect_cba_setup` is removed from the apply path — the plan is authoritative. The `# TODO: This shouldn't be here` in `compute.py` is resolved by moving CBA setup detection fully into `compute_plan()`.
- **D-11:** When `apply_plan()` is called without a pre-computed `Plan` (i.e., direct `rig apply` with no explicit plan step), it calls `compute_plan()` internally as a fallback. `rig apply` remains a single-command workflow for the user.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements (PLAN-01 through PLAN-10)
- `.planning/REQUIREMENTS.md` §PLAN-01 through §PLAN-10 — All ten plan command requirements are defined here; this phase satisfies all of them. Read before planning.

### Phase 4 scaffold (this phase builds on it)
- `.planning/phases/04-plugin-migration/04-CONTEXT.md` — Decisions D-01 through D-07: Device Protocol, PluginRegistry, loader dispatch, apply.py routing; Phase 5 extends these
- `src/rig/engine/devices.py` — `AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device` Plugin implementations; `plan()` and `diff()` currently raise `NotImplementedError` — Phase 5 fills them in
- `src/rig/engine/plugin_registry.py` — `PluginRegistry` with registered device plugins; Phase 5 uses this for apply ordering
- `src/rig/engine/plugin.py` — `DevicePlugin` Protocol + `PluginContext`; Phase 5 implements `plan()` and `diff()`

### Existing plan engine (being extended)
- `src/rig/engine/plan/compute.py` — `compute_plan()` with `detect_cba_setup` TODO; Phase 5 cleans this up and adds unused/missing detection
- `src/rig/engine/plan/models.py` — `Plan`, `ScenePlan`, `DeviceAction`, `CbaSetupAction` Pydantic models; `DeviceAction` needs `before`/`after` fields (PLAN-02)
- `src/rig/engine/plan/__init__.py` — public API for the plan package

### Existing ordering and domain model
- `src/rig/models/rig.py` — `Rig.apply_order()` to be superseded or delegated to `DeviceGraph`; existing signal-chain + controller-last logic is the reference
- `src/rig/models/device.py` — `Device`, `DeviceType`, config discriminated union; `DeviceType.CONTROLLER` is how MC6 is typed
- `src/rig/config/errors.py` — `ConfigError` is the correct exception type to raise for cycle detection

### CLI command
- `src/rig/cli/commands/plan.py` — existing plan command; needs exit codes, cold-start warning, marker updates, `--show-unchanged` flag, summary line
- `src/rig/cli/_shared.py` — shared Typer options and console

### Tests
- `tests/test_plan.py` — existing plan tests; Phase 5 extends these
- `tests/fakes.py` — `InMemoryStateAdapter`, `InMemoryPromptAdapter` available for testing without hardware

### Roadmap
- `.planning/ROADMAP.md` §Phase 5 — Success criteria: 4 items (DeviceGraph.apply_order, unused/missing detection, exit codes + format, visual markers)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Rig.apply_order()` in `src/rig/models/rig.py` — signal-chain + controller-last logic; `DeviceGraph` formalizes this with topological sort and cycle detection
- `compute_plan()` in `src/rig/engine/plan/compute.py` — scene iteration and `DeviceAction` construction; Phase 5 extends it with unused/missing detection and proper two-section output
- `detect_cba_setup()` in `src/rig/engine/plan/compute.py` — CBA setup action generation; stays in compute, removed from apply path
- `Plan`, `ScenePlan`, `DeviceAction`, `CbaSetupAction` in `src/rig/engine/plan/models.py` — `DeviceAction` needs `before`/`after` fields added (PLAN-02)
- `ConfigError` in `src/rig/config/errors.py` — raise this for cycle detection
- `InMemoryStateAdapter` and `InMemoryPromptAdapter` in `tests/fakes.py` — use for plan + apply tests without hardware

### Established Patterns
- Protocol-first structural subtyping — `DeviceGraph` is a plain class wrapping a `Rig`, not a Protocol subtype; no ABC
- `@dataclass` for context objects — if DeviceGraph needs any context object, use dataclass
- `ConfigError` for structural problems found during config resolution or graph traversal
- `logging.getLogger(__name__)` for debug/error logging; `rich.console.Console` for user-facing output
- `Literal` type discriminators on Pydantic models — `ScenePlan.status: Literal["new", "changed", "unchanged"]`

### Integration Points
- `src/rig/cli/commands/plan.py` — primary user-facing change; exit codes, cold-start warning, two-section output format
- `src/rig/engine/apply.py` — updated to accept optional `Plan`; falls back to `compute_plan()` if none passed; removes internal `detect_cba_setup` call
- `src/rig/models/rig.py` — `apply_order()` either delegates to `DeviceGraph` or is superseded; no breaking change to the method signature
- `src/rig/engine/plan/compute.py` — add unused/missing detection; remove the CBA-setup-in-apply TODO
- `tests/test_plan.py` — extend with unused/missing detection tests, exit code assertions, two-section output tests

</code_context>

<specifics>
## Specific Ideas

- Two-section output was explicitly chosen: Setup Actions first (CBA setup in device order), then Scenes. This mirrors how apply actually works — setup happens before scene activation.
- The `~` marker is used for all CBA setup actions regardless of type. The action label (e.g., `establish_channel`, `build_preset`) provides the distinction without adding visual noise.
- CBA setup actions count as "to configure" in the summary line — they require action, so they have the same visual weight as configure actions.
- `apply_plan()` self-computes if no Plan given — this preserves `rig apply` as a single ergonomic command without forcing an explicit plan step.

</specifics>

<deferred>
## Deferred Ideas

- **Full plan→apply pipeline UX** (plan shows, asks for confirmation, then executes) — was raised as an option but deferred. `rig apply` stays a single command that computes and executes without explicit plan confirmation.
- **Device trigger registration protocol** — from Phase 3 deferred list; still deferred post-Phase 5
- **Plugin context subclassing per device type** (MC6PluginContext, MidiPluginContext) — Phase 4 deferred; Phase 5 only needs what's required for `plan()` and `diff()` implementation

</deferred>

---

*Phase: 5-dependency-graph-plan-command*
*Context gathered: 2026-06-06*
