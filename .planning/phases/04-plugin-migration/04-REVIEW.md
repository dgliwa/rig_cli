---
phase: 04-plugin-migration
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/rig/engine/plugin.py
  - src/rig/engine/plugin_registry.py
  - src/rig/engine/devices.py
  - src/rig/config/loader.py
  - src/rig/engine/apply.py
  - src/rig/models/rig.py
  - src/rig/engine/appliers/__init__.py
  - src/rig/engine/appliers/chase_bliss.py
  - tests/test_plugin.py
  - tests/test_devices.py
  - tests/test_loader.py
  - tests/test_apply.py
  - tests/test_appliers.py
findings:
  critical: 3
  warning: 4
  info: 1
  total: 8
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-05
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 4 migrated from direct applier dispatch to a plugin architecture where concrete
device types (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device`) implement a
`Device` Protocol and carry their own `apply()` logic. The structural shape is sound and
all 113 tests pass. However there are three blockers:

1. MC6 bank programming is dead on arrival — `MC6Device.apply()` reads from `self.banks`
   (always `[]` after loader construction) instead of `self.config.banks` (where the
   data actually lives). Every full `apply` run silently skips MC6 programming.
2. `MC6Device.apply()` hardcodes the string `"mc6"` throughout state writes, MIDI sends,
   and port lookups instead of using `ctx.action.device`. Any rig whose MC6 has a
   non-`"mc6"` device ID will silently mis-key state and fail MIDI sends.
3. The `pedal.config` null guard in `MC6Device.apply()` is incomplete; an
   `AttributeError` crash is possible.

`ChaseBlissDevice`'s delegation to a stub `_midi_device` instance is functional but
confusing; the delegation works only because all meaningful data flows through
`ctx.action`, not `self`. Several test coverage gaps leave the new code paths under-verified.

---

## Critical Issues

### CR-01: MC6 bank programming never executes — `self.banks` vs `self.config.banks`

**File:** `src/rig/engine/devices.py:301`

**Issue:** `MC6Device.apply()` guards on `if not self.banks` (line 301). The `banks`
field on `MC6Device` defaults to `[]` and is never populated by the loader. The
loader constructs `MC6Device` via `model_class(**{**data, "config": temp.config})`;
banks live inside the device's YAML `config` block and are therefore in
`self.config.banks` (a `ControllerConfig` field), not in the top-level `self.banks`.

`apply.py` (line 210) correctly reads `mc6_device.config.banks` to decide whether to
call `mc6_device.apply()` — it sees banks and proceeds — but then `MC6Device.apply()`
immediately returns `"skipped"` because `self.banks == []`. MC6 programming silently
does nothing on every real `apply` run.

**Fix:** Replace the `self.banks` guard with `self.config.banks`:

```python
# devices.py — MC6Device.apply()
banks = (
    self.config.banks
    if self.config is not None and hasattr(self.config, "banks")
    else []
)
if not banks or ctx.midi is None:
    return DeviceApplyResult(device=device_id, status="skipped")
# ... use `banks` instead of `self.banks` throughout the method body
```

The `banks: list[dict] = []` field on `MC6Device` can be removed, or left as an
override slot with a note that it is not populated by the loader.

---

### CR-02: `MC6Device.apply()` hardcodes `"mc6"` as device ID throughout

**File:** `src/rig/engine/devices.py:304,318,325,340,341,356`

**Issue:** State reads/writes, MIDI sends, and port-lookup calls all use the literal
string `"mc6"` instead of the actual device ID from `ctx.action.device` (captured as
`device_id` on line 299 but only used in the final `DeviceApplyResult`). Affected
calls:

- `ctx.state.devices.get("mc6", ...)` — reads cached port under wrong key
- `prompt_midi_connect("mc6", ...)` — opens MIDI port keyed as `"mc6"` in `MidiManager`
- `update_device_state(ctx.state, "mc6", ...)` — writes state under wrong key
- `ctx.midi.send_sysex("mc6", ...)` — looks up port under wrong key → `KeyError` or
  silent no-op

Any user whose YAML names the MC6 device anything other than `"mc6"` (e.g. `"mc6-mkii"`,
`"morningstar"`) will get wrong state keys and failed MIDI sends. `apply.py` line 232
(`state.devices.get("mc6")`) has the same hardcoding.

**Fix:**

```python
# devices.py — MC6Device.apply()
device_id = ctx.action.device  # already set on line 299

mc6_port = ctx.state.devices.get(device_id, DeviceState()).midi_port
res, port_name = prompt_midi_connect(device_id, 1, ctx.midi, mc6_port)
# ...
update_device_state(ctx.state, device_id, midi_port=port_name)
# ...
ctx.midi.send_sysex(device_id, msg)
```

```python
# apply.py line 232
if state.devices.get(mc6_device.id):
    state_modified = True
```

---

### CR-03: Incomplete null guard for `pedal.config` causes `AttributeError` crash

**File:** `src/rig/engine/devices.py:351`

**Issue:** The guard is:

```python
if pedal is None or pedal.config.midi_channel is None:
    continue
```

If `pedal` is not `None` but `pedal.config` is `None`, Python evaluates
`pedal.config.midi_channel` and raises `AttributeError: 'NoneType' object has no
attribute 'midi_channel'`. This is not a purely hypothetical case: the registry
singleton stubs (e.g. `AnalogDevice(id="__analog__", config=None)`) have `config=None`,
and any manually constructed device object passed into `rig.devices` will trigger this.

Verified:
```
>>> AnalogDevice(id="test", config=None).config.midi_channel
AttributeError: 'NoneType' object has no attribute 'midi_channel'
```

**Fix:**

```python
if pedal is None or pedal.config is None or pedal.config.midi_channel is None:
    continue
```

---

## Warnings

### WR-01: `Device` Protocol is not `@runtime_checkable`

**File:** `src/rig/engine/plugin.py:41`

**Issue:** `class Device(Protocol)` is not decorated with `@runtime_checkable`. Any
attempt to call `isinstance(x, Device)` at runtime raises `TypeError: Instance and
class checks can only be used with @runtime_checkable protocols`. This is a silent trap
for future callers; the Protocol's value comes largely from being usable in runtime
dispatch checks. The existing tests work around this via `hasattr` probing but cannot
express intent clearly.

**Fix:**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Device(Protocol):
    ...
```

---

### WR-02: `Rig.devices: dict[str, Any]` and `Rig.pedals` return type lie

**File:** `src/rig/models/rig.py:21,27`

**Issue:** `devices: dict[str, Any] = {}` erases all type information for the primary
data structure in `Rig`. The `pedals` property returns `dict[str, Device]` (the legacy
`models.device.Device`) but the dict actually contains `AnalogDevice`, `MidiDevice`,
etc. — plugin types that are structurally compatible but not nominally `Device`. Every
downstream call site loses type safety; type checkers will not catch attribute access
errors on devices.

The migration comment says "concrete Device plugin types... alongside the legacy Device
model during the P3 migration" — but both the legacy `Device` and the plugin types are
now present in the same `dict[str, Any]`. This is a regression: before the migration,
`devices` was typed.

**Fix:** Introduce a union type or a shared base, or mark the property correctly:

```python
from rig.engine.plugin import Device as DevicePlugin  # Protocol

devices: dict[str, Any] = {}  # TODO Phase 5: narrow to dict[str, DevicePlugin]

@property
def pedals(self) -> dict[str, Any]:  # honest until Phase 5 narrows the type
    return self.devices
```

At minimum, remove the false `dict[str, Device]` annotation on `pedals` so type
checkers do not give false confidence.

---

### WR-03: Scenes silently dropped when no `CONTROLLER` device is present

**File:** `src/rig/config/loader.py` (the `if scenes:` block near the end of `load_rig`)

**Issue:** If the rig YAML defines scene files but contains no device with
`type: controller`, the loader silently discards all loaded scenes. The wiring block is:

```python
if scenes:
    ctrl_device = next((...), None)
    if ctrl_device is not None and isinstance(ctrl_device.config, ControllerConfig):
        # scenes wired into controller config
```

When `ctrl_device is None`, no error is raised. `rig.scenes` returns `{}`, and
`_validate_references` skips all scene cross-reference checks. A user who forgets to
add an MC6 device gets no feedback that their scene files were ignored.

**Fix:** Raise an error when scenes exist but no controller is found:

```python
if scenes:
    ctrl_device = next(
        (d for d in devices.values() if d.type == DeviceType.CONTROLLER), None
    )
    if ctrl_device is None:
        raise ValidationError(
            f"Rig defines {len(scenes)} scene(s) but contains no CONTROLLER device. "
            "Add a controller device (e.g. MC6) to host scenes."
        )
    if isinstance(ctrl_device.config, ControllerConfig):
        ...
```

---

### WR-04: `MidiDevice.apply()` — `midi_connected` not cleared on PC send failure

**File:** `src/rig/engine/devices.py:156-172`

**Issue:** `midi_connected = action.device in ctx.connected_devices` is set before
`_try_send_pc()` is called. If `_try_send_pc()` raises and catches an exception
(returning `False`), `midi_connected` remains `True`. The `prompt_device` call on
line 175 then receives `midi_connected=True`, presenting the user with UI that implies
the MIDI send succeeded when it actually failed silently. The `retry` path re-calls
`_try_send_pc()` correctly, but the initial failure is invisible to the UX layer.

**Fix:** Use the return value of `_try_send_pc()` to gate `midi_connected`:

```python
_send_succeeded = _try_send_pc()
effective_midi_connected = midi_connected and _send_succeeded

while True:
    result = ctx.confirmation_io.prompt_device(
        action.device, action.preset_name, action.preset_number,
        action.midi_channel, effective_midi_connected,
    )
    if result == "retry":
        _send_succeeded = _try_send_pc()
        effective_midi_connected = midi_connected and _send_succeeded
        continue
    ...
```

---

## Info

### IN-01: `_update_device_state` is dead code in `apply.py`

**File:** `src/rig/engine/apply.py:45-47`

**Issue:** `_update_device_state` is a one-line wrapper around `update_device_state`
that is never called anywhere in the codebase. The module imports and uses
`update_device_state` directly (line 119). This wrapper adds noise and may mislead a
reader into thinking there are two distinct code paths.

**Fix:** Remove the wrapper:

```python
# Delete lines 45-47:
# def _update_device_state(state: RigState, device: str, **fields) -> None:
#     """Update a device's state fields in-place."""
#     update_device_state(state, device, **fields)
```

---

## Test Coverage Gaps (not individually classified but noted for completeness)

- `test_mc6_device_apply_dry_run_with_banks_returns_skipped` (line 316 in `test_devices.py`)
  sets `ctx.midi = None` which triggers the early-return guard (`not self.banks or midi is
  None`) before the dry-run branch is ever evaluated. The test name implies it covers the
  dry-run path but it actually covers the `midi=None` path. Consider adding a test that
  passes a non-`None` mock MIDI and `dry_run=True` with `banks` set in `self.config.banks`
  (after CR-01 is fixed).

- `ChaseBlissDevice.apply()` tests (lines 253-273 in `test_devices.py`) check only the
  return value; no test verifies that `update_device_state` is called with the correct
  device ID when the delegation path executes. Adding an assertion on `ctx.state.devices`
  after a `confirm` action would close this gap.

---

_Reviewed: 2026-06-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
