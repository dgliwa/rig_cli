# Phase 1: CBA Tech-Debt Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 01-cba-tech-debt-cleanup
**Areas discussed:** _is_cba handling, Test coverage

---

## _is_cba handling

| Option | Description | Selected |
|--------|-------------|----------|
| Inline it | Fold the 3-line check directly into detect_cba_setup. Removes a symbol, no loss of expressiveness — the function body is trivial. | ✓ |
| Rename to is_cba (public) | Keep it as a named function but drop the underscore. Makes it available if future callers in Phase 2/3 need a quick CBA type-check without importing the full plan module. | |

**User's choice:** Inline it
**Notes:** `_is_cba` is only called once, inside `detect_cba_setup`. Inlining eliminates a symbol without losing clarity.

---

## Test coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Existing tests are enough | The refactor is behavior-neutral. If existing CBA applier tests pass after the rename + helper extraction, that's sufficient. No new tests needed. | ✓ |
| Add unit tests for the helpers | Write a small test for mark_preset_saved (verifies presets_saved dict update) and detect_cba_setup (verifies it returns correct action types). Future Phase 2 test work builds on these. | |

**User's choice:** Existing tests are enough
**Notes:** Phase 2 (DEC-07) is where test infrastructure gets built. Phase 1 doesn't pre-build it.

---

## Claude's Discretion

- `mark_preset_saved` implementation: compose with existing `update_device_state` helper in `base.py` rather than duplicating the `model_copy` pattern.

## Deferred Ideas

None — discussion stayed within phase scope.
