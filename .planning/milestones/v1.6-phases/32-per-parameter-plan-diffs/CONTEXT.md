# Phase 32: Per-Parameter Plan Diffs — Context

## Phase Goal
`rig plan` output shows the specific CC values or knob positions that will change, not just a "changed" label at the scene level.

## Requirements
- PLAN-01: `rig plan` per device-action lists each parameter with `before:` and `after:` values when changed
- PLAN-02: Parameters unchanged within a "changed" scene are not listed; JSON format includes parameter diff structure

## Depends On
Phase 30 (complete ✓)

## Success Criteria
1. `rig plan` output per device-action lists each parameter with `before:` and `after:` values when changed
2. Parameters that are unchanged within a "changed" scene are not listed
3. Analog devices list knob/switch names and positions, not CC numbers
4. JSON output (`--format json`) includes the parameter diff structure

## Current State Analysis

### What exists
- `DeviceAction` model: `before: str | None`, `after: str` tracks preset IDs only (not parameter values)
- `AnalogPreset.values: dict[str, float | str | bool]` — knob/switch names → positions
- `DigitalPreset.parameters: dict[str, float | str | bool]` — CC parameter names → values (Chase Bliss)
- `HXStompPreset` — has only `preset_number` + `hlx_file`; no per-parameter data

### What's missing
- No `param_diff` field on `DeviceAction` — the model stores no parameter-level change info
- `compute.py` does not look up preset objects or compare their parameter dicts
- `plan.py` display shows preset name + PC# only; no sub-line parameter diffs

## Design Sketch

### 1. New model type
```python
class ParamDiff(BaseModel):
    name: str
    before: float | str | bool | None  # None when no prior state
    after: float | str | bool
```

Add to `DeviceAction`:
```python
param_diff: list[ParamDiff] = []
```

### 2. Compute change
In `compute.py`, when building `DeviceAction`, look up:
- `before_preset`: the preset object matching `actual_preset` ID (may be None)
- `after_preset`: the preset object matching `preset_id`

Extract parameter dict:
- Analog: `preset.values`
- Digital (Chase Bliss): `preset.parameters`
- HX Stomp / MIDI generic: no parameters (empty diff)

Build diff: for each key in `after_params`, include in `param_diff` only if value changed or `before_preset` is None.

### 3. Display change (plan.py)
Under each device action line with `param_diff`, print sub-lines:
```
    ~ tumnus: 'edge-of-breakup' → 'crunch' (manual)
        gain: 5.0 → 8.0
        tone: 3 → 7
```
Only show params that changed. If `before` is None, display as `? → 8.0`.

## Files to Modify

| File | Change |
|------|--------|
| `packages/rig/src/rig/engine/plan/models.py` | Add `ParamDiff` model; add `param_diff: list[ParamDiff]` to `DeviceAction` |
| `packages/rig/src/rig/engine/plan/compute.py` | Extract parameter diffs when building DeviceAction |
| `packages/rig/src/rig/cli/commands/plan.py` | Display parameter diffs under device action lines |

## Tests to Add

| File | Test |
|------|------|
| `packages/rig/tests/test_plan.py` | analog action has param_diff with changed knob positions |
| `packages/rig/tests/test_plan.py` | digital action has param_diff with changed CC values |
| `packages/rig/tests/test_plan.py` | unchanged params not included in param_diff |
| `packages/rig/tests/test_plan.py` | before=None when no prior state |
| `packages/rig/tests/test_plan.py` | HX Stomp action has empty param_diff |
| `packages/rig/tests/test_cli_plan.py` | parameter diffs printed under action line |
| `packages/rig/tests/test_cli_plan.py` | unchanged params not shown |

## Key Constraints
- Tech stack: Python 3.13, uv, Typer, Pydantic — no new deps
- No MIDI interaction in plan — plan is read-only
- Protocol-first: no ABC inheritance introduced
- Scope boundary: this is display-only; no changes to apply, state, or plugin protocols
- If "before" preset ID from state.json no longer exists in presets list, treat all after-params as having `before=None`
