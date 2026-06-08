---
id: "phase-13"
plan_id: "01"
wave: 1
depends_on: []
requirements_addressed: [DESIGN-01, DESIGN-02]
autonomous: true
status: complete
---

# Plan 01: Resolve Remaining TODO:1.2 Markers

## Objective

Address the 3 remaining `TODO: 1.2` markers: move `Rig.scenes` from a stored field to a computed property (scenes live on controllers), and remove the redundant HX-specific block in `compute.py`.

## Tasks

### Task 1: Convert Rig.scenes from field to property

<read_first>
- packages/rig/src/rig/models/rig.py
- packages/rig/src/rig/config/loader.py (lines 200-240, where Rig(...) is constructed)
</read_first>

<action>
In `packages/rig/src/rig/models/rig.py`:
1. Remove `scenes: dict[str, Scene] = {}` from the `Rig` model field list
2. Add a `@property` called `scenes` that reads scenes from all controller devices:

```python
@property
def scenes(self) -> dict[str, Scene]:
    """Aggregate scenes from all controller devices.

    Scenes live in each controller's config; this property provides
    a unified view for consumers that iterate scenes.
    """
    aggregated: dict[str, Scene] = {}
    for device in self.devices.values():
        if device.type == DeviceType.CONTROLLER:
            cfg = device.config
            raw_scenes = cfg.get("scenes", {}) if isinstance(cfg, dict) else getattr(cfg, "scenes", {})
            for name, data in raw_scenes.items():
                if isinstance(data, dict):
                    aggregated[name] = Scene(
                        name=name,
                        description=data.get("description"),
                        presets=data.get("presets", {}),
                        tags=data.get("tags", []),
                    )
    return aggregated
```

Remove the `Scene` import from rig.py's top-level imports — it's no longer needed as a field type hint. Actually, the property still returns `dict[str, Scene]`, so keep the import.

In `packages/rig/src/rig/config/loader.py`:
1. Remove the `scenes=` keyword argument from the `Rig(...)` constructor call (around line 224)
2. Remove the TODO comment on line 220: `# TODO: 1.2 scenes should only live at the controller level, not the rig level...`
3. The extracted scenes dict from `_extract_controller_scenes` is still computed but no longer stored — it only feeds the `scenes` parameter to the Rig constructor. Since we're making scenes a property, remove the `scenes` variable from the loader's build loop or keep it for the log statement on line 235 (`len(rig.scenes)` now works via the property).

Actually, keep the log statement as-is — it calls `len(rig.scenes)` which will hit the property.
</action>

<acceptance_criteria>
- `Rig` model has no `scenes` field in its model fields
- `Rig.scenes` is a property, not a stored field
- `loader.py` no longer passes `scenes=` to `Rig(...)` constructor
- `loader.py` line 220 TODO marker removed
- `uv run pytest packages/ -q` passes all tests
</acceptance_criteria>

---

### Task 2: Remove compute.py TODO markers and HX-specific block

<read_first>
- packages/rig/src/rig/engine/plan/compute.py (lines 50-115)
</read_first>

<action>
In `packages/rig/src/rig/engine/plan/compute.py`:

1. Remove line 70 TODO comment: `# TODO: 1.2 scenes will go on the controller moving forward`
2. Remove the HX-specific block at lines ~100-118 and the surrounding `is_hx` variable:

Current code (lines ~95-118):
```python
is_hx = pedal.type.value == "modeler"
preset_number = None

# TODO: 1.2 why is this in here? this should be part of the hx preset definition?
if is_hx:
    for hp in [p for p in pedal.presets if hasattr(p, "hlx_file")]:
        if hp.id == preset_id:
            preset_number = hp.preset_number
            break
    logger.debug("    → HX preset #%s", preset_number)
else:
    preset_number = _get_preset_number(rig, pedal_id, preset_id)
    logger.debug("    → digital preset #%s", preset_number)
```

Replace with:
```python
preset_number = _get_preset_number(rig, pedal_id, preset_id)
logger.debug("    → preset #%s", preset_number)
```

No `is_hx` variable needed — `_get_preset_number` works for any preset that has `preset_number` (including HXStompPreset which inherits from Preset with `preset_number`).
</action>

<acceptance_criteria>
- `compute.py` line 70 TODO marker removed
- `compute.py` line 108 TODO marker removed
- No `is_hx` variable in `compute.py`
- No HX-specific branch — all preset_number lookups go through `_get_preset_number`
- `uv run pytest packages/ -q` passes all tests
</acceptance_criteria>

---

### Task 3: Verify TODO:1.2 markers are all resolved

<read_first>
- N/A — run grep
</read_first>

<action>
Run `grep -rn "TODO.*1\.2" --include="*.py" packages/ | grep -v __pycache__` and confirm zero results in source.
</action>

<acceptance_criteria>
- `grep -rn "TODO.*1\.2" --include="*.py" packages/ | grep -v __pycache__` returns zero results
</acceptance_criteria>

## Verification

```bash
# No TODO:1.2 markers remain
grep -rn "TODO.*1\.2" --include="*.py" packages/ | grep -v __pycache__ && echo "FAIL: markers remain" || echo "PASS: no markers"

# Rig.scenes is a property, not a field
grep -n "scenes" packages/rig/src/rig/models/rig.py

# No HX-specific branch in compute.py
grep -n "is_hx" packages/rig/src/rig/engine/plan/compute.py && echo "FAIL: is_hx remains" || echo "PASS: is_hx removed"

# All tests pass
uv run pytest packages/ -q
```

## Wave Assignment

Wave 1 — all tasks are independent or sequential by file:
- Task 1 (Rig.scenes property) ⟶ Wave 1
- Task 2 (compute.py cleanup) ⟶ Wave 1
- Task 3 (verify) ⟶ Wave 1

## must_haves

- `Rig.scenes` is a `@property`, not a `dict` field
- No `is_hx` branch in `compute.py`
- Zero `TODO: 1.2` markers in source
- All tests pass

## Artifacts this phase produces

- Files modified: `rig.py`, `loader.py`, `compute.py`
- No new files or symbols created — this is a refactoring/cleanup phase
