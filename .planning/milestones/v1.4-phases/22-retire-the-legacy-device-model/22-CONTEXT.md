# Phase 22: Retire the Legacy Device Model - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Retire `Device(BaseModel)` from `models/device.py`; move `DeviceType` StrEnum to
`engine/plugin.py`; delete `models/device.py` entirely; type `Rig.devices` as
`dict[str, Device]` against the `Device` Protocol from `engine/plugin.py`; remove 3
`hasattr` guards in `apply.py`; migrate 8 test files to use `FakeDevice` from
`packages/rig/tests/conftest.py`. Zero user-visible behavior changes.

</domain>

<decisions>
## Implementation Decisions

### models/device.py fate
- **D-01:** Move `DeviceType` StrEnum to `engine/plugin.py` alongside the `Device` Protocol — the full public type surface lives in one place.
- **D-02:** Delete `models/device.py` entirely — no backwards-compat re-export shim. Fix all importers directly. Affected: 4 core source files (`models/rig.py`, `models/graph.py`, `engine/plan/compute.py`, `cli/commands/plan.py`), 2 plugin packages (`rig-hx/device.py`, `rig-chasebliss/device.py`), 8 test files.
- **D-03:** `models/__init__.py` drops `Device` and `DeviceType` from its exports. Consumers import `Device` and `DeviceType` directly from `rig.engine.plugin`. `Rig`, `Scene`, `RigConfig` remain in `models/__init__`.

### Test fixture migration
- **D-04:** Create `FakeDevice` in `packages/rig/tests/conftest.py` — a minimal Protocol-satisfying class (dataclass or simple class) with `id`, `name`, `type`, `config`, `presets` fields plus stub `setup()`, `get_scene_pc_command()`, and `apply()` methods. Pytest auto-discovers conftest.py; no import boilerplate in individual test files.
- **D-05:** Migrate all 8 test files that build `Device(BaseModel)` fixtures to use `FakeDevice`. No real plugin packages as test dependencies in core tests.

### Rig.devices type annotation
- **D-06:** Change `Rig.devices: dict[str, Any]` → `dict[str, Device]` where `Device` is imported from `rig.engine.plugin` (via `TYPE_CHECKING`). Static type-checker enforcement only — no Pydantic `model_validator` added. Devices only enter `rig.devices` via the loader (already type-safe through registry) or tests (FakeDevice satisfies Protocol).
- **D-07:** Remove the `arbitrary_types_allowed=True` migration comment in `rig.py` (the comment says "during the P3 migration" — this phase completes that migration; update or remove the comment).

### hasattr guard removal
- **D-08:** Replace the 3 `hasattr` guards in `apply.py` with plain calls — trust the Protocol. No assert statements; if a non-Protocol object somehow enters, it fails loudly at the call site.
  - `if hasattr(device, "setup"): result = device.setup(...)` → `result = device.setup(...)`
  - `if not hasattr(device, "apply"): ...` → remove the guard; always call `device.apply()`
  - `hasattr(controller, "apply")` → similarly removed

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §TYPE-01 — exact acceptance criteria for this phase; grep patterns that must pass are defined there

### Source files being changed
- `packages/rig/src/rig/models/device.py` — file being deleted; contains `Device(BaseModel)`, `DeviceType`, and the `Preset` import; understand all exports before deleting
- `packages/rig/src/rig/engine/plugin.py` — receives `DeviceType` StrEnum; `Device(Protocol)` already lives here
- `packages/rig/src/rig/models/rig.py` — `devices: dict[str, Any]` → `dict[str, Device]`; `controller` return type changes; `arbitrary_types_allowed` comment updated
- `packages/rig/src/rig/models/graph.py` — imports `Device, DeviceType` from `models.device`; update to `engine.plugin`
- `packages/rig/src/rig/engine/apply.py` — contains the 3 `hasattr` guards to remove
- `packages/rig/src/rig/models/__init__.py` — drops `Device` and `DeviceType` re-exports

### Plugin packages updating their DeviceType import
- `packages/rig-hx/src/rig_hx/device.py` — `from rig.models.device import DeviceType` → `from rig.engine.plugin import DeviceType`
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — same update

### Test files being migrated
- `packages/rig/tests/test_models.py` — builds `Device(BaseModel)` fixtures; migrate to `FakeDevice`
- `packages/rig/tests/test_plan.py` — same
- `packages/rig/tests/test_apply.py` — same
- `packages/rig/tests/test_graph.py` — same
- `packages/rig/tests/test_diff.py` — same
- `packages/rig/tests/test_catalog.py` — same
- `packages/rig/tests/test_appliers.py` — same
- `packages/rig/tests/conftest.py` — new file; defines `FakeDevice`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rig.engine.plugin.Device` (Protocol) — the target type; planner should review all Protocol members to ensure `FakeDevice` satisfies them structurally
- `packages/rig-analog/src/rig_analog/device.py` — reference implementation of a Protocol-satisfying device class; `FakeDevice` can copy this structure minimally
- `rig.engine.plugin.SetupResult`, `DeviceApplyResult` — `FakeDevice.setup()` returns `SetupResult()`, `FakeDevice.apply()` returns a stub `DeviceApplyResult`

### Established Patterns
- `TYPE_CHECKING` guard — `models/rig.py` currently avoids circular imports via `TYPE_CHECKING`. After this phase, `Rig` imports `Device` from `engine.plugin`, which already uses `TYPE_CHECKING` to import `Rig`. The runtime import chain is: `models/rig.py` → `engine/plugin.py` → `engine/state.py` (safe — no cycle at runtime).
- `model_construct` in `plugin_registry.py` — placeholder device instances bypass Pydantic validators; this pattern is unaffected by this phase
- No backwards-compat shims (per CLAUDE.md anti-patterns) — confirmed by user

### Integration Points
- `rig.models.__init__` re-exports — `Device` and `DeviceType` are dropped; downstream consumers that import from `rig.models` will need to update to `rig.engine.plugin`; only internal code affected (single-user tool, no external API consumers)
- `engine/plan/compute.py` and `cli/commands/plan.py` — both import `DeviceType` from `models.device`; update to `engine.plugin`

</code_context>

<specifics>
## Specific Ideas

- No specific implementation references — straightforward import migration and type annotation change
- User confirmed: delete file, fix importers, trust the Protocol, no shims

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 22-retire-the-legacy-device-model*
*Context gathered: 2026-06-15*
