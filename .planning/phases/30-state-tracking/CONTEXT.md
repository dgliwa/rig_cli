# Phase 30: State Tracking Completeness — Context

## Phase Goal
`state.json` accurately reflects what preset is active on each device after every apply; `rig plan` diffs reflect actual device state rather than scene-level snapshots.

## Requirement
STATE-01: `state.json` tracks per-device `last_preset` accurately after every apply; `rig plan` uses this to suppress false-positive "changed" signals.

## Depends On
Phase 29 (complete ✓)

## Success Criteria
1. After `rig apply`, each device's `last_preset` in `state.json` matches the preset that was applied
2. `rig plan` reports "unchanged" for a device when `state.json` already records the desired preset — no false positives
3. Applying the same scene twice does not re-prompt for analog devices whose state already matches

## Root Cause Analysis

### Problem 1 — Plan display false positive (criterion 2)
In `engine/plan/compute.py`, analog devices always receive `ActionStatus.ANALOG` regardless of whether `actual_preset == preset_id`:

```python
if pedal.type == DeviceType.ANALOG:
    device_actions.append(DeviceAction(..., status=ActionStatus.ANALOG, ...))
    if actual_preset != preset_id:
        scene_has_changes = True
    continue
```

When a scene is "changed" (due to a MIDI device needing reconfiguration), the analog device action shows as `ActionStatus.ANALOG` in `plan.py` (yellow "⚠ set to X (manual)"), even though the device is already at the right preset. This is a display false positive.

### Problem 2 — Apply false positive (criterion 3)
In `engine/apply.py`, all device actions call `device.apply()` — including `ActionStatus.VERIFY` actions (devices already at their desired preset):

```python
for action in sp.device_actions:
    ...
    action_result = device.apply(device_ctx)
```

When a scene is "changed" because one device needs reconfiguring, other devices with `ActionStatus.VERIFY` still get prompted. Similarly, an analog device that is already at the right preset (its `last_preset` matches the desired preset) is still prompted.

Concrete example:
1. Apply scene "A" (analog "tumnus" + HX "clean") → both confirmed → state recorded
2. Apply scene "B" (HX "lead") → HX changes → state: tumnus="edge", hx="lead"
3. Apply scene "A" again:
   - tumnus: actual="edge" == desired="edge" → scene_has_changes NOT set
   - HX: actual="lead" ≠ desired="clean" → scene_has_changes = True → CONFIGURE
   - Scene "A" is "changed"
   - **tumnus.apply() is called and PROMPTS USER** — false positive

### What Already Works
- `DeviceState.last_preset` is set when devices are confirmed (all 4 plugins: analog, hx, chasebliss, morningstar)
- Scene-level "unchanged" correctly skips entire scenes when ALL devices match state
- `compute_plan()` correctly uses `last_preset` for CONFIGURE/VERIFY determination on non-analog devices
- `scene_has_changes` flag already skips analog-only check when preset matches

## Fix Design

### Fix 1 — compute.py: Assign VERIFY to analog when preset already matches

```python
if pedal.type == DeviceType.ANALOG:
    analog_status = ActionStatus.VERIFY if actual_preset == preset_id else ActionStatus.ANALOG
    device_actions.append(DeviceAction(..., status=analog_status, ...))
    if actual_preset != preset_id:
        scene_has_changes = True
    continue
```

### Fix 2 — apply.py: Auto-confirm VERIFY actions without prompting

```python
for action in sp.device_actions:
    device = rig.devices.get(action.device) if rig else None

    if action.status == ActionStatus.VERIFY:
        # Device already at desired preset per state.json — no user action needed
        device_results.append(DeviceApplyResult(
            device=action.device, status="confirmed", preset=action.preset_name
        ))
        continue

    if device is None:
        ...  # existing skip logic
    else:
        action_result = device.apply(device_ctx)
    ...
```

### Fix 3 — plan.py: Update display to handle analog VERIFY

```python
if action.device_type == DeviceType.ANALOG and action.status == ActionStatus.ANALOG:
    manual_count += 1
    console.print(f"    [yellow]⚠[/yellow] {action.device}: set to '{action.preset_name}' (manual)")
elif action.status == ActionStatus.VERIFY:
    already_set_count += 1
    console.print(f"    [green]✓[/green] {action.device}: '{action.preset_name}' (already set)")
elif action.status == ActionStatus.CONFIGURE:
    configure_count += 1
    ...
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/rig/src/rig/engine/plan/compute.py` | Assign VERIFY to analog when actual==desired |
| `packages/rig/src/rig/engine/apply.py` | Auto-confirm VERIFY actions; import ActionStatus |
| `packages/rig/src/rig/cli/commands/plan.py` | Update analog display for VERIFY case |

## Tests to Add

| File | Test |
|------|------|
| `packages/rig/tests/test_plan.py` | analog gets VERIFY when actual_preset matches |
| `packages/rig/tests/test_apply.py` | VERIFY actions auto-confirmed without calling device.apply() |
| `packages/rig/tests/test_apply.py` | integration: apply → apply again → no ConfirmationIO calls for analog |
| `packages/rig-analog/tests/test_analog_device.py` | Existing tests still pass (no apply() change in analog plugin) |
| `packages/rig/tests/test_cli_plan.py` | Analog "already set" shows ✓ marker (not ⚠) when state matches |

## Key Constraints
- Tech stack: Python 3.13, uv, Typer, Pydantic — no new deps
- No MIDI interaction in plan — plan is read-only
- Protocol-first: no ABC inheritance introduced
- Phase 29 must be complete (it is ✓)
- Do not implement APPLY-01 scope (Phase 33): skipping analog prompts when device is mixed in a changed scene goes beyond state tracking — that is Phase 33
  - Wait, actually criterion 3 requires this. The Fix 2 (VERIFY auto-confirm in apply.py) covers it.
  - Phase 33 adds APPLY-02 (--device flag) and ensures APPLY-01 is explicitly tested across more scenarios
