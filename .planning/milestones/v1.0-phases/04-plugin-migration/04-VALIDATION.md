---
phase: 04-plugin-migration
validated: 2026-06-06
status: passed
score: 19/19
baseline_tests: 274
new_tests_added: 7
final_tests: 281
code_fixes: 1
---

# Phase 4 Validation Report

## State at Audit Start

State (B): No VALIDATION.md existed; SUMMARY.md files present for P1–P4 plus VERIFICATION.md (12/12) and REVIEW.md.

## Behavior Inventory

All phase behaviors sampled against Nyquist criterion (at least one test per distinct code path):

| # | Behavior | Source | Status |
|---|----------|--------|--------|
| 1 | Device Protocol structural compliance | test_plugin.py | COVERED |
| 2 | DeviceApplyContext has all 8 fields with correct defaults | test_plugin.py | COVERED |
| 3 | PluginRegistry.register_model/get_model independent from register/get | test_plugin.py | COVERED |
| 4 | AnalogDevice.apply() dry-run → skipped | test_devices.py | COVERED |
| 5 | AnalogDevice.apply() confirm → confirmed, state updated | test_devices.py | COVERED |
| 6 | AnalogDevice.apply() quit → error | test_devices.py | COVERED |
| 7 | **AnalogDevice.apply() skip → skipped** | test_devices.py | FILLED |
| 8 | MidiDevice.apply() dry-run → skipped | test_devices.py | COVERED |
| 9 | MidiDevice.apply() confirm → confirmed | test_devices.py | COVERED |
| 10 | **MidiDevice.apply() skip → skipped** | test_devices.py | FILLED |
| 11 | **MidiDevice.get_scene_pc_command() with matching digital preset** | test_devices.py | FILLED |
| 12 | **MidiDevice.get_scene_pc_command() no match → None** | test_devices.py | FILLED |
| 13 | ChaseBlissDevice.apply() dry-run → skipped | test_devices.py | COVERED |
| 14 | ChaseBlissDevice.apply() confirm → confirmed | test_devices.py | COVERED |
| 15 | **ChaseBlissDevice.get_scene_pc_command() with matching preset** | test_devices.py | FILLED |
| 16 | MC6Device.apply() no banks → noop | test_devices.py | COVERED |
| 17 | MC6Device.apply() dry-run with banks → skipped | test_devices.py | COVERED |
| 18 | MC6Device.apply() reads from config.banks (not removed banks field) | test_devices.py | COVERED |
| 19 | Loader dispatches all 4 config types to concrete plugin instances | test_loader.py | COVERED |
| 20 | Loader raises on unknown config type | test_loader.py | COVERED |
| 21 | apply.py routes through device.apply(DeviceApplyContext) | test_apply.py | COVERED |
| 22 | No get_scene_applier calls remain in apply.py | test_apply.py | COVERED |
| **23** | **_load_scenes with nonexistent dir returns {} (Python 3.13 compat)** | test_loader.py | FILLED |
| **24** | **get_registry() returns PluginRegistry with all 4 model classes** | test_devices.py | FILLED |

## Gaps Found and Filled

### GAP-1: AnalogDevice.apply() skip path untested
- **Behavior:** When `prompt_analog()` returns "skip", apply() returns `status="skipped"` without mutating state.
- **Fix:** `test_analog_device_apply_skip_returns_skipped` in `tests/test_devices.py`

### GAP-2: MidiDevice.apply() skip path untested
- **Behavior:** When `prompt_device()` returns "skip", apply() returns `status="skipped"`.
- **Fix:** `test_midi_device_apply_skip_returns_skipped` in `tests/test_devices.py`

### GAP-3: MidiDevice.get_scene_pc_command() not unit-tested on concrete type
- **Behavior:** Returns `{"type": "pc", "channel": N, "value": M}` for matching DigitalPreset; None for no match.
- **Fix:** `test_midi_device_get_scene_pc_command_with_digital_preset` and `test_midi_device_get_scene_pc_command_no_matching_preset_returns_none` in `tests/test_devices.py`
- **Note:** Previously only exercised via test_catalog.py loading fixtures with old Device model objects.

### GAP-4: ChaseBlissDevice.get_scene_pc_command() not unit-tested
- **Behavior:** Returns PC command using `self.config.midi_channel` and matching preset's `preset_number`.
- **Fix:** `test_chase_bliss_device_get_scene_pc_command_with_digital_preset` in `tests/test_devices.py`

### GAP-5: _load_scenes missing is_dir() guard (CR-02 from REVIEW.md)
- **Behavior:** On Python 3.13+, `Path.glob()` on a nonexistent path raises; on 3.12 it silently returns empty. The project declares `requires-python = ">=3.12"` so this is a forward-compatibility regression.
- **Code fix:** Added `if not scenes_dir.is_dir(): return {}` guard in `src/rig/config/loader.py:_load_scenes` (consistent with `_load_presets` pattern).
- **Test fix:** `test_load_scenes_nonexistent_dir_returns_empty` in `tests/test_loader.py` — calls `_load_scenes()` directly with a nonexistent path, asserts `{}` returned.

### GAP-6: get_registry() not directly tested
- **Behavior:** `get_registry()` from `plugin_registry.py` returns the default PluginRegistry with all 4 model classes registered.
- **Fix:** `test_get_registry_returns_registry_with_all_four_types` in `tests/test_devices.py`

## Code Changes

| File | Change |
|------|--------|
| `src/rig/config/loader.py` | Added `is_dir()` guard to `_load_scenes()` (CR-02 fix) |

## Test Changes

| File | Tests Added |
|------|-------------|
| `tests/test_devices.py` | +6 tests (gaps 1–4, 6) |
| `tests/test_loader.py` | +1 test (gap 5) |

## Outstanding Known Issues (not Nyquist gaps)

These items are documented in REVIEW.md but are NOT behavioral coverage gaps — they are code quality or type issues:

- **CR-01:** `ChaseBlissDevice._midi_device` is a class-level stub. Apply behavior is correct (uses `ctx.action` not stub's config), but the pattern is confusing. Tracked in REVIEW.md.
- **CR-03:** `DeviceApplyContext.rig` typed `Rig` but `apply_plan` passes `Rig | None`. Guard exists at call site. Type annotation should be `Rig | None`.
- **WR-01:** `mark_preset_saved` called with potentially-None `preset_id` in chase_bliss.py.
- **WR-02:** MC6 apply result discarded — partial state written on cancellation.
- **WR-03:** Scenes silently discarded when no CONTROLLER device present.
- **WR-04:** Device Protocol is not `@runtime_checkable`.
- **IN-01–03:** Dead wrapper, duplicate method, vestigial sentinel registrations.

These are correctness and clarity issues for a future phase, not Nyquist validation gaps.

## Verification

```
uv run pytest tests/ -q
281 passed in 0.46s
```

Baseline was 274. 7 new tests added, 0 regressions.
