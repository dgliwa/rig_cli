---
phase: 5
slug: dependency-graph-plan-command
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-06
audited: 2026-06-06
---

# Phase 5 — Validation Strategy

> Reconstructed from phase artifacts (State B). All 20 must-haves verified; 5 gaps filled by audit.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_graph.py tests/test_plan.py tests/test_cli_plan.py tests/test_apply.py tests/test_appliers.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| P5-T1 | P1 | 1 | D-01 | unit | `uv run pytest tests/test_graph.py -q` | ✅ green |
| P5-T2 | P1 | 1 | D-02 | unit | `uv run pytest tests/test_graph.py -q` | ✅ green |
| P5-T3 | P1 | 1 | D-03 | unit | `uv run pytest tests/test_graph.py::TestCycleDetection -q` | ✅ green |
| P5-T4 | P2 | 1 | PLAN-02, D-04, D-05, D-06 | unit | `uv run pytest tests/test_plan.py -q` | ✅ green |
| P5-T5 | P2 | 1 | PLAN-02 | unit | `uv run pytest tests/test_plan.py::TestBeforeAfterFields -q` | ✅ green |
| P5-T6 | P3 | 2 | PLAN-01, D-07, D-04, D-05, D-06 | unit | `uv run pytest tests/test_plan.py -q` | ✅ green |
| P5-T7 | P3 | 2 | D-07 | unit | `uv run pytest tests/test_plan.py::TestDeviceOrdering -q` | ✅ green |
| P5-T7b | P3 | 2 | PLAN-01 | unit | `uv run pytest tests/test_plan.py::TestComputeDiff -q` | ✅ green |
| P5-T8 | P4 | 3 | PLAN-03..09, D-06..09 | integration | `uv run pytest tests/test_cli_plan.py -q` | ✅ green |
| P5-T8b | P4 | 3 | PLAN-06, PLAN-07, PLAN-05 | integration | `uv run pytest tests/test_cli_plan.py::TestPlanExitCodes tests/test_cli_plan.py::TestPlanColdStart tests/test_cli_plan.py::TestPlanSummaryLine -q` | ✅ green |
| P5-T9 | P5 | 3 | D-11 | unit | `uv run pytest tests/test_apply.py::TestApplyPlanFallback -q` | ✅ green |
| P5-T10 | P5 | 3 | D-11 | unit | `uv run pytest tests/test_apply.py::TestApplyPlanFallback -q` | ✅ green |
| P5-T11 | P6 | 4 | D-10, PLAN-10 | unit | `uv run pytest tests/test_appliers.py::TestChaseBlissApplierSetup -q` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Audit 2026-06-06

| Metric | Count |
|--------|-------|
| Gaps found | 5 |
| Resolved | 5 |
| Escalated | 0 |

### Gaps Resolved

| Requirement | Description | Test Added | File |
|-------------|-------------|------------|------|
| D-07 | `device_actions` sorted by `DeviceGraph.apply_order()` within each ScenePlan | `TestDeviceOrdering` | `tests/test_plan.py` |
| D-08 / PLAN-03 | CLI visual markers: `~` configure, `✓` verify, `⚠` analog | `TestPlanVisualMarkers` | `tests/test_cli_plan.py` |
| D-09 | Summary line reflects configure count when CBA setup actions present | `TestPlanSummaryLine::test_plan_summary_line_reflects_count_with_changes` | `tests/test_cli_plan.py` |
| PLAN-08 | `--show-unchanged` flag controls unchanged scene visibility | `TestShowUnchanged` | `tests/test_cli_plan.py` |
| PLAN-09 | `--scene <name>` filter shows only that scene | `TestSceneFilter` | `tests/test_cli_plan.py` |

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements. No additional setup was needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] No wave 0 missing references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-06
