---
phase: 26-isolated-preset-apply
plan: "01"
subsystem: engine/cli
tags: [apply, preset, isolated, cli, tdd]
dependency_graph:
  requires: []
  provides: [apply_device_preset, --device-flag, --preset-flag]
  affects: [packages/rig/src/rig/engine/apply.py, packages/rig/src/rig/cli/commands/apply.py]
tech_stack:
  added: []
  patterns: [TDD red-green, keyword-only function signature, Protocol-based routing]
key_files:
  created:
    - packages/rig/tests/test_apply_device_preset.py
    - packages/rig/tests/test_cli_apply.py
  modified:
    - packages/rig/src/rig/engine/apply.py
    - packages/rig/src/rig/cli/commands/apply.py
decisions:
  - "apply_device_preset() in engine alongside apply_plan() — same module, narrower scope"
  - "ConfirmedFakeDevice subclass calls update_device_state() to match real device behavior"
  - "Validation order: D-04 (scene conflict) → D-05 (partial flags) → D-06 (existence) — all before MidiManager()"
  - "Routing test patches rig.engine.apply.apply_device_preset to verify dispatch without CLI-module coupling"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-17"
  tasks_completed: 2
  files_changed: 4

requirements-completed: [PRESET-01, PRESET-02, PRESET-03]
---

# Phase 26 Plan 01: Isolated Preset Apply Summary

**One-liner:** `apply_device_preset()` engine function + `--device`/`--preset` CLI flags for isolated single-device preset apply without scene-based plan.

## What Was Built

### Task 1: Engine — `apply_device_preset()`

Added `apply_device_preset()` to `packages/rig/src/rig/engine/apply.py` alongside the existing `apply_plan()`. The new function:

- Accepts `device_id`, `preset_id` as positional args; remaining args are keyword-only (same style as `apply_plan()`)
- Raises `ValueError` if device ID or preset ID is not found in the rig model
- Calls `device.setup()` on the targeted device only (D-03); returns early if `setup_result.cancelled`
- Builds `DeviceAction` with `ActionStatus.CONFIGURE` — always apply, no short-circuit for "already applied"
- Resolves `preset_number` via `getattr(p, "preset_number", None)` and `midi_channel` via `getattr(device.config, ...)`
- Calls `device.apply()` with a `DeviceApplyContext`
- Writes state only if `result.status == "confirmed"` and not `dry_run` and `config_path` is set
- Never touches `state.scenes` (D-07)

### Task 2: CLI — `--device` and `--preset` flags

Extended `packages/rig/src/rig/cli/commands/apply.py` with:

- Two new Typer options: `--device` and `--preset` (both `str | None`, default `None`)
- Validation block (after `load_rig()`, before `MidiManager()`):
  1. D-04: `--scene` + `--device`/`--preset` conflict → exit 1
  2. D-05: one flag without the other → exit 1
  3. D-06: device not in `rig.devices` → exit 1; preset not on device → exit 1
- Routing: `if device and preset: apply_device_preset(...)` else `compute_plan + apply_plan`
- `MidiManager` construction, state_writer, and routing all inside `try/finally: midi.disconnect_all()`

### Tests

- `packages/rig/tests/test_apply_device_preset.py` — 7 unit tests covering PRESET-01 through PRESET-03, D-07, dry_run, setup cancellation, and preset_number resolution
- `packages/rig/tests/test_cli_apply.py` — 7 CLI tests covering D-04, D-05, D-06 error paths and routing

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f4c2bdd | test | Failing unit tests for apply_device_preset (RED) |
| 25d4abc | feat | apply_device_preset engine function (GREEN) |
| a514b97 | test | Failing CLI tests for --device/--preset (RED) |
| 6cd2da1 | feat | --device/--preset CLI flags with validation and routing (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ConfirmedFakeDevice missing update_device_state call**
- **Found during:** Task 1 GREEN phase
- **Issue:** `ConfirmedFakeDevice.apply()` returned `"confirmed"` but didn't call `update_device_state()`, so `state.devices[device_id].last_preset` was never set. Real device plugins (analog, hx) always call `update_device_state` inside `apply()`. Test assertion `state.devices["klon"].last_preset == "clean"` failed.
- **Fix:** Added `update_device_state(ctx.state, self.id, last_preset=ctx.action.preset_name)` to `ConfirmedFakeDevice.apply()` to simulate real plugin behavior.
- **Files modified:** `packages/rig/tests/test_apply_device_preset.py`
- **Commit:** 25d4abc

**2. [Rule 1 - Bug] dry_run test assertion incorrect**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test asserted `"klon" not in state_adapter.state.devices` in dry_run mode. But `update_device_state` mutates `ctx.state` in-memory regardless of `dry_run` — `dry_run` only suppresses the `state_writer.write()` call. The in-memory mutation is correct behavior; only disk persistence is suppressed.
- **Fix:** Removed the second assertion; kept `state_adapter.state is initial_state` which correctly tests that `write()` was not called (since `InMemoryStateAdapter.write()` replaces `self._state` with a new object).
- **Files modified:** `packages/rig/tests/test_apply_device_preset.py`
- **Commit:** 25d4abc

**3. [Rule 3 - Blocking] typer.CliRunner does not accept mix_stderr kwarg**
- **Found during:** Task 2 RED phase
- **Issue:** `CliRunner(mix_stderr=False)` raised `TypeError` — that arg is not supported in this version of typer.
- **Fix:** Changed to `CliRunner()` (default).
- **Files modified:** `packages/rig/tests/test_cli_apply.py`
- **Commit:** a514b97

**4. [Rule 1 - Bug] AnalogPreset requires values field in test fixture**
- **Found during:** Task 2 routing test
- **Issue:** Test fixture YAML had preset without `values: {}` — `AnalogPreset.values` is a required field causing `load_rig()` to raise `ValidationError`.
- **Fix:** Added `values: {}` to the preset in `_write_minimal_rig()`.
- **Files modified:** `packages/rig/tests/test_cli_apply.py`
- **Commit:** a514b97

**5. [Rule 1 - Bug] Routing test patched wrong module path**
- **Found during:** Task 2 routing test analysis
- **Issue:** Test for `test_device_preset_flags_route_to_apply_device_preset` patched `rig.engine.apply.apply_device_preset` (where the function lives) but CLI imports it via `from rig.engine.apply import apply_device_preset` inside the `if` block. The patch was applied at the correct location.
- **Fix:** No change needed; `from rig.engine.apply import apply_device_preset` inside the branch means patching `rig.engine.apply.apply_device_preset` is the right target. Test passed as-is.

## Known Stubs

None — all functionality is fully implemented and wired.

## Threat Flags

None — all surfaces in the threat model were mitigated per T-26-01 and T-26-03:
- Device/preset IDs validated against loaded `Rig` model before `MidiManager()` constructed
- `state.scenes` never modified by `apply_device_preset()`

## Self-Check: PASSED

- [x] `test_apply_device_preset.py` exists and has 7 passing tests
- [x] `test_cli_apply.py` exists and has 7 passing tests
- [x] `apply_device_preset` function defined in `packages/rig/src/rig/engine/apply.py`
- [x] `--device` and `--preset` options in `packages/rig/src/rig/cli/commands/apply.py`
- [x] All 4 commits (f4c2bdd, 25d4abc, a514b97, 6cd2da1) exist in git log
- [x] Full test suite: 257 passed, 0 failed
