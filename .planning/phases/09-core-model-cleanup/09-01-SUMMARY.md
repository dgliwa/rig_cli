---
phase: 09-core-model-cleanup
plan: 01
subsystem: models
tags: [scene, rig, loader, cli]
requires:
  - phase: 08
    provides: dead code elimination from core
provides:
  - Clean Scene model (no mc6_bank/mc6_switch)
  - Rig.scenes as direct Pydantic field (not ControllerConfig property)
  - Rig compat properties removed (pedals, _controller_device, digital_presets, hx_presets, analog_presets, mc6)
  - CLI commands use rig.devices (not rig.pedals)
  - Morningstar generator uses rig.controller (not rig.mc6)
affects: [phase 10, phase 11]
tech-stack:
  added: []
  patterns: ["scenes is a direct model field on Rig rather than a property routing through ControllerConfig"]
key-files:
  created: []
  modified:
    - packages/rig/src/rig/models/scene.py
    - packages/rig/src/rig/models/rig.py
    - packages/rig/src/rig/config/loader.py
    - packages/rig/src/rig/cli/commands/status.py
    - packages/rig/src/rig/cli/commands/validate.py
    - packages/rig-morningstar/src/rig_morningstar/device.py
    - packages/rig-morningstar/src/rig_morningstar/generator.py
    - packages/rig/tests/test_models.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_diff.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_appliers.py
    - packages/rig/tests/test_mc6_generator.py
    - packages/rig/tests/test_catalog.py
key-decisions:
  - "Morningstar generator.py was updated to use rig.controller instead of rig.mc6 (planned for Wave 3 but required now since rig.mc6 was removed)"
patterns-established: []
requirements-completed:
  - MODEL-03
  - MODEL-04
duration: 28min
completed: 2026-06-08
---

# Phase 09: Core Model Cleanup — Wave 1 Summary

**Removed Scene mc6_bank/mc6_switch fields; made Rig.scenes a direct Pydantic field; removed 6 dead compat properties from Rig (pedals, _controller_device, digital_presets, hx_presets, analog_presets, mc6); updated status.py, validate.py, and morningstar plugin to use rig.devices/rig.controller instead**

## Performance

- **Duration:** 28 min
- **Started:** 2026-06-08T04:00:00Z
- **Completed:** 2026-06-08T04:28:00Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments
- Scene model no longer has `mc6_bank` or `mc6_switch` fields
- `Rig.scenes` is now a real `dict[str, Scene]` Pydantic model field, not a property routing through ControllerConfig
- Removed 6 dead compat properties from Rig: `pedals`, `_controller_device`, `digital_presets`, `hx_presets`, `analog_presets`, `mc6`
- `Rig.controller` simplified to iterate devices directly
- Loader passes `scenes=scenes` directly to Rig constructor (no more ControllerConfig scene wiring)
- status.py, validate.py use `rig.devices` instead of `rig.pedals`
- Morningstar device.py uses `rig.devices.get()` instead of `rig.pedals.get()`
- Morningstar generator.py uses `rig.controller` instead of `rig.mc6`
- All 299 tests pass (1 scene test removed for mc6_switch validation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Scene/Rig/Loader changes + test updates** - (pending commit)
2. **Task 2: CLI command updates** - (pending commit)

## Files Modified
- `packages/rig/src/rig/models/scene.py` - Removed mc6_bank, mc6_switch, Literal import
- `packages/rig/src/rig/models/rig.py` - Removed imports, added scenes field, removed 6 properties, simplified controller
- `packages/rig/src/rig/config/loader.py` - Removed ControllerConfig/ChaseBlissConfig imports, removed scene-wiring block, passes scenes=scenes to Rig
- `packages/rig/src/rig/cli/commands/status.py` - Uses rig.devices, len(device.presets)
- `packages/rig/src/rig/cli/commands/validate.py` - Uses rig.devices
- `packages/rig-morningstar/src/rig_morningstar/device.py` - Uses rig.devices.get()
- `packages/rig-morningstar/src/rig_morningstar/generator.py` - Uses rig.controller instead of rig.mc6
- 8 test files updated to pass scenes directly to Rig constructor

## Decisions Made
- **Morningstar generator ahead of schedule**: generator.py was updated to use `rig.controller.config.banks` instead of `rig.mc6` in Wave 1 (planned for Wave 3) because `rig.mc6` was removed in this wave — the cross-wave dependency was tighter than the plan anticipated.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Cross-wave dependency on generator.py**: The plan's Wave 3 task for `generator.py` was a hard dependency of Wave 1's `rig.mc6` removal. Fixed by pulling the generator change forward. No scope creep or rework needed.

## Next Phase Readiness
- Ready for Wave 2: Signal chain simplification (list[str] instead of SignalChainPosition)
- Tests for scene wiring through ControllerConfig are all migrated to direct scenes field
