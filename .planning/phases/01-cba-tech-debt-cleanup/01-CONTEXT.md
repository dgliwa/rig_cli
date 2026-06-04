# Phase 1: CBA Tech-Debt Cleanup - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove private-symbol leakage and raw dict mutation in the CBA applier before Phase 2 protocol work begins. Three targeted refactors — no new behavior, no new features:
1. Extract `mark_preset_saved` helper to `base.py` (CBA-01)
2. Rename `_detect_cba_setup` → `detect_cba_setup` public in `plan.py`, update import in `chase_bliss.py` (CBA-02)
3. Inline `_is_cba` predicate into `detect_cba_setup` — eliminate the symbol (CBA-03)

</domain>

<decisions>
## Implementation Decisions

### _is_cba disposition (CBA-03)
- **D-01:** Inline `_is_cba` directly into `detect_cba_setup`. The predicate is 3 lines, called exactly once, never referenced outside `plan.py`. Removing the symbol is cleaner than promoting it to public.

### Test coverage
- **D-02:** No new tests for Phase 1. The refactor is behavior-neutral — if existing `ChaseBlissApplier` and `apply_plan` tests pass after the renames and helper extraction, that is sufficient. Phase 2 (DEC-07) adds `tests/fakes.py` and rewrites patched tests; Phase 1 does not pre-build test infrastructure.

### mark_preset_saved composition (builder discretion)
- **D-03:** `mark_preset_saved(state, device, preset_id)` should compose with the existing `update_device_state` helper in `base.py` — read `current.presets_saved`, set the new key, call `update_device_state(state, device, presets_saved=updated_dict)`. This keeps a single code path for all state mutations.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §CBA-01, §CBA-02, §CBA-03 — exact signatures, locations, and success criteria for all three Phase 1 items

### Roadmap
- `.planning/ROADMAP.md` §Phase 1 — success criteria (three specific true/false assertions to verify)

### Files being modified
- `src/rig/engine/appliers/chase_bliss.py` — `_build_preset` (lines 143–212) has the raw dict mutation; line 9 has the private import of `_detect_cba_setup`
- `src/rig/engine/plan.py` — `_is_cba` (line 64) and `_detect_cba_setup` (line 71) are the symbols being changed
- `src/rig/engine/appliers/base.py` — `update_device_state` (line 39) already exists here; `mark_preset_saved` goes in this file

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `update_device_state(state, device, **fields)` in `base.py:39` — existing general-purpose state mutation helper; `mark_preset_saved` should delegate to it rather than duplicate the `model_copy` pattern
- `DeviceState` in `state.py` — `presets_saved: dict[str, bool] = {}` is the field being updated

### Established Patterns
- All device state updates go through `model_copy(update=...)` (Pydantic immutable-update pattern) — `update_device_state` encapsulates this; `mark_preset_saved` must not bypass it
- Private helpers in `plan.py` are prefixed with `_` — removing `_detect_cba_setup`'s underscore makes it explicitly public API for cross-module import

### Integration Points
- `chase_bliss.py:9` imports `_detect_cba_setup` — this import must be updated to `detect_cba_setup` (no underscore)
- `chase_bliss.py:40` calls `_detect_cba_setup` inside `_enqueue_new_actions` — update call site
- `plan.py:220` calls `_detect_cba_setup` — update this call site too

</code_context>

<specifics>
## Specific Ideas

No specific requirements — refactor follows the signatures in REQUIREMENTS.md exactly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-cba-tech-debt-cleanup*
*Context gathered: 2026-06-04*
