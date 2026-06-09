# Phase 15: Preset Parameter Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 15-Preset Parameter Validation
**Areas discussed:** Validation timing, Error collection, Error format, Validation approach, Hook point

---

## Area 1: Validation Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Plan + apply | Validate in `_detect_cba_setup_for_device()` when building cc_params. Catches errors early in `rig plan` and during `rig apply` before MIDI interaction. | ✓ |
| Apply only (pre-prompt) | Validate at start of `_build_preset`. Simpler but plan won't surface errors. | |

**User's choice:** Both plan + apply
**Notes:** "We should validate that the params are legitimate and the values make sense. Basically does the rig match the schema for a defined CB device type"

### Sub-question: Plan failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Hard fail | Same as YAML validation error — exit with error, no plan output | ✓ |
| Warn only | Show warning but still produce plan | |

**User's choice:** Hard fail

### Sub-question: Error collection

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast | Report first invalid parameter and stop | |
| Collect all | Validate every parameter across every preset, collect all errors | ✓ |

**User's choice:** Collect all (full error collection in one pass)

### Sub-question: Error formatting

| Option | Description | Selected |
|--------|-------------|----------|
| Flat list | Each error fully qualifies itself (device ID, preset name, parameter, allowed values) | |
| Grouped by device/preset | Errors nested under headings per device/preset | ✓ |

**User's choice:** Grouped by device/preset

### Sub-question: Exit output

| Option | Description | Selected |
|--------|-------------|----------|
| Existing error path | `console.print("[red]✗[/red] ...")` + `raise typer.Exit(1)` | ✓ |
| Rich error display | Rendered error panels/tables | |

**User's choice:** Use existing error path

---

## Area 2: Validation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Modify `get_cc_params` | Add validation inside existing method | |
| Separate `validate_cc_params` | Pure validation pass, called before `get_cc_params` | ✓ |

**User's choice:** Separate function

### Sub-question: Error reporting style

| Option | Description | Selected |
|--------|-------------|----------|
| Return errors | Function returns list of errors, caller checks and raises | ✓ |
| Raise directly | Function raises directly with all collected errors | |

**User's choice:** Return errors

### Sub-question: Function location

| Option | Description | Selected |
|--------|-------------|----------|
| `device.py` | Alongside `ChaseBlissConfig` and `get_cc_params` | ✓ |
| `catalog.py` | Alongside `Control` model | |
| New `validation.py` | Separate module | |

**User's choice:** `device.py`

### Sub-question: Core vs plugin error type

| Option | Description | Selected |
|--------|-------------|----------|
| Import `ValidationError` from core | `from rig.config.errors import ValidationError` — keeps existing error handling path | ✓ |
| Define own error type in plugin | `rig_chasebliss.errors.ValidationError` — clean dependency boundary but breaks `except ConfigError` | |

**User's choice:** Import from core

---

## Area 5: Hook Point

| Option | Description | Selected |
|--------|-------------|----------|
| Inside preset loop | Validate per preset inside `_detect_cba_setup_for_device` loop, collect across all, then raise | ✓ |
| Separate pre-scan before loop | Separate pass before building actions | |

**User's choice:** "Looks right" — inside the preset loop

---

## Claude's Discretion

- Exact error formatting strings (beyond device/preset/param/range)
- Type coercion handling for str/bool parameter values against numeric ranges
- Whether to warn or error on ambiguous type mismatches

## Deferred Ideas

None
