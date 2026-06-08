---
phase: 8
plan: 2
name: Move Plugin-Specific Interactions to Plugin Packages
status: completed
commit: 488fcf0
---

# Summary

CBA and analog prompt functions moved out of core and into their respective plugin packages. `ConfirmationIO` Protocol trimmed to generic methods only.

## What Was Done

- Created `rig_chasebliss/interaction.py` with `prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_register`
- Created `rig_analog/interaction.py` with `prompt_analog`
- Deleted `rig/interaction/cba.py` and `rig/interaction/analog.py` from core
- Removed `prompt_cba_*` and `prompt_analog` methods from `ConfirmationIO` Protocol and `RichConfirmationIO` in `ports.py`
- Removed CBA/analog prompt stubs from `InMemoryPromptAdapter` in `fakes.py`
- Updated `rig_chasebliss/applier.py` to call prompt functions directly (no longer via `ctx.confirmation_io`)
- Updated `rig_analog/device.py` to call `prompt_analog` directly
- Updated tests to use `mock.patch` for prompt functions instead of `InMemoryConfirmationIO` stubs

## Verification

All acceptance criteria met. Full test suite passed.
