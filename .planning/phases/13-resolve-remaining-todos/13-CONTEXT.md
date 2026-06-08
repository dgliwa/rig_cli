# Phase 13: Resolve Remaining TODO:1.2 Markers — Context

**Gathered:** 2026-06-08
**Status:** Ready for planning
**Source:** User discussion

<domain>
## Phase Boundary

Phase 13 resolves 3 remaining `TODO: 1.2` markers left in the codebase after Phases 11-12:

1. **loader.py:220** — "scenes should only live at the controller level, not the rig level"
2. **compute.py:70** — "scenes will go on the controller moving forward"
3. **compute.py:108** — "why is this in here? this should be part of the hx preset definition?"

These are architectural improvement notes from the v1.2 Cleaner Core that were deliberately left as markers rather than tackled during the cleanup sweep.
</domain>

<decisions>
## Implementation Decisions

### DESIGN-01 — Move scenes to controller level

- **Don't remove `Rig.scenes` completely** — too many consumers (plan, diff, validate, status, state) depend on it. Instead, convert it from a stored field to a computed `@property` that aggregates scenes from controller devices.
- Remove `scenes: dict[str, Scene]` from the field list on `Rig(BaseModel)`
- Add `property scenes` that reads `config.scenes` from controller devices and returns a `dict[str, Scene]`
- Remove the `scenes=` keyword argument from the `Rig(...)` constructor call in `loader.py`
- The `Rig.scenes` access pattern stays the same for consumers (iterating, reading, counting) — no consumer changes needed
- This resolves loader.py:220 and compute.py:70

### DESIGN-02 — Remove HX-specific block from compute.py

- The `is_hx` block in `compute.py` (lines ~100-110) manually iterates HX presets to find `preset_number`
- But `HXStompPreset` already has `preset_number` — `_get_preset_number()` (which checks `hasattr(p, "preset_number")`) would find it for any preset type including HX
- Remove the `is_hx` branch entirely; use `_get_preset_number()` for all digital/modeler presets
- This resolves compute.py:108

### Claude's Discretion
- No other changes needed — both TODOs are self-contained design refinements
</decisions>

<canonical_refs>
## Canonical References

### Rig model
- `packages/rig/src/rig/models/rig.py` — `scenes: dict[str, Scene]` field to remove, replace with property

### Loader
- `packages/rig/src/rig/config/loader.py` — remove `scenes=` from `Rig(...)` constructor call; remove TODO marker

### Plan compute
- `packages/rig/src/rig/engine/plan/compute.py` — remove HX-specific block; remove TODO markers

### Controller device config
- `packages/rig/tests/fixtures/sample_rig/rig.yaml` — scenes are defined under `config.scenes` on the controller
</canonical_refs>

<specifics>
## Specific Ideas

- `_get_preset_number` in compute.py already handles `hasattr("preset_number")` — works for HXStompPreset which has `preset_number` and `hlx_file`
- The `is_hx` block was needed when scenes were filtered by `hasattr("hlx_file")` but `_get_preset_number` was added since then and supersedes it
- No new requirements, no test changes expected beyond possibly updating test assertions if Rig.scenes type/behavior changes
</specifics>

<deferred>
## Deferred Ideas
- None
</deferred>

---

*Phase: 13-resolve-remaining-todos*
*Context gathered: 2026-06-08 via user discussion*
