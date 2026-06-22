# Phase 30: State Tracking — Research

## Domain Analysis

### Current State Tracking Architecture

**`engine/state.py`** — `DeviceState.last_preset: str | None` tracks last applied preset per device. `RigState.scenes` tracks which scenes have been applied (as empty dict values).

**`engine/plan/compute.py`** — `compute_plan()` reads `state.json` via `read_state()`. For each device in each scene:
- Non-analog: `needs_config = actual_preset != preset_id` → CONFIGURE or VERIFY
- Analog: always `ActionStatus.ANALOG`, `scene_has_changes = True` only when preset changed

**`engine/apply.py`** — `apply_plan()` processes each scene:
- Skips "unchanged" scenes (all devices match + scene in state.scenes)
- For "new"/"changed" scenes: calls `device.apply(ctx)` for every device action
- After confirmed results: updates `state.scenes[name] = {}`

**`engine/plugin.py`** — `update_device_state()` and `mark_preset_saved()` are the sole mutation paths for state fields.

### Per-Plugin `last_preset` Tracking

| Plugin | last_preset set? | Where |
|--------|----------------|-------|
| `rig_analog.device.AnalogDevice.apply()` | ✓ when confirmed | `update_device_state(ctx.state, action.device, last_preset=action.preset_name)` |
| `rig_hx.device.HXStompDevice.apply()` | ✓ when confirmed | `update_device_state(ctx.state, action.device, last_preset=action.preset_name)` |
| `rig_chasebliss.device.ChaseBlissDevice.apply()` | ✓ when confirmed | `update_device_state(ctx.state, action.device, last_preset=action.preset_name)` |
| `rig_chasebliss.applier.py` | ✓ at registration phase | `update_device_state(ctx.state, action.device, last_preset=action.preset_name)` |
| `rig_morningstar` | N/A (controller) | MC6 has no preset concept |

**Conclusion**: `last_preset` tracking is correct for all plugins. No code gaps.

### Identified Bugs

#### Bug 1 — Analog plan display false positive
`compute.py` assigns `ActionStatus.ANALOG` to all analog device actions, even when `actual_preset == preset_id`. Result: plan.py shows a yellow "⚠ set to X (manual)" warning for an analog device that doesn't need to change.

#### Bug 2 — VERIFY actions prompt user in apply
`apply.py` calls `device.apply()` for all device actions in a "changed" scene — including `ActionStatus.VERIFY` actions. VERIFY means "device is already at desired preset per state.json." Users are prompted for devices that don't need reconfiguration.

**This produces the false-positive in criterion 3**: Apply scene "A" → apply scene "B" (changes some devices) → apply scene "A" again. In scene "A" re-apply, devices that are already at the right preset (VERIFY) are still prompted.

### Existing Test Coverage

- `test_plan.py::TestComputePlan::test_plan_unchanged_skip_when_preset_same` — verifies VERIFY status for non-analog
- No test for analog VERIFY status
- No test for VERIFY auto-confirm in apply
- `test_apply.py::TestApplyPlan::test_clean_plan_prints_no_changes` — scene-level unchanged is already tested
- No integration test that does apply → apply again and checks no re-prompts

### Fix Approach

**3 file changes + 2 test file additions**:

1. `compute.py`: `analog_status = ActionStatus.VERIFY if actual_preset == preset_id else ActionStatus.ANALOG`
2. `apply.py`: Before `device.apply()`, check `action.status == ActionStatus.VERIFY` → auto-confirm without calling apply()
3. `plan.py`: Update analog display condition to check both `device_type == ANALOG` AND `status == ANALOG` (not VERIFY)

## Test Strategy

**Unit tests** (fast, no MIDI):
- `test_plan.py`: `test_analog_verify_when_state_matches` — analog gets VERIFY when actual==desired
- `test_plan.py`: `test_analog_analog_when_state_different` — analog still gets ANALOG when different
- `test_apply.py`: `test_verify_action_auto_confirmed_without_prompt` — VERIFY action confirms without device.apply()
- `test_apply.py`: `test_verify_action_does_not_call_device_apply` — VERIFY action skips device.apply()

**Integration test** (apply → apply again):
- `test_apply.py::test_same_scene_applied_twice_no_reprompt_second_time` — apply scene twice; second apply triggers no ConfirmationIO calls

**CLI test**:
- `test_cli_plan.py`: analog with matching state shows ✓ marker not ⚠ marker

## Invariants to Preserve

- Scene "unchanged" (all devices match + scene in state.scenes) → entire scene skipped, no prompts ← must not break
- Analog with different preset → `ActionStatus.ANALOG`, user prompted ← must not break
- `scene_has_changes` only set when actual != desired ← unchanged
- `state_modified = True` when any confirmed result ← VERIFY auto-confirm must set this too
- `state.scenes[name] = {}` after any confirmed result ← VERIFY auto-confirm contributes to confirmed count
