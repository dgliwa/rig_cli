---
phase: 5
plan: P5
type: implementation
wave: 3
depends_on: [P2, P3]
files_modified:
  - src/rig/engine/apply.py
  - tests/test_apply.py
requirements: [PLAN-10, D-10, D-11]
must_haves:
  - apply_plan() signature accepts plan as optional (Plan | None = None)
  - When plan is None and rig is provided, apply_plan() calls compute_plan() internally and proceeds
  - When plan is None and rig is None, apply_plan() raises ValueError immediately
  - rig apply CLI command continues to work unchanged from user perspective
  - New test confirms fallback path executes without error
---

# Phase 5 P5: apply_plan() Optional Pre-Computed Plan

## Context

Per D-10 and D-11, `apply_plan()` should accept a pre-computed `Plan` (the plan is authoritative)
but must fall back to calling `compute_plan()` internally when no plan is provided. This allows
`rig apply` to remain a single ergonomic command while also enabling a future flow where plan is
computed once and passed explicitly.

The `apply_plan()` function in `src/rig/engine/apply.py` currently has `plan: Plan` as its first
required parameter (line 52). The change makes it optional with `None` as default. No other
parameter changes are needed.

Read `src/rig/engine/apply.py` lines 51-61 (the function signature) and lines 62-66 (the early
return on clean status) before editing to confirm the exact current state.

The existing `src/rig/cli/commands/apply.py` calls `compute_plan()` and passes it to
`apply_plan()` — it remains valid either way and requires no changes.

---

## Task P5-T9: Make plan parameter optional in apply.py

**File:** `src/rig/engine/apply.py`

**Changes:**

Update the function signature of `apply_plan()` (line 52):

Change `plan: Plan,` to `plan: Plan | None = None,`.

Move it so `plan` remains the first parameter. The full updated signature:

```python
def apply_plan(
    plan: Plan | None = None,
    state_writer: StateWriter = ...,
    midi_connection_io: MidiConnectionIO = ...,
    confirmation_io: ConfirmationIO | None = None,
    rig: Rig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
) -> ApplyResult:
```

Note: `state_writer` and `midi_connection_io` currently have no default values (they are required
positional-after-plan). After making `plan` optional with a default, Python will require that all
following parameters also have defaults or be keyword-only. Read the current signature carefully —
if `state_writer` and `midi_connection_io` are currently required (no default), they must become
keyword-only (add `*` before the first keyword-only parameter after `plan`) or be given defaults.
The cleanest approach that does not break existing callers: add a bare `*` after `plan: Plan |
None = None,` to make all remaining parameters keyword-only. Existing call sites in `apply.py`
CLI commands use keyword arguments already — confirm this in `src/rig/cli/commands/apply.py`
before proceeding.

Add the fallback block as the first thing inside the function body, before the existing
`if plan.status == "clean"` check:

```python
if plan is None:
    if rig is None:
        raise ValueError("apply_plan requires either a pre-computed plan or a rig instance")
    from rig.engine.plan import compute_plan
    plan = compute_plan(rig, root_path=config_path)
```

The local import of `compute_plan` avoids a circular import at module level (apply imports from
plan package; plan imports from models; no cycle risk, but local import keeps the dependency
explicit and mirrors the pattern used in `rig.py` for `DeviceGraph`).

No other changes to `apply.py`. The rest of the function body is unchanged.

---

## Task P5-T10: Create tests/test_apply.py with fallback path test

**File:** `tests/test_apply.py`

**Changes:**

Add `from __future__ import annotations`. Import `pytest`. Import `apply_plan` from
`rig.engine.apply`. Import `Plan` from `rig.engine.plan`. Import `_make_rig` from `tests.test_plan`
(reuse the existing builder — confirm the import path works with `from tests.test_plan import
_make_rig` or use a relative import depending on the test runner config; check `pyproject.toml`
`[tool.pytest.ini_options]` for `pythonpath` or `testpaths` settings to know whether
`from test_plan import _make_rig` or `from tests.test_plan import _make_rig` is correct).

Import `InMemoryStateAdapter` and `InMemoryMidiConnectionIO` from `tests.fakes` (or `fakes`
depending on import path).

**class TestApplyPlanFallback:**

- `test_raises_when_no_plan_and_no_rig`: call `apply_plan()` with neither `plan` nor `rig`
  (just provide required `state_writer` and `midi_connection_io` fakes); assert `ValueError` is
  raised. Use `pytest.raises(ValueError)`.

- `test_fallback_computes_plan_from_rig`: call `apply_plan()` with `plan=None` and a valid rig
  from `_make_rig()`. Pass `dry_run=True` to avoid hardware interaction. Pass
  `InMemoryStateAdapter()` as `state_writer` and `InMemoryMidiConnectionIO()` as
  `midi_connection_io`. Assert the result is an `ApplyResult` instance (no exception raised).
  This confirms the fallback path executes `compute_plan(rig)` internally and proceeds to the
  apply logic.

- `test_explicit_plan_bypasses_compute`: create a `Plan(status="clean")` and pass it explicitly
  as `plan=`. Pass `dry_run=True`. Assert result `status == "no_changes"` (the clean plan
  early-return path). This confirms an explicit plan is used as-is without recomputation.

All assertions use plain `assert` statements except `pytest.raises` for the ValueError test.

### Verification

```
uv run pytest tests/test_apply.py -v
```

All three tests must pass. Zero failures.

```
uv run pytest tests/ -v
```

Full test suite must pass. No regressions from the signature change.
