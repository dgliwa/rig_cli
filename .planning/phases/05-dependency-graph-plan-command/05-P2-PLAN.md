---
phase: 5
plan: P2
type: implementation
wave: 1
depends_on: []
files_modified:
  - src/rig/engine/plan/models.py
  - src/rig/engine/plan/__init__.py
requirements: [PLAN-02, D-04, D-05, D-06]
must_haves:
  - DeviceAction has before and after fields typed str | None defaulting to None
  - Plan has missing_refs and unused_presets fields typed list[str] defaulting to []
  - Plan.model_dump_json() includes all four new fields in output
  - Existing tests in test_plan.py continue to pass without modification
---

# Phase 5 P2: Plan Model Extensions

## Context

`DeviceAction` and `Plan` need new fields before `compute_plan()` can populate them (P3). This
plan adds those fields to the Pydantic models only — no logic changes. `before` and `after` on
`DeviceAction` record the preset ID transition (PLAN-02). `missing_refs` and `unused_presets` on
`Plan` are the diagnostic accumulation lists (D-04, D-05, D-06). All fields have safe defaults so
existing callers that don't populate them continue to work.

Field style follows the existing pattern in `src/rig/engine/plan/models.py`: use `list[str] = []`
(not `Field(default_factory=list)`) and `str | None = None` for optional scalars.

---

## Task P5-T4: Extend DeviceAction and Plan in models.py

**File:** `src/rig/engine/plan/models.py`

**Changes:**

Add two fields to `DeviceAction` after the existing `instructions: list[str] = []` line:

- `before: str | None = None` — preset ID that was active on this device before this plan was
  computed (the `actual_preset` from state); `None` when the scene is new and no prior state exists
- `after: str | None = None` — preset ID that will be active after this plan is applied (the
  desired `preset_id` from the scene config)

Add two fields to `Plan` after the existing `cba_setup: list[CbaSetupAction] = []` line:

- `missing_refs: list[str] = []` — human-readable strings describing broken scene→preset
  references; each entry formatted as
  `"scene '{scene_name}' → device '{device_id}' preset '{preset_id}' not found"`
- `unused_presets: list[str] = []` — human-readable strings describing defined but unreferenced
  presets; each entry formatted as `"{device_id}: '{preset_id}' unused"`

No other changes to this file. `from __future__ import annotations` is already present. The
existing `status: Literal["configure", "verify", "analog"]` on `DeviceAction` is unchanged —
do not add `"no_change"`. The `--show-unchanged` flag in P4 operates at the scene level
(`ScenePlan.status == "unchanged"`), not the device-action level; compute never produces a
`"no_change"` action status.

The `status: Literal["clean", "changes_detected"]` on `Plan` is unchanged.

---

## Task P5-T5: Verify __init__.py re-exports

**File:** `src/rig/engine/plan/__init__.py`

**Changes:**

Read the current `__init__.py` to confirm whether `Plan`, `DeviceAction`, `ScenePlan`,
`CbaSetupAction` are all exported. If any new public name from `models.py` needs to be accessible
via `from rig.engine.plan import X`, add it to `__all__` or the explicit import list.

The new fields on existing models are automatically available — no new export names are required
unless a new top-level symbol was introduced (none were in this plan). Confirm the file is
consistent and make no unnecessary changes.

### Verification

```
uv run pytest tests/test_plan.py -v
```

All pre-existing tests must pass. The models are backward-compatible: all new fields have defaults.

```
uv run python -c "from rig.engine.plan.models import Plan, DeviceAction; p = Plan(status='clean'); print(p.missing_refs, p.unused_presets); a = DeviceAction(device='x', device_type='midi', status='configure'); print(a.before, a.after)"
```

Output must be `[] []` and `None None` — confirming defaults are correct.
