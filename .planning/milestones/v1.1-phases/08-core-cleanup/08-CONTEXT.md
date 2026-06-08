# Phase 8: Core Cleanup — Dead Code & Plugin Isolation — Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Source:** Code audit + user direction

<domain>
## Phase Boundary

Clean up `packages/rig` (the core) by removing dead/duplicate code that now lives in plugin packages, and moving plugin-specific interaction code out of core into the respective plugin packages.

This completes the plugin isolation work from Phase 7 — after this phase, core has zero hard imports of plugin-specific modules.

Items out of scope: CI pipelines, PyPI publishing, plugin authoring docs, new features.
</domain>

<decisions>
## Implementation Decisions

### D-CLEANUP-01: Delete duplicate MC6 SysEx from core
- `rig/midi/mc6.py` is identical to `rig_morningstar/sysex.py`
- Delete core copy; update tests to import from plugin
- Plugin `rig_morningstar/sysex.py` is the source of truth

### D-CLEANUP-02: Delete duplicate MC6 generator from core
- `rig/generators/mc6_presets.py` is identical to `rig_morningstar/generator.py`
- Delete core copy; update tests to import from plugin
- Plugin `rig_morningstar/generator.py` is the source of truth

### D-CLEANUP-03: Delete duplicate CBA catalog from core
- `rig/catalog/chase_bliss.py` duplicates `rig_chasebliss/catalog.py`
- Both only contain Mood MkII controls
- Delete core copy; update tests to import from plugin
- Plugin `rig_chasebliss/catalog.py` is the source of truth

### D-CLEANUP-04: Delete dead ChaseBlissApplier from core
- `rig/engine/appliers/chase_bliss.py` is not imported by any production code
- Plugin `rig_chasebliss/applier.py` replaced it
- Delete core copy; update test to import from plugin

### D-CLEANUP-05: Move CBA interaction prompts to rig-chasebliss
- `rig/interaction/cba.py` (`prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_register`) is CBA-specific
- Move to `rig_chasebliss/interaction.py`
- Remove `prompt_cba_*` methods from `ConfirmationIO` Protocol and `RichConfirmationIO`
- Plugin applier (`rig_chasebliss/applier.py`) imports directly from `rig_chasebliss.interaction`

### D-CLEANUP-06: Move analog interaction prompt to rig-analog
- `rig/interaction/analog.py` (`prompt_analog`) is analog-specific
- Move to `rig_analog/interaction.py`
- Remove `prompt_analog` from `ConfirmationIO` Protocol and `RichConfirmationIO`
- Plugin device (`rig_analog/device.py`) imports directly from `rig_analog.interaction`

### D-CLEANUP-07: Refactor Controller model
- `rig/models/controller.py` -> delete file
- `Controller` model is barely used (never constructed in production code)
- `MC6Config` model is barely used
- `ControllerConfig` stays in `device.py` (part of `DeviceConfig` discriminated union)
- Test imports updated to remove `Controller`, `ControllerType`, `MC6Config` references
- `ControllerType` enum is dead code

### D-CLEANUP-08: Clean up shared prompt imports
- `rig/interaction/__init__.py` loses CBA and analog re-exports
- `ConfirmationIO` in `ports.py` becomes generic (only generic prompt methods remain)
- `InMemoryConfirmationIO` in `tests/fakes.py` loses CBA/analog prompt stubs
</decisions>

<specifics>
## Dead Code Inventory

| File | Lines | Duplicate Of | Action |
|------|-------|-------------|--------|
| `rig/midi/mc6.py` | 87 | `rig_morningstar/sysex.py` | Delete |
| `rig/generators/mc6_presets.py` | 72 | `rig_morningstar/generator.py` | Delete |
| `rig/catalog/chase_bliss.py` | 280 | `rig_chasebliss/catalog.py` | Delete |
| `rig/engine/appliers/chase_bliss.py` | 222 | `rig_chasebliss/applier.py` | Delete |
| `rig/interaction/cba.py` | 88 | — | Move to `rig_chasebliss` |
| `rig/interaction/analog.py` | 24 | — | Move to `rig_analog` |
| `rig/models/controller.py` | 30 | — | Delete (unused) |

## Import chain before cleanup
```
rig (core) → rig.engine.ports → rig.interaction.cba      (CBA-specific!)
                               → rig.interaction.analog    (analog-specific!)
```

## Import chain after cleanup
```
rig-chasebliss → rig_chasebliss.interaction  (CBA owns its prompts)
rig-analog     → rig_analog.interaction      (Analog owns its prompts)
```
</specifics>

---

*Phase: 08-core-cleanup*
*Context gathered: 2026-06-07 via code audit*
