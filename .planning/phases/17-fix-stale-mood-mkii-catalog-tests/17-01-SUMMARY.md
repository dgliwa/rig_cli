---
phase: 17-fix-stale-mood-mkii-catalog-tests
plan: 01
status: complete
---

# 17-01 Summary — Fix Stale Mood MkII Catalog Tests

## What changed

Updated two stale assertions in `packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog`:

1. `test_has_expected_knob_count` — updated `len(knobs) == 7` → `len(knobs) == 13`
2. `test_knobs_have_correct_cc_numbers` — corrected CC assignments: `wet_bypass → CC102`, `loop_bypass → CC103` (removed stale `micro_bypass` reference)

## Outcome

- `uv run pytest packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog -v` — 3 passed
- `uv run pytest -q` — 296 passed, 0 failures, 0 errors

## Root cause

Phase 14 expanded MOOD_MKII_CONTROLS from 7 to 13 KNOB controls and renamed CC102/CC103.
The test file was not updated at that time.
