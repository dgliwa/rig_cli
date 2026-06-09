# Phase 15: Preset Parameter Validation - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate CBA preset parameter names and values against the device's catalog controls before any physical pedal interaction. Invalid parameters (unknown names or out-of-range values) cause a hard failure with a clear, grouped error message during both `rig plan` and `rig apply`.

This phase adds validation — it does not change the apply flow beyond adding the validation gate. Reset-to-defaults (sending all controls to their catalog default before applying a preset) is Phase 16.

</domain>

<decisions>
## Implementation Decisions

### D-01: Validation Timing
- Validation fires in both `rig plan` and `rig apply` — not apply-only
- Validation is called inside `_detect_cba_setup_for_device()` in `device.py`, before `get_cc_params` is called to build `CbaSetupAction`
- This means `rig plan` will hard-fail if preset parameters don't match the catalog, surfacing errors before the user runs apply

### D-02: Hard Fail Behavior
- Invalid parameters cause a hard failure in both plan and apply — no warnings or partial plans
- Uses the existing error output pattern: `console.print("[red]✗[/red] ...")` + `raise typer.Exit(1)`
- Same behavior as YAML validation errors — the pipeline stops

### D-03: Full Error Collection
- All errors are collected across ALL presets in one pass before raising
- Not fail-fast — the user sees every invalid parameter in a single run
- Errors are **grouped by device, then by preset** so the user can see exactly which entries in rig.yaml need fixing

### D-04: Error Format
- Each error includes: device ID, preset name, parameter name, and what's wrong (unknown name or allowed range)
- Uses `from rig.config.errors import ValidationError` from core — the plugin reuses the existing error type
- No new error types in the plugin package

### D-05: Separate `validate_cc_params` Function
- A new function `validate_cc_params(parameters: dict, controls: list[Control]) -> list[str]` is added to `device.py`
- Returns a list of error strings (empty list = valid)
- Called from `_detect_cba_setup_for_device` in the preset loop, right before `get_cc_params`
- Separate from `get_cc_params` which remains a clean transform

### D-06: Validation Rule
- Parameter name must match a `Control.name` in the device's catalog controls (case-sensitive)
- Parameter value must be within `Control.min` to `Control.max` range (inclusive)
- Boolean/string parameter values for toggle positions are validated when `positions` is non-empty — need to handle type coercion consistently with how CC values are computed during apply

### Claude's Discretion
- The exact error formatting strings (beyond the required device/preset/param/range info)
- How to handle type coercion for `str` and `bool` parameter values against numeric `min`/`max` (e.g., toggle positions)
- Whether validation warns or errors on parameters where the type mismatch between value (str/bool) and control range (float) is ambiguous — planner should consult `get_cc_params`'s current `int(value)` pattern for guidance

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CBA plugin device model
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — `ChaseBlissConfig`, `get_cc_params`, `_detect_cba_setup_for_device`. Where `validate_cc_params` will be added and where validation is called.
- `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` — `Control` model (name, min, max, positions, type). Validation reads these fields.
- `packages/rig-chasebliss/src/rig_chasebliss/models.py` — `CbaSetupAction` model. Actions are built after validation passes.

### CBA preset model
- `packages/rig-chasebliss/src/rig_chasebliss/preset.py` — `DigitalPreset` (extends `Preset`) with `parameters: dict[str, float | str | bool]`. The input to validation.

### Error handling
- `packages/rig/src/rig/config/errors.py` — `ValidationError(ConfigError)`. The error type imported and raised by the plugin.
- `packages/rig/src/rig/cli/commands/plan.py` — `except ConfigError: console.print(...); raise typer.Exit(1)`. Existing pattern for error display. Exit code 1 for config errors.

### CBA apply flow
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — `ChaseBlissApplier.apply_setup()` / `_build_preset()`. The apply-side code that runs after validation passes.

### Tests
- `packages/rig-chasebliss/tests/test_catalog.py` — Existing tests; new validation tests go in `packages/rig-chasebliss/tests/test_device.py` (new file).

</canonical_refs>

<code_context>
## Existing Code Insights

### Key Function to Validate Against
- `get_cc_params` in `ChaseBlissConfig` (device.py:34-39) — currently iterates controls and silently skips params not matching a control name. Validation replaces the silent skip with an error.

### Pattern for Error Handling
- `rig.config.errors.ValidationError` — used by loader.py for validation failures. Matches the `ConfigError` catch in plan.py line 53-56.

### Integration Point
- `_detect_cba_setup_for_device` (device.py:46-87) — iterates presets, calls `get_cc_params(preset.parameters)`. Validation fire immediately before this call, in the same loop.

</code_context>

<specifics>
## Specific Ideas

- The validation should mirror the logic in `get_cc_params` for name matching (control exists with that name) and the existing `Control.min`/`Control.max` for range checking
- For TOGGLE/DIPSWITCH controls with `positions`, the valid range is implicit from `positions` list indices — validation should use `min`/`max` if set, else derive from `len(positions) - 1`
- The TODO on `DigitalPreset` in preset.py (`# TODO: 1.3 when parsing the cba device, we should have custom validation...`) is the original motivator — this phase resolves it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-preset-parameter-validation*
*Context gathered: 2026-06-08*
