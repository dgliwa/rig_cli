---
phase: 5
plan: P3
type: implementation
wave: 2
depends_on: [P1, P2]
files_modified:
  - src/rig/engine/plan/compute.py
  - tests/test_plan.py
requirements: [PLAN-01, PLAN-02, D-04, D-05, D-06, D-10]
must_haves:
  - DeviceAction.before and .after are populated on every action produced by compute_plan()
  - device_actions within each ScenePlan sorted by DeviceGraph.apply_order() (D-07)
  - Plan.missing_refs contains a human-readable entry for every broken scene→device or scene→preset reference
  - Plan.unused_presets contains a human-readable entry for every DigitalPreset or HXStompPreset never referenced in any scene
  - AnalogPresets are excluded from unused_presets detection
  - The TODO comment on detect_cba_setup call in compute.py is removed
  - compute_diff() in diff.py marks a scene as "unchanged" when no preset assignments drifted (fixes always-"changed" bug at line 35)
  - All new tests in test_plan.py pass
---

# Phase 5 P3: compute_plan() Extensions

## Context

With the model fields in place (P2) and DeviceGraph available (P1), this plan wires the logic:
populate `before`/`after` on every `DeviceAction`, detect missing scene→preset references, detect
unused presets, and clean up the TODO comment that noted CBA setup detection doesn't belong in
apply (D-10 resolves this by making the plan authoritative — compute.py already owns it, so the
TODO is simply misleading and must be removed).

The current `compute_plan()` in `src/rig/engine/plan/compute.py` is being extended, not replaced.
Read lines 84-192 carefully before editing. The existing scene-iteration loop and CBA detection
call must be preserved intact except for the additions described below.

---

## Task P5-T6: Extend compute_plan() in compute.py

**File:** `src/rig/engine/plan/compute.py`

**Changes:**

**Import additions:** Add `from rig.models.graph import DeviceGraph` at the top with the other
imports. Add `AnalogPreset` to the existing `from rig.models.preset import ...` line (it is
needed to exclude AnalogPresets from unused detection).

**before/after population:** Inside the per-device loop (around line 107), after reading
`actual_preset = actual.devices.get(pedal_id, DeviceState()).last_preset`, store it. When
constructing each `DeviceAction`, pass `before=actual_preset, after=preset_id`. This applies to
both the analog branch (lines 113-124) and the configure/verify branch (lines 146-155). The
`before` value is `actual_preset` which will be `None` when no prior state exists for that device
(since `DeviceState().last_preset` is `None` by default — confirm this against `state.py`).
The `after` value is always `preset_id` (the desired state from the scene config).

**Missing ref detection:** Add a private function `_detect_missing_refs(rig: Rig) -> list[str]`
above `compute_plan()`. Implementation:
- Collect all `(scene_name, device_id, preset_id)` triples from `rig.scenes.items()` iterating
  `scene.presets.items()`.
- For each triple: if `device_id` not in `rig.devices`, append
  `f"scene '{scene_name}' → device '{device_id}' not found"`.
- Else if no preset with `id == preset_id` exists in `rig.devices[device_id].presets`, append
  `f"scene '{scene_name}' → device '{device_id}' preset '{preset_id}' not found"`.
- Return the list sorted for stable output.

**Unused preset detection:** Add a private function `_detect_unused_presets(rig: Rig) -> list[str]`
above `compute_plan()`. Implementation:
- Build `referenced: set[str]` — all preset IDs referenced across all scenes:
  `{pid for scene in rig.scenes.values() for pid in scene.presets.values()}`.
- For each device in `rig.devices.values()`, for each preset in `device.presets`:
  - Skip if `isinstance(preset, AnalogPreset)` — AnalogPresets document knob positions, not
    scene-activated (D-05).
  - If `preset.id` not in `referenced`, append `f"{device.id}: '{preset.id}' unused"`.
- Return the list sorted for stable output.

**Wire both functions into compute_plan():** After the existing scene loop and before the CBA
detection call, add:

```python
missing_refs = _detect_missing_refs(rig)
unused_presets = _detect_unused_presets(rig)
```

Update the `return Plan(...)` at the bottom (line 188) to pass the two new fields:

```python
return Plan(
    status=plan_status,
    scenes=scenes_plan,
    cba_setup=cba_setup,
    missing_refs=missing_refs,
    unused_presets=unused_presets,
)
```

**Remove TODO comment:** Line 174 has `# TODO: This shouldn't be here` above the
`cba_setup = detect_cba_setup(rig, actual)` call. Delete that comment line. The CBA setup
detection belongs in `compute_plan()` — per D-10, the plan is authoritative, and the comment was
only tracking uncertainty that is now resolved. Also remove the second TODO on line 177
(`# TODO: let's revisit this - we should detect changes here`) — the behavior is correct: CBA
setup actions do indicate changes. Leave the `logger.debug` call on line 179 intact.

Do not add `"no_change"` status to `DeviceAction` in the compute logic. The existing `"verify"`
status already means "already set, no action needed". The `--show-unchanged` flag in P4 controls
display of scenes with `ScenePlan.status == "unchanged"` — it operates at the scene level, not
the device-action level.

**Device ordering within scenes (D-07):** After building `device_actions` for each scene, sort
the list by the device's position in `DeviceGraph(rig).apply_order()`. Compute the order once
before the scene loop:

```python
graph = DeviceGraph(rig)
ordered_devices = [d.id for d in graph.apply_order()]

def _action_sort_key(action: DeviceAction) -> int:
    try:
        return ordered_devices.index(action.device)
    except ValueError:
        return len(ordered_devices)
```

After `device_actions` is built for each scene, call:
`device_actions.sort(key=_action_sort_key)`

This ensures devices appear in signal-chain order (controller last) within each scene's action
list, satisfying D-07.

---

## Task P5-T7: Add tests to tests/test_plan.py

**File:** `tests/test_plan.py`

**Changes:**

Add three new test classes after the existing `TestCbaDetection` class. Reuse the existing
`_make_rig()` builder and add a second builder `_make_rig_with_extra_preset()` that includes an
extra `DigitalPreset` on the `brothers` device that is NOT referenced in any scene — use this for
unused preset tests.

**class TestMissingRefs:**

- `test_missing_device_in_scene`: create a rig where a scene references a device ID that does not
  exist in `rig.devices`; call `compute_plan(rig)`; assert `"not found"` appears in at least one
  entry of `plan.missing_refs` for that device. Do this by passing `scene_presets={"ghost-device":
  "some-preset"}` to `_make_rig()`.
- `test_missing_preset_on_existing_device`: create a scene that references `hx-stomp` with a
  preset ID that does not exist on the hx-stomp device (e.g., `"nonexistent-preset"`); assert
  `plan.missing_refs` contains an entry mentioning `"hx-stomp"` and `"nonexistent-preset"`.
- `test_valid_refs_produce_empty_missing_refs`: use the default `_make_rig()` (all refs valid);
  assert `plan.missing_refs == []`.

**class TestUnusedPresets:**

- `test_unused_digital_preset_detected`: build a rig where brothers has two DigitalPresets but
  the scene only references one of them; assert `plan.unused_presets` contains the unreferenced
  one formatted as `"brothers: '{preset_id}' unused"`.
- `test_unused_hx_preset_detected`: add a second `HXStompPreset` to hx-stomp that is not in any
  scene; assert it appears in `plan.unused_presets`.
- `test_analog_presets_excluded_from_unused`: add an `AnalogPreset` to the tumnus device that is
  not referenced in any scene; assert `plan.unused_presets` does NOT contain any entry for tumnus.
- `test_all_referenced_produces_empty_unused_presets`: default `_make_rig()` where all defined
  digital/HX presets are in the scene; assert `plan.unused_presets == []`.

**class TestBeforeAfterFields:**

- `test_before_none_when_no_prior_state`: default `_make_rig()` with no state file; call
  `compute_plan(rig)` (no root_path); find the hx-stomp `DeviceAction`; assert `action.before is
  None` and `action.after == "clean-edge"`.
- `test_before_populated_from_state`: write a state file with hx-stomp `last_preset = "old-patch"`;
  call `compute_plan(rig, root_path=str(tmp_path))`; assert hx-stomp action `before == "old-patch"`
  and `after == "clean-edge"`. Requires `tmp_path` fixture.
- `test_analog_action_has_before_after`: use `_make_rig({"tumnus": "edge-of-breakup"})`; assert
  the tumnus `DeviceAction` has `after == "edge-of-breakup"` and `before is None` (no state).

**class TestComputeDiff (PLAN-01 regression):**

- `test_diff_unchanged_when_state_matches`: write state with hx-stomp `last_preset = "clean-edge"`
  and scene "test-scene" applied; call `compute_diff(rig, root_path=str(tmp_path))`; assert
  `changes["scenes"]` is empty (no changes). This fails before the fix (diff.py:35 bug).
- `test_diff_changed_when_preset_differs`: write state with hx-stomp `last_preset = "old-patch"`;
  call `compute_diff(rig, root_path=str(tmp_path))`; assert "test-scene" is in `changes["scenes"]`
  with status "changed".

### Task P5-T7b: Fix always-"changed" bug in compute_diff() (PLAN-01)

**File:** `src/rig/engine/diff.py`

**Location:** Line ~35 (the `else` branch of the `if scene_name not in actual.scenes:` check)

**Current code:**
```python
else:
    scene_diffs["_status"] = "changed"
    scene_diffs["presets"] = {}
    for pedal_id, preset_id in scene.presets.items():
        actual_preset = actual_devices.get(pedal_id, DeviceState()).last_preset
        if actual_preset != preset_id:
            scene_diffs["presets"][pedal_id] = {
                "_status": "changed",
                "old": actual_preset,
                "new": preset_id,
            }
```

**Fix:** Move the `_status` assignment after the presets loop so it reflects actual drift:
```python
else:
    scene_diffs["presets"] = {}
    for pedal_id, preset_id in scene.presets.items():
        actual_preset = actual_devices.get(pedal_id, DeviceState()).last_preset
        if actual_preset != preset_id:
            scene_diffs["presets"][pedal_id] = {
                "_status": "changed",
                "old": actual_preset,
                "new": preset_id,
            }
    scene_diffs["_status"] = "unchanged" if not scene_diffs["presets"] else "changed"
```

The existing gate `if scene_diffs.get("presets") or scene_diffs.get("_status") == "new":` already
suppresses unchanged scenes from appearing in `changes["scenes"]` — but setting the status
correctly also makes `format_diff` render it correctly if the entry ever does appear.

### Verification

```
uv run pytest tests/test_plan.py -v
```

All tests (existing + new) must pass. Zero failures.
