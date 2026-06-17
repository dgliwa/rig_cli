---
phase: 24-close-v1-4-gaps-phase-21-verification-mc6-preset-typing-qual
plan: "01"
subsystem: engine
tags: [pydantic, strenum, protocol, typing, plugin-boundary]

# Dependency graph
requires:
  - phase: 21-concrete-types-plugin-boundary
    provides: concrete config types and Preset Protocol in plugin boundary
  - phase: 20-quick-wins-dead-code
    provides: DeviceType StrEnum, QUAL-01 baseline
provides:
  - ActionStatus StrEnum for DeviceAction.status
  - DeviceAction fully enum-typed (device_type: DeviceType, status: ActionStatus)
  - MC6Device.presets: SkipValidation[list[Preset]] — no more list[Any]
  - Phase 21 VERIFICATION.md with live evidence
  - TYPE-02 and TYPE-03 marked Complete in REQUIREMENTS.md
affects: [phase-25-onwards, any consumer of DeviceAction construction]

# Tech tracking
tech-stack:
  added: [SkipValidation (pydantic.functional_validators)]
  patterns:
    - ActionStatus(StrEnum) parallel to DeviceType(StrEnum) in engine/plan/models.py
    - SkipValidation[list[Protocol]] for Pydantic-compatible Protocol-typed fields

key-files:
  created:
    - .planning/phases/21-concrete-types-plugin-boundary/21-01-VERIFICATION.md
  modified:
    - packages/rig/src/rig/engine/plan/models.py
    - packages/rig-morningstar/src/rig_morningstar/device.py
    - packages/rig/src/rig/engine/plan/compute.py
    - packages/rig/src/rig/engine/apply.py
    - packages/rig/src/rig/cli/commands/plan.py
    - packages/rig/tests/test_devices.py
    - packages/rig/tests/test_plugin.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "ActionStatus(StrEnum) placed in engine/plan/models.py alongside DeviceAction — not in engine/plugin.py"
  - "MC6Device.presets uses SkipValidation[list[Preset]] because Pydantic cannot validate list[Protocol] at runtime; SkipValidation preserves the typed annotation for static analysis"
  - "Pydantic StrEnum fields serialize to their .value in JSON automatically — no custom serializer needed; DeviceAction JSON output unchanged"

patterns-established:
  - "SkipValidation[list[Protocol]] pattern for Pydantic models that need Protocol-typed list fields"
  - "All DeviceAction construction uses enum members; raw string literals banned at call sites"

requirements-completed: [TYPE-02, TYPE-03, QUAL-01]

# Metrics
duration: 25min
completed: 2026-06-16
---

# Phase 24: Close v1.4 Gaps (Phase 21 Verification, MC6 Preset Typing, QUAL-01 DeviceAction) Summary

**ActionStatus StrEnum added; DeviceAction fully enum-typed; MC6Device.presets changed from list[Any] to SkipValidation[list[Preset]]; Phase 21 VERIFICATION.md written with live evidence; TYPE-02/TYPE-03 marked Complete**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-16T00:00:00Z
- **Completed:** 2026-06-16
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added `ActionStatus(StrEnum)` with `CONFIGURE`, `VERIFY`, `ANALOG` members to `engine/plan/models.py`
- Retyped `DeviceAction.device_type: str` → `DeviceType` and `DeviceAction.status: Literal[...]` → `ActionStatus`
- Changed `MC6Device.presets: list[Any]` → `SkipValidation[list[Preset]]` — satisfies TYPE-03, no more `list[Any]`
- Updated all 4 DeviceAction construction sites (3 in compute.py, 1 in apply.py) to use enum members
- Updated CLI plan.py status comparisons to use `ActionStatus.CONFIGURE/VERIFY`
- Written Phase 21 VERIFICATION.md with live grep evidence confirming all 4 success criteria pass
- Marked TYPE-02 and TYPE-03 as `[x]` complete in REQUIREMENTS.md checklist and Traceability table
- Updated test_plugin.py to include MC6Device in the "no list[Any]" regression test

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ActionStatus StrEnum; retype DeviceAction and MC6Device.presets** - `8ffdbd7` (feat)
2. **Task 2: Use ActionStatus and DeviceType enum members at all construction sites** - `64d4e2b` (refactor)
3. **Task 3: Write Phase 21 VERIFICATION.md; mark TYPE-02/TYPE-03 complete** - `2ee70ee` (docs)

## Files Created/Modified

- `packages/rig/src/rig/engine/plan/models.py` — Added `ActionStatus(StrEnum)`; retyped `DeviceAction.device_type: DeviceType`, `status: ActionStatus`
- `packages/rig-morningstar/src/rig_morningstar/device.py` — Changed `presets: list[Any]` → `SkipValidation[list[Preset]]`; added `Preset` and `SkipValidation` imports
- `packages/rig/src/rig/engine/plan/compute.py` — Updated 3 DeviceAction construction sites to use enum members; imported `ActionStatus`
- `packages/rig/src/rig/engine/apply.py` — Updated controller action construction to use `DeviceType.CONTROLLER` and `ActionStatus.CONFIGURE`
- `packages/rig/src/rig/cli/commands/plan.py` — Imported `ActionStatus`; use enum comparisons instead of raw strings
- `packages/rig/tests/test_devices.py` — Updated DeviceAction construction in test helper to use enum members
- `packages/rig/tests/test_plugin.py` — Updated "no list[Any]" test to include MC6Device; updated docstring
- `.planning/phases/21-concrete-types-plugin-boundary/21-01-VERIFICATION.md` — Written with live evidence for all 4 Phase 21 success criteria
- `.planning/REQUIREMENTS.md` — TYPE-02 and TYPE-03 marked `[x]` complete; Traceability table updated

## Decisions Made

- **SkipValidation for MC6Device.presets**: Pydantic cannot build a validator for `list[Preset]` when `Preset` is a non-`runtime_checkable` Protocol (raises `SchemaError: 'cls' must be valid as the first argument to 'isinstance'`). `SkipValidation[list[Preset]]` from `pydantic.functional_validators` preserves the typed annotation visible to mypy/pyright while bypassing Pydantic's runtime isinstance check. This is the correct pattern for Pydantic models with Protocol-typed list fields.
- **ActionStatus in models.py**: `ActionStatus` lives alongside `DeviceAction` in `engine/plan/models.py`, not in `engine/plugin.py` — the plugin module is for the Device protocol and apply-time contracts; plan models are a separate concern.
- **Comparison sites in plan.py**: Updated `action.status == "configure"` comparisons to `action.status == ActionStatus.CONFIGURE` for consistency. StrEnum preserves string equality so these were not broken, but explicit enum usage is cleaner.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_plugin.py test excluded MC6Device from the "no list[Any]" regression test**
- **Found during:** Task 3 (gathering grep evidence)
- **Issue:** The test `test_all_plugin_devices_satisfy_preset_field_is_not_list_any` had a comment saying "MC6Device is excluded — it has no real presets and retains list[Any] intentionally" and explicitly excluded MC6Device from the loop. After Task 1, MC6Device now uses `SkipValidation[list[Preset]]` which passes the `"Any" not in str(ann)` check.
- **Fix:** Updated the test to include MC6Device in the loop; updated the docstring to reflect the SkipValidation approach.
- **Files modified:** `packages/rig/tests/test_plugin.py`
- **Verification:** `uv run pytest packages/rig/tests/test_plugin.py -q` — 33 passed

---

**Total deviations:** 1 auto-fixed (Rule 1 - existing test comment/exclusion no longer accurate after MC6 typing fix)
**Impact on plan:** Minor test cleanup; no scope creep. The test now correctly validates the new annotation.

## Issues Encountered

- Pydantic cannot validate `list[Preset]` when `Preset` is a Protocol (not `@runtime_checkable`). This required `SkipValidation[list[Preset]]` rather than a plain `list[Preset]` field annotation. The context document (D-01) did not anticipate this constraint, but the fix is clean and idiomatic.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TYPE-02, TYPE-03, and QUAL-01 are now Complete
- `DeviceAction` is fully typed with enums — no raw strings at any construction or comparison site
- MC6Device satisfies the `Device` Protocol's `presets: list[Preset]` requirement
- Phase 21 VERIFICATION.md written — v1.4 gap closed
- All 309 tests passing — ready for next phase
