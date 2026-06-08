---
phase: 11-dead-code-compat-removal
type: plan
milestone: v1.2
requirements:
  - CLEANUP-01
  - CLEANUP-02
started: 2026-06-08
---

# Phase 11: Dead Code & Compat Removal

## Goal

The codebase contains no `TODO: 1.2` markers, no multi-file config parsing paths, and no code that was retained solely for backwards compatibility with the pre-v1.2 config layout.

**Requirement IDs:** CLEANUP-01, CLEANUP-02

## Success Criteria

1. `grep -r "TODO.*1\.2" packages/rig/src/` returns zero results
2. `load_rig()` has no code paths that read `signal-chain.yaml`, `scenes/*.yaml`, `pedals/*.yaml`, or `mc6.yaml` — the function accepts only a single `rig.yaml` path
3. All tests pass after removal — no test fixture depends on multi-file layout

## Current State (11 TODO:1.2 markers)

| # | File | TODO | Wave |
|---|------|------|------|
| 1 | `models/preset.py:4` | `AnalogPreset` should move to the analog plugin | W1 |
| 2 | `models/preset.py:15` | `DigitalPreset` should move to the chasebliss plugin | W1 |
| 3 | `models/preset.py:26` | `HXStompPreset` should move to the hx plugin | W1 |
| 4 | `models/preset.py:36` | Barebones `Preset` class in core | W1 |
| 5 | `cli/commands/generate.py:16` | `mc6` command — shouldn't be here, is it used? | W4 |
| 6 | `engine/plan/models.py:26` | `CbaSetupAction` needs to move to cba plugin | W2 |
| 7 | `engine/plan/compute.py:43` | `isinstance(preset, AnalogPreset)` shouldn't be here | W4 |
| 8 | `engine/plan/compute.py:51` | Issue #13 — device should generate its own action | W4 |
| 9 | `engine/apply.py:81` | CBA-specific code (`cba_results`) in apply | W3 |
| 10 | `engine/apply.py:180` | MC6-specific — "too specifically named" | W3 |
| 11 | `engine/apply.py:184` | MC6 device should be responsible for its action | W3 |

## Execution Plan

---

# Wave 1: Move Preset Models to Plugin Packages

**Addresses presets.py TODOs #1-4.** Creates a minimal `Preset` base in core and migrates each plugin-specific preset type to its owning plugin. This is the largest change in Phase 11.

## Files Created
- `packages/rig-analog/src/rig_analog/preset.py` — `AnalogPreset` (extends `rig.models.preset.Preset`)
- `packages/rig-chasebliss/src/rig_chasebliss/preset.py` — `DigitalPreset` (extends core `Preset`)
- `packages/rig-hx/src/rig_hx/preset.py` — `HXStompPreset` (extends core `Preset`)

## Files Modified

### Core
| File | Change |
|------|--------|
| `packages/rig/src/rig/models/preset.py` | Replace 3 plugin-specific models with a single barebones `Preset` base class |
| `packages/rig/src/rig/models/device.py` | Change `Preset` type alias; update `Device.presets` annotation to `list[Preset]`; remove plugin preset imports |
| `packages/rig/src/rig/models/__init__.py` | Remove `AnalogPreset`, `DigitalPreset`, `HXStompPreset` from imports and `__all__` |
| `packages/rig/src/rig/config/loader.py` | Use bare `Preset` type; inline/lazy imports from plugin packages for construction |
| `packages/rig/src/rig/engine/plan/compute.py` | Replace `isinstance(preset, AnalogPreset)` with `hasattr(preset, "values")` or base-class check |

### Plugins
| File | Change |
|------|--------|
| `packages/rig-chasebliss/src/rig_chasebliss/device.py` | Import `DigitalPreset`/`HXStompPreset` from own plugin's preset module |
| `packages/rig-hx/src/rig_hx/device.py` | Import `DigitalPreset`/`HXStompPreset` from own plugin's preset module |

### Tests
| File | Change |
|------|--------|
| `packages/rig/tests/test_models.py` | Import `AnalogPreset`, `DigitalPreset`, `HXStompPreset` from plugin packages |
| `packages/rig/tests/test_plan.py` | Same — update import sources |
| `packages/rig/tests/test_diff.py` | Same — update import sources |
| `packages/rig/tests/test_apply.py` | Same — update import sources |
| `packages/rig/tests/test_catalog.py` | Same — update import sources |
| `packages/rig/tests/test_appliers.py` | Same — update `from rig.models.preset` to plugin imports |
| `packages/rig/tests/test_loader.py` | Same — update `from rig.models.preset import HXStompPreset` |
| `packages/rig/tests/test_devices.py` | Same — update `from rig.models.preset import DigitalPreset` |
| `packages/rig/tests/test_mc6_generator.py` | Same — update `from rig.models.preset import HXStompPreset` |

## Details

### `preset.py` (core) — New shape

```python
from pydantic import BaseModel

class Preset(BaseModel):
    """Barebones preset base — plugin-specific types extend this."""
    id: str
    name: str = ""
    notes: str | None = None
    tags: list[str] = []
```

### `AnalogPreset` in `rig_analog/preset.py`

```python
from rig.models.preset import Preset

class AnalogPreset(Preset):
    pedal: str | None = None
    values: dict[str, float | str | bool]
    photo: str | None = None
```

### `DigitalPreset` in `rig_chasebliss/preset.py`

```python
from rig.models.preset import Preset

class DigitalPreset(Preset):
    pedal: str | None = None
    preset_number: int
    parameters: dict[str, float | str | bool] = {}
```

### `HXStompPreset` in `rig_hx/preset.py`

```python
from rig.models.preset import Preset

class HXStompPreset(Preset):
    preset_number: int
    hlx_file: str
```

### `device.py` — Preset type changes

The `Preset` type alias becomes just the base class:
```python
from rig.models.preset import Preset
```
And `Device.presets` becomes `list[Preset]`. Pydantic will accept subclass instances because they inherit from `Preset`.

### `compute.py` — isinstance check alternatives

The AnalogPreset isinstance check in `_detect_unused_presets`:
```python
# Before:
if isinstance(preset, AnalogPreset):
    continue
# After:
if hasattr(preset, "values"):  # AnalogPreset-specific field
    continue
```

The DigitalPreset isinstance check in `_get_preset_number`:
```python
# Before:
if isinstance(p, DigitalPreset) and p.id == preset_id:
    return p.preset_number
# After: check for the field instead of type
if hasattr(p, "preset_number") and p.id == preset_id:
    return p.preset_number
```

The HXStompPreset isinstance check in `compute_plan`:
```python
# Before:
for hp in [p for p in pedal.presets if isinstance(p, HXStompPreset)]:
# After: check for hlx_file field
for hp in [p for p in pedal.presets if hasattr(p, "hlx_file")]:
```

### `loader.py` — _parse_presets changes

```python
def _parse_presets(device_type: str, preset_list: list[dict]) -> list[Any]:
    if not preset_list:
        return []
    if device_type == "analog":
        from rig_analog.preset import AnalogPreset
        return [AnalogPreset(**p) for p in preset_list]
    if device_type == "modeler":
        from rig_hx.preset import HXStompPreset
        return [HXStompPreset(**p) for p in preset_list]
    from rig_chasebliss.preset import DigitalPreset
    return [DigitalPreset(**p) for p in preset_list]
```

## Verification

```bash
# Plugin packages define their preset types
grep -c "class AnalogPreset" packages/rig-analog/src/rig_analog/preset.py  # 1
grep -c "class DigitalPreset" packages/rig-chasebliss/src/rig_chasebliss/preset.py  # 1
grep -c "class HXStompPreset" packages/rig-hx/src/rig_hx/preset.py  # 1

# Core has only barebones Preset
grep -c "class Preset" packages/rig/src/rig/models/preset.py  # 1
grep -c "class AnalogPreset\|class DigitalPreset\|class HXStompPreset" packages/rig/src/rig/models/preset.py  # 0

# Device uses list[Preset]
python -c "from rig.models.device import Device; print([f.name for f in Device.model_fields().values()])"

# All tests pass
uv run pytest packages/ -q --tb=short
```

---

# Wave 2: Move CbaSetupAction to CBA Plugin

**Addresses plan/models.py TODO #6.** Moves the `CbaSetupAction` model from core into `rig_chasebliss` where it belongs. The CBA plugin already owns all CBA setup logic — the model definition should live there too.

## Files Created
- `packages/rig-chasebliss/src/rig_chasebliss/models.py` — defines `CbaSetupAction`

## Files Modified

| File | Change |
|------|--------|
| `packages/rig/src/rig/engine/plan/models.py` | Remove `CbaSetupAction` class and its TODO |
| `packages/rig/src/rig/engine/plan/__init__.py` | Remove `CbaSetupAction` from imports and `__all__` |
| `packages/rig-chasebliss/src/rig_chasebliss/device.py` | Import `CbaSetupAction` from own plugin's `models.py` |
| `packages/rig-chasebliss/src/rig_chasebliss/applier.py` | Import `CbaSetupAction` from own plugin's `models.py` |
| `packages/rig/tests/test_appliers.py` | Import `CbaSetupAction` from `rig_chasebliss.models` |

## Details

### `rig_chasebliss/models.py`

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CbaSetupAction(BaseModel):
    device: str
    midi_channel: int
    type: Literal["establish_channel", "build_preset", "register_scenes"]
    preset_id: str | None = None
    preset_name: str | None = None
    preset_number: int | None = None
    scene_refs: list[str] = []
    cc_params: list[dict[str, int]] = []
```

### Updated imports

**rig_chasebliss/device.py** (inline import):
```python
# Before:
from rig.engine.plan.models import CbaSetupAction
# After:
from rig_chasebliss.models import CbaSetupAction
```

**rig_chasebliss/applier.py**:
```python
# Before:
from rig.engine.plan import CbaSetupAction
# After:
from rig_chasebliss.models import CbaSetupAction
```

**test_appliers.py**:
```python
# Before:
from rig.engine.plan import CbaSetupAction
# After:
from rig_chasebliss.models import CbaSetupAction
```

## Verification

```bash
# CbaSetupAction present in CBA plugin, absent from core
grep -c "class CbaSetupAction" packages/rig-chasebliss/src/rig_chasebliss/models.py  # 1
grep -c "CbaSetupAction" packages/rig/src/rig/engine/plan/models.py  # 0

# All tests pass
uv run pytest packages/ -q --tb=short
```

---

# Wave 3: Clean Up apply.py Dead Code and TODOs

**Addresses apply.py TODOs #9-11.** Removes the unused `cba_results` variable, cleans the MC6 programming phase to be more generic, and removes all TODO markers from apply.py.

## Files Modified

| File | Change |
|------|--------|
| `packages/rig/src/rig/engine/apply.py` | Remove `cba_results` (never populated); clean MC6 section; remove 3 TODO markers |

## Details

Three changes in apply.py:

**Change 1: Remove unused `cba_results`**

The variable `cba_results: list[DeviceApplyResult] = []` is declared but never modified (no `.append()` calls). It's only used in `ApplyResult(cba_setup=cba_results, ...)` — returning an empty list. Remove it entirely.

- Delete `cba_results: list[DeviceApplyResult] = []` declaration
- Remove `cba_results=cba_results` from all `ApplyResult(...)` constructor calls
- The `ApplyResult.cba_setup` field stays as a model field (backward compat for any consumers), but always defaults to `[]`

**Change 2: Simplify MC6 section**

Replace the three TODO markers with generic code:

```python
# --- Phase 2: Controller programming ---
if rig and rig.controller and not scene:
    controller = rig.controller
    if hasattr(controller, "apply") and midi:
        console.print("\n[bold]Controller Programming Phase[/bold]")
        controller_action = DeviceAction(
            device=controller.id,
            device_type="controller",
            status="configure",
            preset_name="",
        )
        controller_ctx = DeviceApplyContext(
            action=controller_action,
            state=ctx.state,
            rig=rig,
            dry_run=ctx.dry_run,
            confirmation_io=ctx.confirmation_io,
            midi=ctx.midi,
            connected_devices=ctx.connected_devices,
            config_path=ctx.config_path,
        )
        controller.apply(controller_ctx)
        if controller.id in state.devices:
            state_modified = True
```

This makes the controller section generic — no `mc6_device`/`mc6_banks` variables, no device-ID hardcoding. It uses `rig.controller` (already a property on Rig) and `hasattr` to check for the apply method. The `DeviceApplyContext` import is already present.

**Change 3: Remove the "too big a function" comment at the top**

Remove `# TODO: i think this is too big a function` — this is not a `TODO: 1.2` marker, but it's adjacent cleanup worth doing.

## Verification

```bash
# No TODO markers in apply.py
grep -c "TODO" packages/rig/src/rig/engine/apply.py  # 0

# cba_results variable absent
grep -c "cba_results" packages/rig/src/rig/engine/apply.py  # 0

# mc6_device/mc6_banks removed
grep -c "mc6_device\|mc6_banks" packages/rig/src/rig/engine/apply.py  # 0

# All tests pass
uv run pytest packages/ -q --tb=short
```

---

# Wave 4: Clean Up compute.py, Remove _load_scenes, Fix generate.py

**Addresses compute.py TODOs #7-8, generate.py TODO #5, and CLEANUP-02.** Removes dead `_load_scenes` compat function from loader, updates compute.py isinstance checks and resolves issue #13, fixes the generate.py error message, and removes the _load_scenes test.

## Files Modified

| File | Change |
|------|--------|
| `packages/rig/src/rig/config/loader.py` | Remove dead `_load_scenes()` function |
| `packages/rig/src/rig/engine/plan/compute.py` | Resolve TODOs #7 (isinstance checks) and #8 (issue #13) |
| `packages/rig/src/rig/cli/commands/generate.py` | Update error message; resolve TODO #5 |
| `packages/rig/tests/test_loader.py` | Remove `_load_scenes` test |

## Details

### `loader.py` — Remove `_load_scenes`

The function `_load_scenes` is never called anywhere in the codebase (confirmed via grep). Remove:
- The function definition (109-122)
- Its docstring with backward-compat justification

No other changes needed — no callers exist.

### `compute.py` — Resolve TODOs

**TODO #7:** The `isinstance(preset, AnalogPreset)` check in `_detect_unused_presets` is updated during Wave 1 (changing to `hasattr(preset, "values")`). In this wave, remove the remaining TODO marker.

**TODO #8 (issue #13):** The TODO says "the device should be in charge of generating its device action" — this is a known architectural debt about the `compute_plan` function doing device-level action construction instead of delegating to devices. This is a substantive design change (D-13 in the project backlog) and not something to fix inline. **Resolution:** Replace the TODO with a proper reference to the GitHub issue and add a `# HACK:` label:

```python
# HACK: issue #13 — device should be in charge of generating its device action
# Instead, compute_plan() manually constructs DeviceAction for every device.
# This prevents plugins from customizing their action output.
```

### `generate.py` — Resolve TODO #5

The `generate mc6` command IS actively used (the `rig generate mc6` CLI path works and is documented). **Resolution:** The command stays. Remove the TODO. Update the fallback error message from `mc6.yaml` to `rig.yaml`:

```python
# Before:
console.print("[yellow]No MC6 configuration found (mc6.yaml missing or empty)[/yellow]")
# After:
console.print("[yellow]No MC6 configuration found (controller has no scenes or banks)[/yellow]")
```

### `test_loader.py` — Remove _load_scenes test

Remove the test class/method `test_load_scenes_nonexistent_dir_returns_empty` (lines ~278-287) since it tests dead code.

## Verification

```bash
# _load_scenes removed from loader
grep -c "_load_scenes" packages/rig/src/rig/config/loader.py  # 0

# No TODO markers remain in src
grep -r "TODO.*1\.2" packages/rig/src/  # 0 results

# generate.py has no mc6.yaml reference
grep -c "mc6.yaml" packages/rig/src/rig/cli/commands/generate.py  # 0

# All tests pass
uv run pytest packages/ -q --tb=short
```

---

# Full Verification

After all waves complete:

```bash
# CLEANUP-01: No TODO:1.2 markers
grep -r "TODO.*1\.2" packages/rig/src/ 2>/dev/null || echo "PASS: No TODO:1.2 markers"

# CLEANUP-02: No multi-file config paths
grep -n "signal-chain.yaml\|mc6.yaml\|pedals/.*\.yaml\|scenes/.*\.yaml" packages/rig/src/ 2>/dev/null || echo "PASS: No multi-file config paths"

# load_rig accepts only single rig.yaml path (confirmed by grep for _load_scenes/scenes_dir)
grep -c "_load_scenes\|scenes_dir" packages/rig/src/rig/config/loader.py  # Expected: 0

# All tests pass
uv run pytest packages/ -q --tb=short

# Total test count: should remain at ~274 (no functional tests removed)
```

## Rollback Strategy

Each wave is self-contained and tested independently. If any wave fails:
1. Run `git checkout -- packages/` to revert all changes
2. Address the failure and re-apply
3. Use the wave-level verification commands to validate before proceeding to next wave
