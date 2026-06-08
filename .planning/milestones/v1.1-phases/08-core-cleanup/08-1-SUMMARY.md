---
phase: 8
plan: 1
name: Remove Dead/Duplicate Core Code
status: completed
commit: 1d50370
---

# Summary

All four dead core files deleted and test imports updated to plugin packages.

## What Was Done

- Deleted `rig/midi/mc6.py` (duplicate of `rig_morningstar.sysex`)
- Deleted `rig/generators/mc6_presets.py` (duplicate of `rig_morningstar.generator`)
- Deleted `rig/catalog/chase_bliss.py` (duplicate of `rig_chasebliss.catalog`)
- Deleted `rig/engine/appliers/chase_bliss.py` (duplicate of `rig_chasebliss.applier`)
- Updated `Device._populate_cba_controls` to import `get_controls` from `rig_chasebliss.catalog`
- Updated all test imports (`test_mc6_sysex`, `test_mc6_generator`, `test_catalog`, `test_appliers`) to reference plugin packages
- Updated `test_base_helpers.py` AST test to check the plugin file path instead of the deleted core path

## Verification

All acceptance criteria met. Full test suite passed.
