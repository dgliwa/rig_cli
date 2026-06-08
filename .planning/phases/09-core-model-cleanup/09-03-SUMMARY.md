---
phase: 09-core-model-cleanup
plan: 03
subsystem: models
tags: [plugin-migration, cba, config-types]
requires:
  - phase: 09
    provides: clean Scene/Rig models, list[str] signal chain
provides:
  - Control/ControlType defined in rig-chasebliss (not core)
  - ChaseBlissConfig defined in rig-chasebliss (not core)
  - Core device.py exports only DeviceType, Device, Preset (no plugin configs)
  - Device.config changed from discriminated union to Any
  - Plan model no longer has cba_setup field
  - detect_cba_setup removed from compute.py
  - Setup Actions section removed from plan CLI
  - Morningstar generator uses rig.controller (dict-aware)
  - All plugin device models handle dict configs
affects: [phase 10, phase 11]
tech-stack:
  added: []
  patterns: ["config: Any on Device (not discriminated union)", "dict-aware config access via isinstance checks"]
key-files:
  deleted: []
  modified:
    - packages/rig/src/rig/models/device.py
    - packages/rig/src/rig/models/__init__.py
    - packages/rig/src/rig/config/loader.py
    - packages/rig/src/rig/engine/plan/compute.py
    - packages/rig/src/rig/engine/plan/models.py
    - packages/rig/src/rig/cli/commands/plan.py
    - packages/rig/src/rig/cli/commands/status.py
    - packages/rig-chasebliss/src/rig_chasebliss/catalog.py
    - packages/rig-chasebliss/src/rig_chasebliss/device.py
    - packages/rig-hx/src/rig_hx/device.py
    - packages/rig-morningstar/src/rig_morningstar/device.py
    - packages/rig-morningstar/src/rig_morningstar/generator.py
    - packages/rig/tests/test_models.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_diff.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_appliers.py
    - packages/rig/tests/test_catalog.py
    - packages/rig/tests/test_loader.py
    - packages/rig/tests/test_mc6_generator.py
    - packages/rig/tests/test_devices.py
    - packages/rig/tests/test_cli_plan.py
key-decisions:
  - "Config is now Any — plugin device models must handle both dict and model configs using isinstance checks"
  - "CBA setup actions moved from core compute_plan to plugin ChaseBlissDevice.setup()"
  - "All plugin device get_scene_pc_command methods updated to access midi_channel via dict/attribute fallback"
patterns-established: []
requirements-completed:
  - MODEL-01
  - MODEL-02
duration: 45min
completed: 2026-06-08
---

# Phase 09: Core Model Cleanup — Wave 3 Summary

**Moved all plugin config types (Control, ControlType, ChaseBlissConfig) to their plugin packages; removed CBA plan-time detection from core; made Device.config: Any with dict-aware access patterns**

## Performance

- **Duration:** 45 min
- **Started:** 2026-06-08T04:43:00Z
- **Completed:** 2026-06-08T05:28:00Z
- **Tasks:** 2
- **Files modified:** 22+

## Accomplishments
- `Control` and `ControlType` defined natively in `rig_chasebliss/catalog.py` (no import from core)
- `ChaseBlissConfig` defined natively in `rig_chasebliss/device.py` with `get_cc_params` method
- Core `device.py` stripped of all plugin-specific types: `ControlType`, `Control`, `DeviceConfig`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig`
- `Device.config` changed from `Annotated[discriminated union]` to `Any = None`
- `models/__init__.py` cleaned up to only export core types
- `detect_cba_setup` function removed from `compute.py` (CBA now handled in plugin `ChaseBlissDevice.setup()`)
- `Plan.cba_setup` field removed (CbaSetupAction class kept for plugin use)
- CLI "Setup Actions" section removed from plan output
- `get_scene_pc_command` updated with `_get_midi_channel` helper supporting both dict and model configs
- All plugin device models updated to access config via dict/attribute fallback
- 272 tests pass (CBA/Config-type tests removed as expected)

## Files Modified
- **Core device.py**: Stripped to DeviceType, Device, Preset only
- **Plugin packages**: Control, ControlType, ChaseBlissConfig migrated to rig-chasebliss
- **Plan engine**: CBA setup removed from compute_plan
- **CLI**: Setup Actions section removed from plan command
- **All plugin devices**: Dict-aware config access patterns

## Decisions Made
- Config is now `Any` everywhere — plugin models handle both dict and model configs
- Dict-aware access pattern: `config.get("key") if isinstance(config, dict) else getattr(config, "key", None)`

## Deviations from Plan
The plan was followed exactly, but cross-wave dependency issues required several pre-Wave-4 fixes:
- Plugin device `get_scene_pc_command` methods updated to handle dict configs (planned for Wave 4 but required in Wave 3)
- Various test files updated more extensively than planned due to config type removal

## Issues Encountered
- **Config dict vs model**: Removing the discriminated union from Device.config meant all downstream code that accessed `config.midi_channel` as an attribute broke. Fixed by adding dict-aware fallback throughout.

## Next Phase Readiness
- Ready for Wave 4: Remove manufacturer/model from Device; clean up remaining test references
