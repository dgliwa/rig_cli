---
phase: 26
slug: isolated-preset-apply
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-17
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/rig/tests/test_apply_device_preset.py packages/rig/tests/test_cli_apply.py -v` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/rig/tests/test_apply_device_preset.py packages/rig/tests/test_cli_apply.py -v`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | PRESET-01 | — | Only targeted device is applied; all others skipped | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetIsolation::test_applies_only_targeted_device -v` | ✅ | ✅ green |
| 26-01-02 | 01 | 1 | PRESET-02 | T-26-02 | After confirmed apply, state.devices[device_id].last_preset == applied preset | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetIsolation::test_state_updated_for_targeted_device -v` | ✅ | ✅ green |
| 26-01-03 | 01 | 1 | PRESET-03 | T-26-02 | state.scenes not modified; other device entries unchanged | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetIsolation::test_state_scenes_not_touched -v` | ✅ | ✅ green |
| 26-01-04 | 01 | 1 | PRESET-01 | — | dry_run=True suppresses state write | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetDryRun -v` | ✅ | ✅ green |
| 26-01-05 | 01 | 1 | PRESET-01 | — | skipped result does not write state | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetSkipped -v` | ✅ | ✅ green |
| 26-01-06 | 01 | 1 | PRESET-01 | — | setup cancellation short-circuits apply() call | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetSetupCancelled -v` | ✅ | ✅ green |
| 26-01-07 | 01 | 1 | PRESET-02 | — | preset_number resolved from device.presets and passed to DeviceAction | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::TestApplyDevicePresetPresetNumber -v` | ✅ | ✅ green |
| 26-01-08 | 01 | 1 | D-05 | T-26-03 | --device without --preset exits 1 with clear message | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_device_without_preset_exits_1 -v` | ✅ | ✅ green |
| 26-01-09 | 01 | 1 | D-05 | T-26-03 | --preset without --device exits 1 with clear message | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_preset_without_device_exits_1 -v` | ✅ | ✅ green |
| 26-01-10 | 01 | 1 | D-04 | T-26-03 | --scene combined with --device/--preset exits 1 | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_scene_and_device_conflict_exits_1 -v` | ✅ | ✅ green |
| 26-01-11 | 01 | 1 | D-06 | T-26-01 | Unknown device exits 1 before MIDI port opens | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_unknown_device_exits_1 -v` | ✅ | ✅ green |
| 26-01-12 | 01 | 1 | D-06 | T-26-01 | Unknown preset exits 1 before MIDI port opens | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_unknown_preset_exits_1 -v` | ✅ | ✅ green |
| 26-01-13 | 01 | 1 | PRESET-01 | — | No regression: apply without flags routes to compute_plan+apply_plan | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestApplyRouting::test_no_flags_uses_existing_apply_plan_path -v` | ✅ | ✅ green |
| 26-01-14 | 01 | 1 | PRESET-01 | — | --device+--preset routes to apply_device_preset, not apply_plan | CLI integration | `uv run pytest packages/rig/tests/test_cli_apply.py::TestApplyRouting::test_device_preset_flags_route_to_apply_device_preset -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

Test files created during phase execution (TDD red-green):
- `packages/rig/tests/test_apply_device_preset.py` — 7 unit tests for PRESET-01 through PRESET-03
- `packages/rig/tests/test_cli_apply.py` — 7 CLI integration tests for D-04, D-05, D-06

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-17

---

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests verified | 14 |
| Compliant | true |
