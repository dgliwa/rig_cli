---
phase: 04-plugin-migration
plan: P3
subsystem: engine/loader
tags: [plugin-architecture, registry-dispatch, device-protocol, applier-cleanup]
dependency_graph:
  requires:
    - phase: P1
      provides: Device Protocol, DeviceApplyContext, PluginRegistry.register_model
    - phase: P2
      provides: AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device, default_registry
  provides:
    - Registry-driven device YAML dispatch in loader.py
    - apply.py routes scene/MC6 actions through device.apply(DeviceApplyContext)
    - No direct applier imports remain in apply.py
    - appliers/ contains only base.py and chase_bliss.py
  affects:
    - Phase 5 (plan/diff implementations use the Device Protocol)
    - Any new device type only needs plugin registration — no core changes
tech_stack:
  added: []
  patterns:
    - Registry-driven YAML dispatch (loader calls get_registry().get_model(config_type))
    - Device Protocol routing in apply loop (device.apply(DeviceApplyContext))
    - extra="allow" on Pydantic models for backward-compatible extra fields
key_files:
  created: []
  modified:
    - src/rig/config/loader.py
    - src/rig/engine/apply.py
    - src/rig/engine/devices.py
    - src/rig/models/rig.py
    - src/rig/engine/appliers/__init__.py
    - src/rig/engine/appliers/chase_bliss.py
    - tests/test_loader.py
    - tests/test_apply.py
    - tests/test_appliers.py
  deleted:
    - src/rig/engine/appliers/analog.py
    - src/rig/engine/appliers/midi_device.py
    - src/rig/engine/appliers/mc6.py
    - src/rig/engine/appliers/registry.py
key-decisions:
  - "Use Device(**data) as intermediate parse step in _parse_device() to get typed config objects before constructing the concrete plugin type — avoids duplicating the discriminated union logic"
  - "Add extra='allow' to concrete device types so they accept the full YAML structure (manufacturer, model, type, presets) without losing those attributes"
  - "Make name field optional with default '' on concrete types since device YAML has manufacturer+model but no name field"
  - "Add explicit type: DeviceType field to concrete types to avoid .type.value AttributeError in compute.py"
  - "Add get_scene_pc_command() to all four concrete types so mc6_presets.py generator continues to work"
  - "Change Rig.devices to dict[str, Any] with arbitrary_types_allowed so concrete plugin types can coexist with legacy Device objects"
  - "Graceful skip in apply.py for devices without apply() — backward compat for tests that pass old Device objects without rig= arg"
  - "MC6 programming phase constructs a sentinel DeviceAction for mc6_device.apply(mc6_ctx)"
patterns-established:
  - "Registry dispatch: loader reads config.type from YAML, calls get_registry().get_model(config_type) to find concrete class, constructs via model_class(**data)"
  - "Device-as-Protocol in apply loop: construct DeviceApplyContext from ApplyContext fields, call device.apply(device_ctx)"
requirements-completed: []
duration: ~35min
completed: "2026-06-05"
---

# Phase 4 Plan P3: Wire Plugin Architecture End-to-End Summary

**Plugin migration complete: loader.py dispatches via registry, apply.py routes through device.apply(DeviceApplyContext), old applier files deleted — adding a new device type now requires only plugin registration.**

## Performance

- **Duration:** ~35 minutes
- **Started:** 2026-06-05
- **Completed:** 2026-06-05
- **Tasks:** 3 (T1 TDD, T2 TDD, T3 auto)
- **Files modified:** 9 files modified, 4 files deleted

## Accomplishments

- loader.py produces concrete device plugin types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) via registry-driven dispatch
- apply.py routes scene actions through `device.apply(DeviceApplyContext)` — no `get_scene_applier` calls remain
- MC6 programming phase calls `mc6_device.apply(mc6_ctx)` — no `get_mc6_applier` calls remain
- CBA 3-phase setup kept in ChaseBlissApplier.apply_setup (migration deferred per CONTEXT.md)
- Four applier files deleted: analog.py, midi_device.py, mc6.py, registry.py
- 238 tests passing (no regressions from pre-P3 baseline of 246 minus the 8 deleted AnalogApplier/MidiApplier test cases)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for registry-driven loader dispatch** - `2af779c` (test)
2. **Task 1 GREEN: Registry-driven loader dispatch + concrete device types** - `0f1b2de` (feat)
3. **Task 2 RED: Failing tests for device.apply() routing** - `9ef8c4c` (test)
4. **Task 2 GREEN: Route apply.py through device.apply(ctx)** - `df182c9` (feat)
5. **Task 3: Delete superseded appliers, update chase_bliss and test_appliers** - `3372389` (refactor)

_Note: TDD tasks have RED/GREEN commits._

## Files Created/Modified

- `src/rig/config/loader.py` — registry dispatch via get_registry().get_model(config_type); Device(**data) as parse intermediary
- `src/rig/engine/apply.py` — scene loop via device.apply(DeviceApplyContext); MC6 via mc6_device.apply; no registry imports
- `src/rig/engine/devices.py` — extra="allow", optional name, explicit type/presets fields, get_scene_pc_command() on all types
- `src/rig/models/rig.py` — devices: dict[str, Any] with arbitrary_types_allowed
- `src/rig/engine/appliers/__init__.py` — stripped to base exports only
- `src/rig/engine/appliers/chase_bliss.py` — removed MidiApplier dependency and apply_scene method; apply_setup retained
- `tests/test_loader.py` — added TestRegistryDispatch (6 new tests verifying concrete type instances)
- `tests/test_apply.py` — updated _make_config() to use MidiDevice/ChaseBlissDevice; added TestDevicePluginRouting
- `tests/test_appliers.py` — removed AnalogApplier/MidiApplier tests; kept ChaseBlissApplier setup tests

### Deleted

- `src/rig/engine/appliers/analog.py` — logic migrated to AnalogDevice.apply()
- `src/rig/engine/appliers/midi_device.py` — logic migrated to MidiDevice.apply()
- `src/rig/engine/appliers/mc6.py` — logic migrated to MC6Device.apply()
- `src/rig/engine/appliers/registry.py` — superseded by plugin_registry.py + default_registry

## Decisions Made

- **Typed config via Device intermediary:** `_parse_device()` calls `Device(**data)` first to get a typed config (using Pydantic's discriminated union), then constructs `model_class(**{...data, "config": temp.config})`. This avoids duplicating the ManualConfig/MidiConfig/ChaseBlissConfig/ControllerConfig parsing logic.
- **`extra="allow"` on concrete types:** All four concrete types use `ConfigDict(arbitrary_types_allowed=True, extra="allow")` so they accept the full device YAML (manufacturer, model, type, presets) without losing those attributes. The `type` field is explicit (DeviceType enum) to preserve `.type.value` semantics used in compute.py.
- **`get_scene_pc_command()` added to all types:** The MC6 generator (`mc6_presets.py`) calls this method on devices. Adding it to concrete types preserves backward compat without modifying the generator. Rule 2 deviation (missing critical functionality).
- **`Rig.devices: dict[str, Any]`:** The type was changed from `dict[str, Device]` to `dict[str, Any]` to accommodate concrete plugin types without a Pydantic validation error. Pydantic's `arbitrary_types_allowed=True` also added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added get_scene_pc_command() to concrete device types**
- **Found during:** Task 1 (GREEN phase — full test suite run)
- **Issue:** `mc6_presets.py` generator and `MC6Device.apply()` call `device.get_scene_pc_command()` — the old Device model has this method but the new concrete types didn't, causing 3 failures in test_catalog.py
- **Fix:** Added `get_scene_pc_command()` to AnalogDevice (returns None), MidiDevice (full lookup), ChaseBlissDevice (same as MidiDevice), and MC6Device (returns None)
- **Files modified:** src/rig/engine/devices.py
- **Verification:** uv run pytest tests/test_catalog.py — 3 previously failing tests now pass
- **Committed in:** 0f1b2de (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] Added explicit type: DeviceType field to concrete types**
- **Found during:** Task 1 (investigation of compute.py compatibility)
- **Issue:** compute.py calls `pedal.type.value` (expecting DeviceType enum); with `extra="allow"`, `type` is stored as a raw string which has no `.value` attribute
- **Fix:** Added explicit `type: DeviceType` field to all four concrete types with appropriate defaults; Pydantic auto-coerces YAML strings to the enum
- **Files modified:** src/rig/engine/devices.py
- **Verification:** compute_plan() works correctly with concrete device types
- **Committed in:** 0f1b2de (Task 1 GREEN commit)

**3. [Rule 3 - Blocking] Updated test_apply.py to pass rig= for device resolution**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** `test_apply_writes_state` didn't pass `rig=` arg; after routing change, devices are resolved from `rig.devices` — without rig, all devices skip
- **Fix:** Added `rig=config` to the test call
- **Files modified:** tests/test_apply.py
- **Verification:** All TestApplyPlan tests pass
- **Committed in:** df182c9 (Task 2 GREEN commit)

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

None — all issues resolved via deviation rules above.

## Known Stubs

None — all device types execute real apply logic; no placeholder data flows to output.

## TDD Gate Compliance

**Task 1 (TDD):**
1. RED gate commit: `2af779c` — `test(04-P3): add failing tests for registry-driven loader dispatch`
2. GREEN gate commit: `0f1b2de` — `feat(04-P3): registry-driven loader dispatch and concrete device types`

**Task 2 (TDD):**
1. RED gate commit: `9ef8c4c` — `test(04-P3): add failing tests for device.apply() routing in apply.py`
2. GREEN gate commit: `df182c9` — `feat(04-P3): route apply.py through device.apply(ctx), remove registry imports`

Both TDD gate pairs satisfied.

## Next Phase Readiness

- Plugin architecture wired end-to-end: loader → concrete types, apply.py → device.apply()
- Phase 5 can now implement plan() and diff() on concrete device types; replace `raise NotImplementedError` with real implementations
- New device types require only: create Pydantic model + register in default_registry; no core changes

---
*Phase: 04-plugin-migration*
*Completed: 2026-06-05*
