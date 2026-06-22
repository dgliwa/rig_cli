---
phase: 32-per-parameter-plan-diffs
verified: 2026-06-22T22:10:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 32: Per-Parameter Plan Diffs Verification Report

**Phase Goal:** `rig plan` output shows specific CC values or knob positions that will change — not just a "changed" label at the scene level.
**Verified:** 2026-06-22T22:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | rig plan output shows each changed parameter with before and after values per device action | VERIFIED | `plan.py` lines 103-105 and 113-115 loop `action.param_diff` and print `name: before -> after`; `TestParamDiffRendering::test_analog_param_diff_lines_shown_when_no_prior_state` and `test_digital_param_diff_lines_shown_when_changed` pass |
| 2 | Unchanged parameters within a changed scene are not listed | VERIFIED | `_compute_param_diff` only appends a `ParamDiff` when `before_val != after_val` (compute.py line ~50); `TestParamDiff::test_analog_param_diff_shows_changed_params_only` confirms only the changed `gain` (5.0->8.0) appears while unchanged `tone` is absent; CLI analogue `test_analog_param_diff_shows_changed_params_only` also passes |
| 3 | Analog devices show knob/switch names and positions, not CC numbers | VERIFIED | `_compute_param_diff` reads `preset.values` (AnalogPreset dict keyed by human-readable name); keys like `"gain"`, `"tone"` come from the YAML `values:` dict, never from CC numbers; `test_analog_param_diff_populated_when_no_prior_state` asserts `diff_map["gain"]` and `diff_map["tone"]` |
| 4 | VERIFY actions never show param_diff lines | VERIFIED | ANALOG branch in compute.py sets `param_diff = []` when `not analog_needs_change`; CONFIGURE branch sets `digital_param_diff = []` when `not needs_config`; plan.py VERIFY branch (lines 116-120) has no param_diff loop at all; `TestParamDiff::test_analog_verify_action_has_empty_param_diff` and CLI `test_verify_action_has_no_param_diff_lines` both pass |
| 5 | rig plan --format json includes param_diff field on every DeviceAction | VERIFIED | `param_diff: list[ParamDiff] = []` on `DeviceAction` model; Pydantic `model_dump_json()` serializes it automatically; `TestPlanJsonParamDiff::test_json_output_includes_param_diff_field` asserts key present on every action; `test_json_param_diff_populated_for_analog_action` confirms correct `{name, before, after}` shape |
| 6 | before is None when there is no prior state for a device | VERIFIED | `_compute_param_diff` uses `before_params.get(key)` which returns `None` for missing keys, then checks `if before_preset is None` to always append when cold-starting; `ParamDiff.before: float \| str \| bool \| None` allows None; `test_json_param_diff_populated_for_analog_action` asserts `gain_diff["before"] is None`; text output test asserts `"?" in result.output` (which is the `before_str` representation of None) |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/rig/src/rig/engine/plan/models.py` | ParamDiff model and param_diff field on DeviceAction | VERIFIED | `class ParamDiff(BaseModel)` at line 17; `param_diff: list[ParamDiff] = []` at line 33 |
| `packages/rig/src/rig/engine/plan/compute.py` | `_find_preset` and `_compute_param_diff` helpers wired into compute_plan | VERIFIED | Both functions present (lines 25, 34); `ParamDiff` imported line 6; wired into ANALOG branch (lines 123-138) and CONFIGURE branch (lines 156-173) |
| `packages/rig/src/rig/cli/commands/plan.py` | sub-line rendering of param diffs for ANALOG and CONFIGURE actions | VERIFIED | `for diff in action.param_diff:` loops present after ANALOG (line 103) and CONFIGURE (line 113) blocks; VERIFY branch has no such loop |
| `packages/rig/tests/test_plan.py` | TestParamDiff class covering all diff scenarios | VERIFIED | `class TestParamDiff` at line 507; 7 tests covering analog cold start, changed-only params, VERIFY empty, digital cold start, digital changed-only, HX Stomp empty, ParamDiff model serialization |
| `packages/rig/tests/test_cli_plan.py` | CLI tests for param diff display in text and JSON output | VERIFIED | `class TestParamDiffRendering` (5 tests) at line 355; `class TestPlanJsonParamDiff` (4 tests) at line 450; 9 CLI tests total |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `packages/rig/src/rig/engine/plan/compute.py` | `packages/rig/src/rig/engine/plan/models.py` | ParamDiff import; assigned to DeviceAction.param_diff | VERIFIED | `from rig.engine.plan.models import ActionStatus, DeviceAction, ParamDiff, Plan, ScenePlan` at line 6; `ParamDiff(name=key, before=before_val, after=after_val)` used in `_compute_param_diff`; `param_diff=param_diff` passed to `DeviceAction(...)` in both action branches |
| `packages/rig/src/rig/cli/commands/plan.py` | `packages/rig/src/rig/engine/plan/models.py` | action.param_diff iteration in ANALOG and CONFIGURE branches | VERIFIED | `for diff in action.param_diff:` at lines 103 and 113; `diff.name`, `diff.before`, `diff.after` accessed; `before_str = "?" if diff.before is None else str(diff.before)` |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces computed plan output (not a UI component rendering DB data). The data flows from YAML preset definitions through `_find_preset` / `_compute_param_diff` into `DeviceAction.param_diff`, which is serialized to JSON or rendered as text. All stages verified above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TestParamDiff (7 tests) | `uv run pytest packages/rig/tests/test_plan.py::TestParamDiff -v` | 7 passed in 0.03s | PASS |
| TestParamDiffRendering (5 tests) | `uv run pytest packages/rig/tests/test_cli_plan.py::TestParamDiffRendering -v` | 5 passed | PASS |
| TestPlanJsonParamDiff (4 tests) | `uv run pytest packages/rig/tests/test_cli_plan.py::TestPlanJsonParamDiff -v` | 4 passed | PASS |
| Full test suite | `uv run pytest packages/rig/tests/ -q` | 305 passed in 0.43s | PASS |

### Probe Execution

No probes defined for this phase (no `probe-*.sh` scripts referenced).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PLAN-32-01 | 32-01-PLAN.md | param_diff field on DeviceAction; before/after values shown | SATISFIED | `ParamDiff` model + `param_diff` field exist and populate correctly |
| PLAN-32-02 | 32-01-PLAN.md | Unchanged params within changed scene not listed | SATISFIED | `_compute_param_diff` only emits diffs where values differ |
| PLAN-32-03 | 32-01-PLAN.md | Analog devices show knob/switch names, not CC numbers | SATISFIED | Uses `preset.values` dict (human-readable YAML keys) |
| PLAN-32-04 | 32-01-PLAN.md | JSON output includes param_diff on all DeviceActions | SATISFIED | Pydantic serialization includes field by default; tests confirm |

Roadmap SCs 1-4 align directly to the above four requirements — all satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/rig/src/rig/cli/commands/plan.py` | 80 | `TODO: scene plans should have their own logging output class` | INFO | Pre-existing marker; introduced before phase 32 (commit `469b23c` predates phase 32 commits; confirmed via git blame — marker was already present in `469b23c` which is pre-phase-32) |
| `packages/rig/src/rig/engine/plan/compute.py` | 95 | `TODO: not a fan of defining functions INSIDE functions` | INFO | Pre-existing marker; present in `5c2dc0f` (pre-phase-32 commit; confirmed `1f3d23b` diff shows no `+TODO` line) |

Both TODO markers were verified as pre-existing before any phase 32 commits. Neither was introduced by this phase. Per the debt-marker gate, only markers _introduced_ by a phase are blockers. These are informational carry-forwards.

The CLI rendering uses `[dim]` Rich markup wrapping (e.g. `[dim]{diff.name}: {before_str} → {diff.after}[/dim]`) while the PLAN specified "No Rich markup on param diff sub-lines." This is a minor deviation — the `[dim]` markup produces dimmed gray text rather than plain text, and does not affect the informational content. It is not a functional gap.

### Human Verification Required

None. All truths are machine-verifiable and confirmed by passing tests.

### Gaps Summary

No gaps. All 6 must-have truths verified, all 5 artifacts substantive and wired, both key links confirmed, all 305 tests passing. Phase goal is achieved: `rig plan` output now shows specific knob positions and CC values that will change per device action, with unchanged parameters suppressed, proper before/after formatting including `?` for cold starts, and JSON serialization of the full diff structure.

---

_Verified: 2026-06-22T22:10:00Z_
_Verifier: Claude (gsd-verifier)_
