# Phase 34: First-Class Scenes - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Promote scene definitions from inside the MC6 controller's `config.scenes` block to a top-level `scenes:` key in `rig.yaml`. `Rig.scenes` becomes a real Pydantic field (not a computed property). A rig without a controller device can have scenes; applying a scene without a controller sends device presets and skips MC6 programming.

</domain>

<decisions>
## Implementation Decisions

### Migration strategy
- **D-01:** Hard cutover — no dual-read fallback. `MC6Config.scenes` is removed entirely (field dropped). Existing `rig.yaml` files with scenes under `config.scenes` must be migrated; the loader will not read them from there.
- **D-02:** All test fixtures must be updated to the new top-level `scenes:` schema as part of this phase.

### Top-level scene location
- **D-03:** Scenes live inline in `rig.yaml` under a top-level `scenes:` block — same structure as today but promoted out of the controller device. No separate `scenes/` directory support in this phase.

### MC6Config fate
- **D-04:** `MC6Config.scenes` field is removed entirely. MC6Config contains `banks` only. Banks reference scene names (strings); scene definitions live at the top level of `rig.yaml`. No silent-ignore, no deprecation warning — the field simply doesn't exist.

### Controller-less apply
- **D-05:** `rig apply --scene <name>` works without a controller device. The engine iterates the scene's `presets` map and applies each device's preset (MIDI PC for digital/modeler, analog prompt for analog). MC6 bank/switch programming is skipped if no controller device is present. No error, no warning — controller is optional.

### Claude's Discretion
- Exact YAML key name for top-level scenes (`scenes:` seems natural; confirm in implementation).
- Whether `Rig.scenes` stays `dict[str, Scene]` or needs ordering guarantees.
- How `Rig.controller` property and `Rig.scenes` property are updated (property → real field migration approach).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Domain models
- `packages/rig/src/rig/models/scene.py` — `Scene` model (name, description, tempo, presets, tags)
- `packages/rig/src/rig/models/rig.py` — `Rig` model; `scenes` is currently a `@property` aggregating from controller devices — this must become a real field
- `packages/rig/src/rig/engine/plugin.py` — `Device`, `DeviceType` (CONTROLLER type)

### Controller config
- `packages/rig-morningstar/src/rig_morningstar/config.py` — `MC6Config`; `scenes` field must be removed, only `banks` remains

### Config loader
- `packages/rig/src/rig/config/loader.py` — scene loading at line 19 (reads from controller config.scenes) and validation at lines 101–114; both must be updated

### Schema example
- `packages/rig/tests/fixtures/sample_rig/rig.yaml` — primary fixture; scenes currently under `mc6.config.scenes`; must be migrated to top-level

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Scene` Pydantic model: already complete — `name`, `description`, `tempo`, `presets: dict[str, str]`, `tags`. No changes needed to the model itself.
- `Rig.scenes` `@property`: iterates controller devices to aggregate scenes. Replace with a real `scenes: dict[str, Scene] = {}` field.

### Established Patterns
- Pydantic `BaseModel` with `dict[str, Scene]` fields are already used throughout (e.g., `devices: dict[str, Device]`). The `scenes` field follows the same pattern.
- `loader.py` constructs `Rig(...)` from parsed YAML — adding `scenes` to the constructor call is straightforward once it's a real field.
- `MC6Config` uses `extra="ignore"` today — removing `scenes` from the model means old YAMLs with `scenes` under the controller silently discard it at parse time (since extra fields are ignored). The hard-cutover intent requires **removing** `extra="ignore"` OR adding explicit rejection in the loader's validation step.

### Integration Points
- `Rig.scenes` property consumers: `loader.py` (validation at lines 101–114), `cli.py` (status/plan/apply commands that iterate scenes), engine apply path
- `MC6Config` is defined in `packages/rig-morningstar` — a separate package; the field removal touches a plugin package, not core

</code_context>

<specifics>
## Specific Ideas

- The hard-cutover approach means the sample rig fixture (`tests/fixtures/sample_rig/rig.yaml`) will need its `mc6.config.scenes` block moved to a top-level `scenes:` block — this should be a concrete task in the plan.
- The `MC6Config.extra="ignore"` question is a subtle trap: if left in place, old YAMLs won't error even without `scenes` on the model. The planner should decide whether to keep `extra="ignore"` (silent discard) or remove it (strict parse errors for unknown fields) — the user's intent is hard cutover so strict may be preferable.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 34-First-Class Scenes*
*Context gathered: 2026-07-01*
