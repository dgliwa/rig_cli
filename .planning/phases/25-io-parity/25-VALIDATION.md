---
phase: 25
slug: io-parity
status: compliant
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-17
---

# Phase 25 — Validation Strategy

**Phase Goal:** Thread ConfirmationIO through AnalogDevice.apply() — eliminating the last raw input() call in any applier path. All device confirmation prompts route through the ConfirmationIO Protocol.

## Test Infrastructure

| Tool | Config | Command |
|------|--------|---------|
| pytest | `pyproject.toml` (uv workspaces) | `make test` |
| uv | workspace root | `uv run pytest` |

## Per-Task Requirement Map

| Task | Requirement | Behavior | Test File | Test Name | Status |
|------|-------------|----------|-----------|-----------|--------|
| Task 1 | IO-01 | `prompt_device()` prints "Set {device} manually (knobs/switches)" when `midi_channel=None` | `packages/rig/tests/test_interaction_midi.py` | `test_prompt_device_analog_prints_set_manually` | ✓ COVERED |
| Task 2 | IO-01 | `AnalogDevice.apply()` calls `ctx.confirmation_io.prompt_device()` — confirm path returns confirmed | `packages/rig/tests/test_devices.py:133` | `test_analog_device_apply_confirm_returns_confirmed` | ✓ COVERED |
| Task 2 | IO-01 | `AnalogDevice.apply()` calls `ctx.confirmation_io.prompt_device()` — quit path returns error | `packages/rig/tests/test_devices.py:147` | `test_analog_device_apply_quit_returns_error` | ✓ COVERED |
| Task 3 | IO-01 | `prompt_analog` not importable from `rig_analog` or `rig_analog.interaction` | `packages/rig-analog/tests/test_analog_exports.py` | `test_prompt_analog_not_in_rig_analog` | ✓ COVERED |
| Task 4 | IO-02 | 3 analog tests use `InMemoryPromptAdapter` without monkeypatching `builtins.input` | `packages/rig/tests/test_devices.py:338` | `test_analog_device_apply_skip_returns_skipped` | ✓ COVERED |
| Task 5 | IO-01, IO-02 | Full test suite passes with no regressions | all | `make test` | ✓ COVERED |

## Manual-Only Items

None — all phase goal behaviors are verifiable programmatically.

## Validation Sign-Off

| Metric | Value |
|--------|-------|
| Requirements | IO-01, IO-02 |
| Tasks with automated tests | 5/5 |
| Tests added this phase | 4 (migrated 3 + new 1 interaction + 1 export guard) |
| Total suite | 313 passed |
| Nyquist compliant | yes |

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |

**Gaps filled:**
- `test_interaction_midi.py` — verifies `prompt_device()` emits the analog message when `midi_channel=None`
- `test_analog_exports.py` — guards against accidental re-introduction of `prompt_analog`
