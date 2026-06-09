# Stack Research — v1.3 Chase Bliss Pedal Support

**Milestone:** v1.3 Chase Bliss Pedal Support
**Date:** 2026-06-08

---

## Summary

No new dependencies. All changes are within the existing `rig-chasebliss` package using Pydantic v2 and the existing `Control`/`ControlType` model. The one model change needed is adding an optional `default` field to `Control` to support the reset-to-defaults flow.

---

## Model Changes Required

### Add `default: float | None = None` to `Control`

The reset flow sends all parameter controls to their default value. Without a `default` on `Control`, the reset function must infer defaults (e.g., always 64 for knobs, 0 for toggles) — which is fragile and doesn't account for pedals where "neutral" isn't 64 or 0.

**Recommended change to `catalog.py`:**

```python
class Control(BaseModel):
    name: str
    type: ControlType
    midi_cc: int | None
    min: float
    max: float
    default: float | None = None  # ADD THIS
    positions: list[str] = []
    expression_assignable: bool = False
```

`float | None` handles all CC value types (knob 0-127, toggle position index, dip 0/1). `None` means "no default defined / excluded from reset" — footswitches and utility controls set `default=None`.

**Backward compatibility:** `default=None` as the field default means all existing `Control(...)` constructor calls in the existing Mood MkII catalog continue to work without modification. The field is additive.

### No Changes to `DigitalPreset` model

The `DigitalPreset.parameters: dict[str, float | str | bool]` field stays as-is. Parameter validation is done imperatively in apply(), not via Pydantic validators. See Validation section below.

---

## Validation Approach

**Location: imperative check in `ChaseBlissDevice.apply()`, not a Pydantic model_validator.**

Reasons:
1. Validation requires the catalog (`get_controls(manufacturer, model)`) which is an external lookup — Pydantic validators run at model construction time before the catalog is available
2. A Pydantic validator on `DigitalPreset` would need the device model as context, requiring `model_validator(mode='before')` with injected context — significant complexity for limited gain
3. Existing `TODO: 1.3 when parsing the cba device, we should have custom validation that the pedal type supports the param names?` (in preset.py) implies the author expected imperative validation at device apply time

**What validation checks:**
- For each key in `preset.parameters`: key must match a control `name` in the device's catalog
- For each value in `preset.parameters`: value must be within `control.min` to `control.max`
- Unknown parameter names → raise `ValidationError` with the offending key
- Out-of-range values → raise `ValidationError` with control name, value, and allowed range

---

## Dependencies

**None required.** All patterns use:
- `pydantic>=2.0` — already a dependency; `model_copy()` used for `default` field addition
- Python stdlib only for reset logic
- Existing `get_controls()` function from `catalog.py`

---

## Recommendation

1. Add `default: float | None = None` to `Control` in catalog.py
2. Set explicit `default=` values on all controls in Mood MkII catalog (knobs→64, toggles→0, dipswitches→0, footswitches/utility→None)
3. Set explicit `default=` values on all Wombtone and Brothers controls during catalog authoring
4. Implement validation imperatively in `ChaseBlissDevice.apply()` before sending CCs
5. Implement reset as a new helper function: `def build_reset_actions(controls: list[Control]) -> list[tuple[int, int]]` — returns (cc, default_value) for all controls where `default is not None`
