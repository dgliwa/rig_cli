---
phase: 03-core-domain-refactor
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/rig/models/device.py
  - src/rig/models/controller.py
  - src/rig/models/rig.py
  - src/rig/config/loader.py
  - src/rig/engine/plugin.py
  - src/rig/engine/plugin_registry.py
  - tests/test_models.py
  - tests/test_loader.py
  - tests/test_plugin.py
  - tests/test_mc6_generator.py
  - tests/test_diff.py
  - tests/test_plan.py
  - tests/test_apply.py
findings:
  critical: 3
  warning: 5
  info: 0
  total: 8
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-05
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The phase 3 refactor successfully consolidates the controller model into the `Device` graph (via `ControllerConfig` and `DeviceType.CONTROLLER`), introduces the `DevicePlugin` Protocol and `PluginRegistry` scaffolding, and adds reasonable test coverage. The new models, plugin protocol, and registry are structurally sound. However, three critical defects exist: two in the loader that can cause crashes or silent data loss, and one misleading test whose assertion passes vacuously and does not cover the behavior implied by its name. Five additional warnings degrade type safety, dead code hygiene, and test reliability.

## Critical Issues

### CR-01: Empty YAML files cause TypeError instead of ParseError

**File:** `src/rig/config/loader.py:23`
**Issue:** `_read_yaml` calls `yaml.safe_load()` which returns `None` for empty or comment-only YAML files. The result is passed directly to `Device(**data)`, `Scene(**data)`, or `AnalogPreset(**data)` without a None guard. Python raises `TypeError: argument after ** must be a mapping, not NoneType` — an unhandled exception that does not produce the expected `ParseError` and gives the user no actionable message.

**Fix:**
```python
def _read_yaml(path: Path):
    ...
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ParseError(f"Empty or blank YAML file: {path}")
        ...
        return data
    except yaml.YAMLError as e:
        ...
```

---

### CR-02: Scenes are silently dropped when no controller device is present

**File:** `src/rig/config/loader.py:195-201`
**Issue:** In `load_rig`, scene YAML files are loaded correctly into the `scenes` dict. They are then wired into the `ControllerConfig` of the first device with `DeviceType.CONTROLLER`. If no such device exists (e.g., a user does not define an MC6), the scenes dict is discarded without any warning or error. Downstream code reads `rig.scenes` via `Rig._controller_device`, which returns `{}`. As a consequence, `_validate_references` skips all scene-level validation and the caller sees an empty scene set — a silent data loss.

**Fix:** Raise a warning (or error) when scenes are loaded but no controller device exists:
```python
if scenes:
    ctrl_device = next((d for d in devices.values() if d.type == DeviceType.CONTROLLER), None)
    if ctrl_device is None:
        logger.warning(
            "Loaded %d scene(s) but no CONTROLLER device found — scenes will not be applied",
            len(scenes),
        )
        # or: raise ValidationError("Scenes defined but no controller device found")
    elif isinstance(ctrl_device.config, ControllerConfig):
        updated_config = ctrl_device.config.model_copy(update={"scenes": scenes})
        devices[ctrl_device.id] = ctrl_device.model_copy(update={"config": updated_config})
```

---

### CR-03: `test_clean_plan_prints_no_changes` tests the wrong plan state

**File:** `tests/test_apply.py:68-75`
**Issue:** The test name implies it verifies that a **clean** plan prints "No changes needed." In reality, `compute_plan(config)` is called without `root_path`, so the state is empty. Every scene is therefore `"new"` and `plan.status` is `"changes_detected"` — not `"clean"`. The assertion `assert "No changes needed" not in captured.out` passes trivially because `apply_plan` never prints that message when status is `changes_detected`. The actual behavior of a clean plan is never tested.

**Fix:** Provide a state file that matches the desired config so `plan.status == "clean"`, then assert the expected message:
```python
def test_clean_plan_prints_no_changes(self, tmp_path, capsys):
    config = _make_config()
    _write_state_file(
        tmp_path,
        {
            "devices": {
                "hx-stomp": {"last_preset": "clean-edge"},
                "brothers": {
                    "last_preset": "low-gain",
                    "channel_established": True,
                    "midi_channel": 3,
                    "presets_saved": {"low-gain": True},
                    "registration_done": True,
                },
            },
            "scenes": {"test-scene": {}},
        },
    )
    plan = compute_plan(config, root_path=str(tmp_path))
    assert plan.status == "clean"
    state_adapter = InMemoryStateAdapter()
    midi_io = InMemoryMidiConnectionIO()
    apply_plan(plan, state_writer=state_adapter, midi_connection_io=midi_io, dry_run=True)
    captured = capsys.readouterr()
    assert "No changes needed" in captured.out
```

---

## Warnings

### WR-01: `invalid_control_rejected` is never collected by pytest — missing `test_` prefix

**File:** `tests/test_models.py:87`
**Issue:** The method `def invalid_control_rejected(self):` inside `TestPedalModels` is missing the `test_` prefix. pytest never collects or runs it. The validation it is meant to assert (that an empty `name` is rejected by Pydantic) is not tested at all.

**Fix:**
```python
def test_invalid_control_rejected(self):
    with pytest.raises(ValidationError):
        Control(name="", type=ControlType.KNOB)
```

---

### WR-02: `ControllerConfig.scenes` typed as `dict[str, Any]` but semantically holds `dict[str, Scene]`

**File:** `src/rig/models/device.py:84`
**Issue:** `ControllerConfig.scenes: dict[str, Any] = {}` accepts and stores `Scene` objects correctly at construction time, but after a `model_dump()` / `Device(**dumped)` round-trip, the stored values degrade to plain `dict`s. Any code that calls `.presets` on those values after such a round-trip would get `AttributeError: 'dict' object has no attribute 'presets'`. Even without a round-trip, the `Any` type forces callers to add their own isinstance checks and suppresses static type errors.

**Fix:** Use the correct type and add a `model_validator` or `field_validator` to coerce dicts back to `Scene` objects:
```python
from rig.models.scene import Scene  # import here or in TYPE_CHECKING block

class ControllerConfig(DeviceConfig):
    type: Literal["controller"] = "controller"
    banks: list[dict[str, Any]] = []
    scenes: dict[str, Scene] = {}
```
Note: this requires resolving the import (currently `scene` is not imported in `device.py`). Alternatively, keep `dict[str, Any]` but document the degradation risk and add a round-trip test.

---

### WR-03: `diff.py` initializes `"pedals"` key that is never populated — dead code

**File:** `src/rig/engine/diff.py:19-21`
**Issue:** `compute_diff` returns `{"scenes": ..., "pedals": {}}`. The `"pedals"` key is initialized but no code populates it. No consumer in `src/` reads `diff["pedals"]`. This is dead code that creates a misleading API contract — callers may expect per-pedal diff data that does not exist.

**Fix:** Remove the unused key:
```python
changes: dict[str, Any] = {
    "scenes": {},
}
```
If per-device diff is planned, add a TODO comment and leave it out of the return value until implemented.

---

### WR-04: Empty `TYPE_CHECKING` block in `device.py` — unused import

**File:** `src/rig/models/device.py:10-11`
**Issue:** `TYPE_CHECKING` is imported from `typing` and used in an `if TYPE_CHECKING: pass` block that contains only `pass`. This is dead code: nothing is guarded under `TYPE_CHECKING`, making the import of `TYPE_CHECKING` itself unused.

**Fix:** Remove the dead block entirely:
```python
# Before:
from typing import TYPE_CHECKING, Annotated, Any, Literal
...
if TYPE_CHECKING:
    pass

# After:
from typing import Annotated, Any, Literal
```

---

### WR-05: `MidiConfig.get_cc_params` raises `ValueError` for non-numeric string parameter values

**File:** `src/rig/models/device.py:67`
**Issue:** `int(v)` is called on values from `preset.parameters` which is typed `dict[str, float | str | bool]`. If a parameter value is a non-numeric string (e.g., `"on"`, `"half"`) — a valid YAML value — `int()` raises an unhandled `ValueError`. This propagates out of `detect_cba_setup` in the plan engine with no user-facing message.

**Fix:** Guard the conversion and skip or log the invalid value:
```python
def get_cc_params(self, parameters: dict[str, Any]) -> list[dict[str, int]]:
    by_name = {c.name: c for c in self.controls if c.midi_cc is not None}
    result = []
    for k, v in parameters.items():
        if k not in by_name:
            continue
        try:
            result.append({"cc": by_name[k].midi_cc, "value": int(v)})
        except (TypeError, ValueError):
            logger.warning("Parameter '%s' value '%s' cannot be coerced to int; skipping", k, v)
    return result
```

---

_Reviewed: 2026-06-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
