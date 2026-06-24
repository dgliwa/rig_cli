---
phase: 32
slug: per-parameter-plan-diffs
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-24
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for PLAN-01/02 (per-parameter plan diffs). Reconstructed from plan, summary, and verification artifacts.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `packages/rig/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/rig/tests/test_plan.py packages/rig/tests/test_cli_plan.py -q` |
| **Full suite command** | `uv run pytest packages/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File | Status |
|---------|------|------|-------------|-----------|-------------------|------|--------|
| 32-01-01 | 01 | 1 | PLAN-01 — ParamDiff model and param_diff field on DeviceAction | unit | `uv run pytest packages/rig/tests/test_plan.py::TestParamDiff -q` | `test_plan.py` | ✅ green |
| 32-01-02 | 01 | 1 | PLAN-01 — `_compute_param_diff` wired into compute_plan for ANALOG/CONFIGURE | unit | `uv run pytest packages/rig/tests/test_plan.py::TestParamDiff -q` | `test_plan.py` | ✅ green |
| 32-01-03 | 01 | 1 | PLAN-01 — CLI renders before/after lines under ANALOG/CONFIGURE actions | integration | `uv run pytest packages/rig/tests/test_cli_plan.py::TestParamDiffRendering -q` | `test_cli_plan.py` | ✅ green |
| 32-01-04 | 01 | 1 | PLAN-02 — JSON output includes param_diff on every DeviceAction | integration | `uv run pytest packages/rig/tests/test_cli_plan.py::TestPlanJsonParamDiff -q` | `test_cli_plan.py` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. No new test infrastructure was needed.*

---

## Test Coverage Map

| Requirement | Test File | Test Class / Name | Assertion |
|-------------|-----------|-------------------|-----------|
| PLAN-01: ParamDiff model | `test_plan.py` | `TestParamDiff::test_param_diff_model_serialization` | `ParamDiff(name="gain", before=5.0, after=8.0)` serializes correctly |
| PLAN-01: analog cold start (before=None) | `test_plan.py` | `TestParamDiff::test_analog_param_diff_populated_when_no_prior_state` | `diff_map["gain"]["before"] is None` |
| PLAN-01: changed params only | `test_plan.py` | `TestParamDiff::test_analog_param_diff_shows_changed_params_only` | unchanged `tone` absent from diff |
| PLAN-01: VERIFY empty | `test_plan.py` | `TestParamDiff::test_analog_verify_action_has_empty_param_diff` | `action.param_diff == []` |
| PLAN-01: digital cold start | `test_plan.py` | `TestParamDiff::test_digital_param_diff_populated_when_no_prior_state` | CC diffs present |
| PLAN-01: digital changed only | `test_plan.py` | `TestParamDiff::test_digital_param_diff_shows_changed_params_only` | only changed CC present |
| PLAN-01: HX Stomp empty | `test_plan.py` | `TestParamDiff::test_hx_stomp_has_empty_param_diff` | `action.param_diff == []` |
| PLAN-01: CLI text rendering | `test_cli_plan.py` | `TestParamDiffRendering::test_analog_param_diff_lines_shown_when_no_prior_state` | "gain" and "tone" sub-lines rendered |
| PLAN-01: CLI changed only | `test_cli_plan.py` | `TestParamDiffRendering::test_analog_param_diff_shows_changed_params_only` | only changed param in output |
| PLAN-01: CLI VERIFY no sub-lines | `test_cli_plan.py` | `TestParamDiffRendering::test_verify_action_has_no_param_diff_lines` | no sub-lines for VERIFY |
| PLAN-01: CLI digital rendering | `test_cli_plan.py` | `TestParamDiffRendering::test_digital_param_diff_lines_shown_when_changed` | CC value sub-lines shown |
| PLAN-02: JSON param_diff present | `test_cli_plan.py` | `TestPlanJsonParamDiff::test_json_output_includes_param_diff_field` | `param_diff` key on all actions |
| PLAN-02: JSON populated analog | `test_cli_plan.py` | `TestPlanJsonParamDiff::test_json_param_diff_populated_for_analog_action` | `gain` diff with `before: null` |

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Audit 2026-06-24

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All requirements COVERED by tests at completion time. VERIFICATION.md score 6/6. 399 tests pass, 0 failures.

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not required — existing infrastructure covers all requirements
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-24
