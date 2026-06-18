---
phase: 26-isolated-preset-apply
verified: 2026-06-17
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 26: Isolated Preset Apply — Verification Report

**Phase Goal:** Add `apply_device_preset()` to the engine and wire `--device`/`--preset` flags
into the CLI, enabling `rig apply --device <id> --preset <id>` to apply exactly one device's
preset without a scene-based plan. All other devices skipped. Only that device's state.json
entry updated; state.scenes untouched.
**Verified:** 2026-06-17
**Status:** passed
**Re-verification:** No — initial verification (retroactive)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `rig apply --device <id> --preset <id>` applies only that device; all others are skipped | ✓ VERIFIED | `test_applies_only_targeted_device` PASSES — builds Rig with two FakeDevices, calls `apply_device_preset` for device 1, asserts device 2 state unchanged |
| 2 | After targeted apply, `state.devices[device_id].last_preset` equals the applied preset; other device state entries unchanged | ✓ VERIFIED | `test_state_updated_for_targeted_device` PASSES — `ConfirmedFakeDevice.apply()` calls `update_device_state()`, assertion on `last_preset` |
| 3 | `state.scenes` is not modified by `apply_device_preset()` | ✓ VERIFIED | `test_state_scenes_not_touched` PASSES — pre-populates `state.scenes` with `{"test-scene": {}}`, verifies unchanged after apply; grep confirms no `state.scenes` write in `apply_device_preset()` |
| 4 | Unknown device ID or preset ID produces a red error and exits with code 1 before any MIDI port is opened | ✓ VERIFIED | `test_unknown_device_exits_1` and `test_unknown_preset_exits_1` PASS; validation gates run before `MidiManager()` construction in CLI |
| 5 | `rig apply` without `--device`/`--preset` behaves exactly as before (no regression) | ✓ VERIFIED | `test_no_flags_uses_existing_apply_plan_path` PASSES — patches `compute_plan` and `apply_plan`, asserts they are called; full suite 367 passing confirms no regression |
| 6 | `--device` without `--preset` (or vice versa) produces a clear error and exits 1 | ✓ VERIFIED | `test_device_without_preset_exits_1` and `test_preset_without_device_exits_1` PASS; error message contains "--device and --preset must be used together" |
| 7 | `--scene` combined with `--device`/`--preset` produces a clear error and exits 1 | ✓ VERIFIED | `test_scene_and_device_conflict_exits_1` PASSES; error message contains "--scene cannot be combined with --device/--preset" |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/rig/src/rig/engine/apply.py` | `apply_device_preset()` function — isolated single-device apply | ✓ VERIFIED | Function exists at line ~195; calls `device.setup()` then `device.apply()`, writes state on confirmed |
| `packages/rig/src/rig/cli/commands/apply.py` | `rig apply` command with `--device` and `--preset` Typer options | ✓ VERIFIED | Both options present; validation block (D-04 → D-05 → D-06) before MIDI construction |
| `packages/rig/tests/test_apply_device_preset.py` | Unit tests for PRESET-01/02/03, D-07, dry_run, skipped, setup cancelled | ✓ VERIFIED | 7 tests, all passing |
| `packages/rig/tests/test_cli_apply.py` | CLI integration tests for D-04, D-05, D-06, routing | ✓ VERIFIED | 7 tests, all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `packages/rig/src/rig/cli/commands/apply.py` | `packages/rig/src/rig/engine/apply.py` | `apply_device_preset()` import and call when `--device` and `--preset` both set | ✓ WIRED | `from rig.engine.apply import apply_device_preset` inside `if device and preset:` block |
| `packages/rig/src/rig/engine/apply.py` | `rig.engine.plugin` | `DeviceApplyContext` / `SetupContext` construction, `device.setup()` then `device.apply()` | ✓ WIRED | `SetupContext` built with state/rig/dry_run/confirmation_io/midi; `DeviceApplyContext` with full action |
| `packages/rig/src/rig/engine/apply.py` | `rig.engine.plan.models.DeviceAction` | `DeviceAction(device=device_id, status=ActionStatus.CONFIGURE, ...)` | ✓ WIRED | Imports from `rig.engine.plan.models`; always uses `CONFIGURE` status |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 14 phase tests pass | `uv run pytest packages/rig/tests/test_apply_device_preset.py packages/rig/tests/test_cli_apply.py -v` | 14 passed in 0.11s | ✓ PASS |
| Full suite passes (no regression) | `uv run pytest packages/ -q` | 367 passed in 0.59s | ✓ PASS |
| No state.scenes write in apply_device_preset | `grep -n "state\.scenes" packages/rig/src/rig/engine/apply.py` | Only line 145 in `apply_plan()` path, not in `apply_device_preset()` | ✓ PASS |
| THREAT T-26-01 mitigated | Unknown device/preset validated before MidiManager() | Pre-MIDI validation in CLI apply.py | ✓ MITIGATED |
| THREAT T-26-03 mitigated | All validation runs before MidiManager() construction | MidiManager created after validation block | ✓ MITIGATED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PRESET-01 | 26-01-PLAN | `rig apply --device <id> --preset <id>` applies one preset without full scene setup | ✓ SATISFIED | `apply_device_preset()` called from CLI with both flags; `test_applies_only_targeted_device` confirms isolation; `test_device_preset_flags_route_to_apply_device_preset` confirms routing |
| PRESET-02 | 26-01-PLAN | `--device`/`--preset` flags skip all other devices | ✓ SATISFIED | `test_applies_only_targeted_device` asserts device 2 state unchanged; `test_state_scenes_not_touched` confirms scenes untouched |
| PRESET-03 | 26-01-PLAN | `rig apply --device <id> --preset <id>` updates `state.json` for targeted device only | ✓ SATISFIED | `test_state_updated_for_targeted_device` asserts `last_preset` set; state write uses `state_writer.write()` on confirmed; `test_state_scenes_not_touched` confirms scenes unchanged |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODOs, FIXME, XXX, or stub patterns found in any phase-26 files |

### Human Verification Required

None — all phase goal behaviors are fully verifiable programmatically.

### Gaps Summary

No gaps. All 7 must-have truths verified. All 4 required artifacts exist and are substantively implemented. All 3 key links are correctly wired. All 3 requirements (PRESET-01, PRESET-02, PRESET-03) satisfied with behavioral test evidence.

**Note:** This VERIFICATION.md was created retroactively during the v1.5 milestone audit. The phase was executed with TDD red-green commits and a comprehensive SUMMARY.md, but the formal verification document was not produced during phase execution. All evidence below confirms the phase goal was fully achieved.

### Commit Evidence

| Hash | Type | Description |
|------|------|-------------|
| `f4c2bdd` | test | Failing unit tests for apply_device_preset (RED) |
| `25d4abc` | feat | apply_device_preset engine function (GREEN) |
| `a514b97` | test | Failing CLI tests for --device/--preset (RED) |
| `6cd2da1` | feat | --device/--preset CLI flags with validation and routing (GREEN) |
| `ad57d04` | docs | Plan 26-01 summary |
| `deebccf` | feat | Merge plan 26-01 |
| `bebece1` | docs | Nyquist validation strategy — 14/14 covered |

---

_Verified: 2026-06-17_
_Verifier: pi (gsd-audit-milestone — retrospective verification)_
