---
phase: 04-plugin-migration
reviewed: 2026-06-06T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/rig/config/loader.py
  - src/rig/engine/appliers/__init__.py
  - src/rig/engine/appliers/chase_bliss.py
  - src/rig/engine/apply.py
  - src/rig/engine/devices.py
  - src/rig/engine/plugin.py
  - src/rig/engine/plugin_registry.py
  - src/rig/models/rig.py
  - tests/test_appliers.py
  - tests/test_apply.py
  - tests/test_devices.py
  - tests/test_loader.py
  - tests/test_plugin.py
findings:
  critical: 3
  warning: 4
  info: 3
  total: 10
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The phase-4 plugin migration is structurally sound: registry-driven device dispatch works,
all four concrete device types are registered and reachable from the loader, and tests
demonstrate the routing path. Three critical behavioral defects were found that cause silent
incorrect behavior at runtime.

The most serious: `ChaseBlissDevice.apply()` always delegates to a blank `MidiDevice`
stub instance (Pydantic private field semantics), meaning CBA scene-level PC sends are
always dropped. A second critical defect is a Python 3.12-vs-3.13 time-bomb in the loader
where `_load_scenes` calls `glob()` on a potentially nonexistent directory without a guard.
A type-contract violation in `DeviceApplyContext.rig` rounds out the blockers.

---

## Critical Issues

### CR-01: `ChaseBlissDevice.apply()` delegates to a blank stub — CC sends silently dropped

**File:** `src/rig/engine/devices.py:228,256`

**Issue:** `ChaseBlissDevice` delegates `apply()` to `self._midi_device`, which is
declared as a Pydantic class-level private variable initialized with `config=None` and
`presets=[]`. Because Pydantic treats leading-underscore fields as private class variables
(not instance fields), every `ChaseBlissDevice` instance holds a distinct stub `MidiDevice`
with `config=None` and no presets — not a copy of the wrapper's actual config or preset list.

Verified empirically:
```
d = ChaseBlissDevice(id='cba', config=ChaseBlissConfig(midi_channel=3), presets=[...])
d._midi_device.config   # None  (NOT ChaseBlissConfig(midi_channel=3))
d._midi_device.id       # ""    (NOT "cba")
```

When `MidiDevice.apply()` executes via this stub, `_try_send_pc()` always short-circuits
(`action.midi_channel` may be set on the action, so PC sends actually work through
`ctx.action` — but `get_scene_pc_command()` will always return `None` because the stub
has no presets, breaking any caller that uses it for PC command generation). The state
update path writes to `action.device` correctly because it reads from `ctx.action`, not
from `self`, so apply state writes are fine. The broken surface is: `get_scene_pc_command`
on the stub returns `None` for every preset lookup, meaning MC6 bank programming misses
CBA PC commands.

**Fix:** Remove the private delegation field. Inline the MidiDevice logic or construct a
properly-populated delegate at call time:

```python
def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
    # Delegate to MidiDevice apply logic with this device's actual config/presets.
    delegate = MidiDevice(id=self.id, name=self.name, config=self.config, presets=self.presets)
    return delegate.apply(ctx)
```

---

### CR-02: `_load_scenes` crashes on Python 3.13 — missing `is_dir()` guard

**File:** `src/rig/config/loader.py:121`

**Issue:** `_load_scenes` calls `scenes_dir.glob("*.yaml")` with no existence check.
In Python 3.12, `Path.glob()` on a nonexistent path silently returns an empty iterator.
In Python 3.13+ the behavior changed: `glob()` on a nonexistent directory raises
`FileNotFoundError` / `OSError`. The project declares `requires-python = ">=3.12"`, so
this is a forward-compatibility regression.

The loader already applies the correct guard pattern for `devices_dir` (line 200) and
`preset_dir` (line 93). `_load_scenes` simply lacks the check.

The existing test `test_scenes_dir_missing` passes today because of the 3.12 silent
behavior, masking the regression.

**Fix:** Add a guard at the top of `_load_scenes`, consistent with the rest of the loader:

```python
def _load_scenes(scenes_dir: Path) -> dict[str, Scene]:
    scenes: dict[str, Scene] = {}
    if not scenes_dir.is_dir():
        logger.debug("Scenes directory not found: %s", scenes_dir)
        return scenes
    logger.debug("Loading scenes from: %s", scenes_dir)
    for path in sorted(scenes_dir.glob("*.yaml")):
        ...
```

---

### CR-03: `DeviceApplyContext.rig` is typed `Rig` (non-optional) but receives `Rig | None`

**File:** `src/rig/engine/apply.py:170-173`, `src/rig/engine/plugin.py:33`

**Issue:** `apply_plan` has `rig: Rig | None = None`. The guard at line 160
(`device = rig.devices.get(...) if rig else None`) prevents the `else` branch from
executing when `rig is None`, so no immediate crash occurs on the current happy path.
However, `DeviceApplyContext` is constructed at line 170 with `rig=rig` where `rig` is
`Rig | None`, but `DeviceApplyContext.rig` is annotated `rig: Rig` (no `| None`). Static
type checkers will flag every call site. More critically: any applier that accesses
`ctx.rig` without a None guard will raise `AttributeError` at runtime if `apply_plan` is
ever called without a `rig` argument and the guard logic changes.

**Fix:** Either make the field optional to match real usage:

```python
# plugin.py
@dataclass
class DeviceApplyContext:
    action: DeviceAction
    state: RigState
    rig: Rig | None        # was: rig: Rig
    ...
```

Or enforce that `rig` is always required for non-dry-run apply paths and assert before
the loop.

---

## Warnings

### WR-01: `mark_preset_saved` called with potentially-`None` `preset_id`

**File:** `src/rig/engine/appliers/chase_bliss.py:207`

**Issue:** `CbaSetupAction.preset_id` is typed `str | None` (default `None`). The
`_build_preset` handler calls `mark_preset_saved(ctx.state, action.device, action.preset_id)`
unconditionally. `mark_preset_saved` accepts `preset_id: str`. If `preset_id` is `None`,
`updated[None] = True` is stored in the `presets_saved` dict — a `None` key where only
string keys are expected. This corrupts the state dictionary used downstream to determine
which presets are already saved.

In practice `build_preset` actions always have `preset_id` set, but the type system does
not enforce this and a future code path could trigger the corruption.

**Fix:**
```python
if res == "confirm":
    update_device_state(ctx.state, action.device, last_preset=action.preset_name)
    if action.preset_id is not None:
        mark_preset_saved(ctx.state, action.device, action.preset_id)
```

---

### WR-02: MC6 `apply()` result is discarded — `state_modified` check is unreliable

**File:** `src/rig/engine/apply.py:231-233`

**Issue:** The MC6 phase calls `mc6_device.apply(mc6_ctx)` and discards the
`DeviceApplyResult`. `state_modified` is set only if `state.devices.get("mc6")` is
truthy (line 232). Because `MC6Device.apply()` calls `update_device_state(..., "mc6",
midi_port=...)` at line 324 of `devices.py` before returning, `state.devices["mc6"]` is
populated even when the apply ends with `status="error"` (user quit). The result is that
a user who quits during MC6 programming still triggers a state save — partial state is
written on cancellation.

**Fix:** Use the return value:
```python
mc6_result = mc6_device.apply(mc6_ctx)
if mc6_result.status == "confirmed":
    state_modified = True
```

---

### WR-03: Scenes silently discarded when no `CONTROLLER` device is present

**File:** `src/rig/config/loader.py` (`load_rig`, scenes wiring block)

**Issue:** When the rig YAML defines scene files but no device has `type: controller`,
the loader silently drops all scenes. The wiring block guards `if ctrl_device is not None`
but raises no error. `rig.scenes` returns `{}`, `_validate_references` skips all
scene cross-reference checks, and the user receives no feedback that their scene files
were ignored.

**Fix:** Raise on the condition rather than silently discarding:
```python
if scenes:
    ctrl_device = next(
        (d for d in devices.values() if d.type == DeviceType.CONTROLLER), None
    )
    if ctrl_device is None:
        raise ValidationError(
            f"Rig defines {len(scenes)} scene(s) but no CONTROLLER device exists. "
            "Add a controller device (e.g. MC6) to host scenes."
        )
    if isinstance(ctrl_device.config, ControllerConfig):
        ...
```

---

### WR-04: `Device` Protocol is not `@runtime_checkable`

**File:** `src/rig/engine/plugin.py:41`

**Issue:** `class Device(Protocol)` is not decorated with `@runtime_checkable`. Any
`isinstance(x, Device)` call at runtime raises `TypeError: Instance and class checks can
only be used with @runtime_checkable protocols`. Existing tests work around this via
`hasattr` probing, but callers that reach for `isinstance` in application code (e.g. when
the apply engine needs to branch on device type) will hit a runtime crash.

**Fix:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Device(Protocol):
    ...
```

---

## Info

### IN-01: Dead wrapper `_update_device_state` in `apply.py`

**File:** `src/rig/engine/apply.py:45-47`

**Issue:** `_update_device_state` is a one-line wrapper around `update_device_state`
(imported directly at line 13) that is never called anywhere in the module. All internal
call sites use `update_device_state` directly. The wrapper adds noise and may mislead
a reader into thinking two distinct paths exist.

**Fix:** Remove lines 45-47.

---

### IN-02: `ChaseBlissDevice.get_scene_pc_command` duplicates `MidiDevice.get_scene_pc_command` verbatim

**File:** `src/rig/engine/devices.py:236-253`

**Issue:** The two methods are byte-for-byte identical (both check `self.config.midi_channel`
and iterate `self.presets`). The delegation story for `apply()` says "CBA scene switching
is just a PC message", but the same rationale applies to `get_scene_pc_command`. The
duplication signals an incomplete refactor and will diverge if either method is updated.

**Fix:** After CR-01 is addressed, if `ChaseBlissDevice` properly delegates to
`MidiDevice`, `get_scene_pc_command` can be removed from `ChaseBlissDevice` and the
base delegation will cover it automatically.

---

### IN-03: Singleton plugin instances registered in `default_registry` are vestigial

**File:** `src/rig/engine/devices.py:382-387`

**Issue:** Four sentinel instances are registered via `default_registry.register(...)` with
placeholder `id` values (`"__analog__"`, `"__midi__"`, etc.). The live dispatch path
uses `registry.get_model(config_type)` to construct per-device instances from YAML data;
`registry.get(config_type)` returning these singletons is not called anywhere in the
codebase. The singletons are potentially misleading (a future caller might use `get()` and
accidentally mutate the shared registry instance).

**Fix:** Either remove the `register()` calls (keeping only `register_model()`) or add a
comment explaining what use case `get()` is reserved for.

---

_Reviewed: 2026-06-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
