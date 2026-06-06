---
phase: 5
plan: P4
subsystem: cli
tags: [plan-command, cli, exit-codes, output-formatting, smoke-tests]
dependency_graph:
  requires: [P2, P3]
  provides: [plan-command-complete]
  affects: [src/rig/cli/commands/plan.py]
tech_stack:
  added: []
  patterns: [typer-exit-codes, cold-start-detection, structured-cli-output]
key_files:
  created:
    - tests/test_cli_plan.py
  modified:
    - src/rig/cli/commands/plan.py
decisions:
  - Cold-start warning is suppressed in JSON mode to avoid corrupting JSON output
  - Scenes require a CONTROLLER device with ControllerConfig for Rig.scenes to resolve — smoke tests include mc6.yaml device fixture
metrics:
  duration: ~15 minutes
  completed: 2026-06-06
  tasks: 2
  files_changed: 2
---

# Phase 5 Plan P4: CLI Plan Command — Output Formatting & Smoke Tests Summary

Rewrote `src/rig/cli/commands/plan.py` with correct exit codes, cold-start detection, structured two-section output, and warnings. Added 4 CLI smoke tests in `tests/test_cli_plan.py`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| T8 | Rewrite plan CLI command | 67843b7 | src/rig/cli/commands/plan.py |
| T8b | CLI smoke tests for plan command | 46d271e | tests/test_cli_plan.py |

## What Was Built

### T8 — plan CLI rewrite (67843b7)

Rewrote `src/rig/cli/commands/plan.py` with all must-have behaviors:

- **Exit codes**: exits 0 when `plan.status == "clean"` and `missing_refs` is empty; exits 2 when `status == "changes_detected"` OR `missing_refs` is non-empty; exits 1 on `ConfigError`
- **Cold-start warning**: printed in text mode only when `.rig/state.json` is absent — suppressed in JSON mode to prevent corrupting JSON output
- **ConfigError catch**: wraps both `load_rig()` and `compute_plan()` calls; prints `✗ {error}` and exits 1
- **Setup Actions section**: printed before Scenes when `cba_setup` is non-empty; each CBA action uses `~` marker
- **Action markers**: configure uses `~`, verify uses `✓`, analog uses `⚠`
- **`--show-unchanged` flag**: controls whether `ScenePlan.status == "unchanged"` scenes are rendered
- **Warnings section**: missing_refs printed as `Warnings — Missing References`, unused_presets as `Warnings — Unused Presets`
- **Summary line**: `Plan: No changes — N already set, N manual` when clean; `Plan: N to configure, N manual, N already set` otherwise

### T8b — CLI smoke tests (46d271e)

Added `tests/test_cli_plan.py` with 4 `typer.testing.CliRunner` tests:

- `test_plan_exits_0_when_clean`: writes rig + matching state.json; asserts `exit_code == 0`
- `test_plan_exits_2_when_changes_detected`: writes rig with no state.json; asserts `exit_code == 2`
- `test_plan_cold_start_warning`: asserts `"Cold start"` in output when no state.json
- `test_plan_summary_line_present_when_clean`: asserts `"Plan:"` and `"No changes"` in output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cold-start warning printed before JSON mode check**

- **Found during:** T8b test run
- **Issue:** `console.print("[yellow]⚠ Cold start..."` was emitted unconditionally before the `if output_format == "json": return` branch. This prepended the warning text to the JSON output, causing `json.loads(result.stdout)` to raise `JSONDecodeError` in the existing `test_plan_json` and `test_plan_short_format_flag` tests.
- **Fix:** Moved the cold-start `console.print` call to after the `if output_format == "json": ... return` block so it only runs in text mode.
- **Files modified:** src/rig/cli/commands/plan.py
- **Commit:** 67843b7 (fixed within same commit)

**2. [Rule 1 - Bug] Smoke test fixture missing CONTROLLER device**

- **Found during:** T8b test run (test_plan_exits_2_when_changes_detected failed with exit 0)
- **Issue:** The minimal rig fixture in tests/test_cli_plan.py did not include a CONTROLLER device. `Rig.scenes` returns an empty dict unless a CONTROLLER device with `ControllerConfig` is present (per the domain model). Without scenes, `plan.status` was always `"clean"` regardless of state, making `exit_code` always 0.
- **Fix:** Added `mc6.yaml` (type: controller) to the fixture's devices dir so the loader wires the scene from `scenes/main.yaml` into `ControllerConfig.scenes`.
- **Files modified:** tests/test_cli_plan.py
- **Commit:** 46d271e

## Verification

```
uv run pytest tests/test_cli_plan.py -v   # 4 passed
uv run pytest tests/ -q -k "not test_apply"  # 239 passed, 24 deselected
uv run python -c "from rig.cli.commands.plan import plan; print('import ok')"  # import ok
```

## Self-Check: PASSED

- [x] src/rig/cli/commands/plan.py committed at 67843b7
- [x] tests/test_cli_plan.py committed at 46d271e
- [x] 239 tests pass (no regressions)
- [x] import ok verified
