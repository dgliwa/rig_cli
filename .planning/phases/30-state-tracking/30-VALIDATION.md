---
phase: 30
slug: state-tracking
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-22
audited: 2026-06-22
---

# Phase 30 — Validation Strategy

> Per-phase validation contract. STATE-01 fully covered by automated tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `packages/rig/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/rig/tests/test_plan.py packages/rig/tests/test_apply.py packages/rig/tests/test_cli_plan.py -v -x` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|------|--------|
| 30-01-T1a | 01 | 1 | STATE-01 criterion 1 | analog→VERIFY when actual==desired; no spurious prompt | unit | `uv run pytest packages/rig/tests/test_plan.py::TestComputePlan::test_analog_gets_verify_when_preset_already_matches_state -v` | test_plan.py:337 | ✅ green |
| 30-01-T1b | 01 | 1 | STATE-01 criterion 1 | analog→ANALOG when actual≠desired; manual prompt required | unit | `uv run pytest packages/rig/tests/test_plan.py::TestComputePlan::test_analog_gets_analog_when_preset_differs_from_state -v` | test_plan.py:353 | ✅ green |
| 30-01-T1c | 01 | 1 | STATE-01 criterion 1 | analog→ANALOG on cold start (no state); safe default | unit | `uv run pytest packages/rig/tests/test_plan.py::TestComputePlan::test_analog_with_no_state_gets_analog -v` | test_plan.py:369 | ✅ green |
| 30-01-T1d | 01 | 1 | STATE-01 criterion 2 | VERIFY skips device.apply() — no prompt for correct device | unit | `uv run pytest packages/rig/tests/test_apply.py::TestVerifyActionSkipped::test_verify_action_does_not_call_device_apply -v` | test_apply.py:614 | ✅ green |
| 30-01-T1e | 01 | 1 | STATE-01 criterion 3 | applying same scene twice → no reprompt on second apply | integration | `uv run pytest packages/rig/tests/test_apply.py::TestVerifyActionSkipped::test_same_scene_applied_twice_no_reprompt_on_second_apply -v` | test_apply.py | ✅ green |
| 30-01-T2 | 01 | 1 | STATE-01 criterion 3 | CLI shows ✓ for analog VERIFY (not ⚠) | unit | `uv run pytest packages/rig/tests/test_cli_plan.py::TestPlanOutput::test_analog_verify_action_uses_checkmark_marker -v` | test_cli_plan.py:154 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

- `packages/rig/tests/test_plan.py` — compute_plan() unit tests
- `packages/rig/tests/test_apply.py` — apply_plan() unit/integration tests
- `packages/rig/tests/test_cli_plan.py` — CLI rendering tests

---

## Manual-Only Verifications

None — all STATE-01 behaviors are fully covered by automated tests.

---

## Validation Audit 2026-06-22

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Gap closed:** `test_same_scene_applied_twice_no_reprompt_on_second_apply` added to `TestVerifyActionSkipped` in `test_apply.py`. Full suite: 373 passed, 0 failures.
