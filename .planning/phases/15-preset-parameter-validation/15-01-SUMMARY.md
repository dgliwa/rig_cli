---
phase: 15-preset-parameter-validation
plan: 01
status: complete
commit: (to be filled after commit)
---

## What was done

Added preset parameter validation to the rig-chasebliss plugin so that applying a CBA preset with unknown or out-of-range parameter values fails immediately with a clear, grouped error message, before any physical pedal interaction.

**`validate_cc_params` function (device.py):**
- New module-level function `validate_cc_params(parameters, controls) -> list[str]`
- Returns `[]` when all param names and values are valid
- Returns error strings for: unknown parameter names, out-of-range values (above max or below min), invalid toggle position strings, and invalid toggle position indices
- Handles type coercion safely (try/except around `int()`)
- Empty params dict returns `[]`; empty controls list flags every param as unknown

**Validation wired into `_detect_cba_setup_for_device` (device.py):**
- Calls `validate_cc_params` before `get_cc_params` for each unsaved preset
- Collects all errors across all presets in one pass, grouped by device then preset
- Raises `ValidationError` from `rig.config.errors` (existing error path) with grouped messages on failure
- Error format: `CBA preset validation failed for device '<id>':\n  <device>: preset '<name>' (<id>) — <detail>`

**ValidationError import:**
- Added `from rig.config.errors import ValidationError` import — reuses core error type
- Propagates through existing `except ConfigError` handler in plan.py and apply.py

**Tests:**
- Created `packages/rig-chasebliss/tests/test_device.py` with 10 tests covering valid params, unknown names, out-of-range values, toggle position validation, empty params, multiple errors, and min/max being None
- All 10 validation tests pass alongside existing 14 catalog tests (24 total)

## Must-haves satisfied

- [x] `validate_cc_params(parameters, controls)` returns `[]` when all param names and values are valid
- [x] `validate_cc_params` returns error string for unknown parameter name
- [x] `validate_cc_params` returns error string for out-of-range value (above max or below min)
- [x] Validation fires before `get_cc_params` and before user is prompted for MIDI interaction
- [x] Validation fires via `_detect_cba_setup_for_device` — same code path for apply (dry-run and live)
- [x] Validation errors raise `ValidationError` with grouped messages (device → preset → param detail)
- [x] `uv run pytest packages/rig-chasebliss/ -q` passes (24 passed)
