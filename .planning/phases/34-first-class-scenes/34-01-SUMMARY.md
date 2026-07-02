---
phase: 34-first-class-scenes
plan: "01"
subsystem: models
tags: [pydantic, scenes, rig-model, loader, mc6-config, schema-migration]

requires:
  - phase: 33-apply-completions
    provides: stable apply engine this phase builds upon

provides:
  - "Rig.scenes as a first-class Pydantic field (dict[str, Scene] = {})"
  - "Loader reads top-level scenes: key from rig.yaml into Rig.scenes"
  - "MC6Config hard cutover — no scenes field, extra=forbid, stale key raises ConfigError"
  - "All fixtures and test builders migrated to top-level / Rig(scenes=...) pattern"
  - "Scene.tempo preserved through loader round-trip"

affects: [34-02, mc6-apply, compute_plan, compute_diff, sample_rig]

tech-stack:
  added: []
  patterns:
    - "Scenes are a top-level rig.yaml key — not nested under any device config"
    - "Device configs use extra='forbid' to surface stale keys as clean ConfigErrors"
    - "_parse_device wraps pydantic.ValidationError in rig.config.errors.ValidationError for user-friendly messages"

key-files:
  created: []
  modified:
    - "packages/rig/src/rig/models/rig.py — scenes @property replaced with scenes: dict[str, Scene] = {} field"
    - "packages/rig/src/rig/config/loader.py — reads top-level scenes:, wraps pydantic.ValidationError, updated docstring"
    - "packages/rig-morningstar/src/rig_morningstar/config.py — MC6Config: removed scenes, added midi_channel, extra=forbid"
    - "packages/rig/tests/fixtures/sample_rig/rig.yaml — migrated scenes to top-level"
    - "packages/rig/tests/test_models.py — new Pydantic field tests, removed old property tests"
    - "packages/rig/tests/test_loader.py — BASE_RIG_YAML migrated, new TestTopLevelScenes tests"
    - "packages/rig/tests/test_plan.py — all builder helpers migrated to Rig(scenes=...)"
    - "packages/rig/tests/test_apply.py — all inline rig builds migrated"
    - "packages/rig/tests/test_appliers.py — inline rig build migrated"
    - "packages/rig/tests/test_diff.py — _make_rig migrated"
    - "packages/rig/tests/test_cli_plan.py — all _write_*_rig helpers migrated"
    - "packages/rig-morningstar/tests/test_mc6_device.py — new MC6Config cutover tests"

key-decisions:
  - "Hard cutover (D-01): no fallback — scenes under controller config now raises ConfigError immediately"
  - "MC6Config gets explicit midi_channel field (not stripped by extra=forbid) since rig.yaml includes it"
  - "Plain-dict ordering sufficient for scenes — no OrderedDict needed (CONTEXT.md Claude's Discretion)"

patterns-established:
  - "Scenes as top-level Pydantic field: domain model owns scenes directly, not aggregated from devices"
  - "Loader pydantic.ValidationError wrapping: all plugin parse errors surface as clean ConfigError"
  - "extra=forbid on device configs: stale keys caught at load time with readable errors"

requirements-completed: [SCENE-01, D-01, D-02, D-03, D-04]

coverage:
  - id: D1
    description: "Rig.scenes is a real Pydantic field in Rig.model_fields"
    requirement: "SCENE-01"
    verification:
      - kind: unit
        ref: "packages/rig/tests/test_models.py#TestRigConfig::test_rig_scenes_is_pydantic_field"
        status: pass
      - kind: unit
        ref: "packages/rig/tests/test_models.py#TestRigConfig::test_rig_scenes_constructor_accepts_scene_dict"
        status: pass
      - kind: unit
        ref: "packages/rig/tests/test_models.py#TestRigConfig::test_rig_scenes_empty_by_default"
        status: pass
    human_judgment: false
  - id: D2
    description: "MC6Config has no scenes field and rejects stale scenes: key with extra=forbid"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "packages/rig-morningstar/tests/test_mc6_device.py#test_mc6_config_has_no_scenes_field"
        status: pass
      - kind: unit
        ref: "packages/rig-morningstar/tests/test_mc6_device.py#test_mc6_config_rejects_scenes_key"
        status: pass
    human_judgment: false
  - id: D3
    description: "Loader reads top-level scenes: key and populates Rig.scenes with Scene.tempo preserved"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "packages/rig/tests/test_loader.py#TestLoadRig::test_loads_scenes_from_top_level"
        status: pass
      - kind: unit
        ref: "packages/rig/tests/test_loader.py#TestTopLevelScenes::test_loader_preserves_scene_tempo"
        status: pass
    human_judgment: false
  - id: D4
    description: "Stale scenes: under controller config raises ConfigError (not raw pydantic traceback)"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "packages/rig/tests/test_loader.py#TestTopLevelScenes::test_loader_rejects_scenes_in_controller_config"
        status: pass
    human_judgment: false
  - id: D5
    description: "All fixtures and test builders express scenes at top-level / via Rig(scenes=...)"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "make test — 406 tests green, no SimpleNamespace(scenes=...) on controller configs"
        status: pass
    human_judgment: false

duration: 37min
completed: "2026-07-02"
status: complete
---

# Phase 34 Plan 01: Core model + schema migration Summary

**Rig.scenes promoted to a first-class Pydantic field populated by the loader from a top-level rig.yaml scenes: key; MC6Config hard cutover removes scenes, adds extra=forbid**

## Performance

- **Duration:** 37 min
- **Started:** 2026-07-02T03:39:41Z
- **Completed:** 2026-07-02T04:17:10Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- Replaced `Rig.scenes` `@property` aggregating from controller devices with a real `dict[str, Scene] = {}` Pydantic field
- Implemented loader to read `data['scenes']` from top-level rig.yaml, constructing `Scene` objects with `tempo` preserved
- Removed `scenes` field from `MC6Config`, changed `extra="ignore"` to `extra="forbid"` — stale `scenes:` key under controller config now surfaces as a clean `ConfigError` via `_parse_device` wrapping
- Added `midi_channel` as explicit field on `MC6Config` (required because rig.yaml includes it and `extra="forbid"` rejects unknown keys)
- Migrated all fixtures and test builders across 8 test files — no `SimpleNamespace(scenes=...)` remains on any controller config
- All 406 tests pass (7 additional tests added)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Wave-0 tests for Rig.scenes and MC6Config cutover** - `e342a86` (test)
2. **Task 1 GREEN: Promote Rig.scenes to real field, MC6Config hard cutover** - `b239418` (feat)
3. **Task 2 RED: Add RED tests for top-level scene loading** - `ff6f16e` (test)
4. **Task 2 GREEN: Loader reads top-level scenes, wraps pydantic ValidationError** - `38a6659` (feat)
5. **Task 3: Migrate fixtures and test builders to top-level scenes schema** - `a410add` (refactor)

_TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified

- `packages/rig/src/rig/models/rig.py` — removed `scenes` `@property`, added `scenes: dict[str, Scene] = {}` field
- `packages/rig/src/rig/config/loader.py` — top-level scene parsing, `pydantic.ValidationError` wrapping, updated docstring
- `packages/rig-morningstar/src/rig_morningstar/config.py` — removed `scenes` field, added `midi_channel` field, `extra="forbid"`
- `packages/rig/tests/fixtures/sample_rig/rig.yaml` — scenes moved to top level
- `packages/rig/tests/test_models.py` — new field tests, removed old property tests
- `packages/rig/tests/test_loader.py` — `BASE_RIG_YAML` migrated, `TestTopLevelScenes` class added
- `packages/rig/tests/test_plan.py` — all helpers migrated
- `packages/rig/tests/test_apply.py` — all inline rig builds migrated
- `packages/rig/tests/test_appliers.py` — inline rig build migrated
- `packages/rig/tests/test_diff.py` — `_make_rig` migrated
- `packages/rig/tests/test_cli_plan.py` — all `_write_*_rig` helpers migrated
- `packages/rig-morningstar/tests/test_mc6_device.py` — new MC6Config cutover tests

## Decisions Made

- **Hard cutover (D-01):** No fallback — scenes under controller config raises ConfigError immediately. Chosen because gradual migration would leave the codebase in a partial state.
- **MC6Config gets explicit `midi_channel` field:** `extra="forbid"` requires all YAML keys to be declared as fields. The fixture YAML had `midi_channel: 1` under mc6 config, so this had to be added as a proper field rather than removing it from YAML.
- **Plain-dict ordering sufficient:** No `OrderedDict` needed for `scenes` field (per CONTEXT.md Claude's Discretion).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `midi_channel` field to `MC6Config`**
- **Found during:** Task 2 (loader tests failing after `extra="forbid"` change)
- **Issue:** `MC6Config` had `extra="forbid"` but the fixture and test YAMLs include `midi_channel: 1` under the controller config. This caused `pydantic.ValidationError` for a legitimate field (not a stale key).
- **Fix:** Added `midi_channel: int | None = None` as explicit field on `MC6Config`
- **Files modified:** `packages/rig-morningstar/src/rig_morningstar/config.py`
- **Verification:** All MC6 device tests pass
- **Committed in:** `ff6f16e` (part of Task 2 RED commit)

**2. [Rule 2 - Missing Critical] Migrated additional test files not in plan's Task 3 list**
- **Found during:** Task 3 (`make test` revealed 22 failures in test_appliers, test_diff, test_cli_plan)
- **Issue:** `test_appliers.py`, `test_diff.py`, and `test_cli_plan.py` contained inline rig builds and YAML helpers using the old `scenes:` under controller config pattern. Not listed in plan's Task 3 file list.
- **Fix:** Migrated all inline rig builds and YAML helpers in these 3 files to the top-level scenes schema
- **Files modified:** `test_appliers.py`, `test_diff.py`, `test_cli_plan.py`
- **Verification:** `make test` passes (406 tests)
- **Committed in:** `a410add` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing critical)
**Impact on plan:** Both auto-fixes were necessary for correctness. No scope creep.

## Issues Encountered

None beyond the two deviations documented above.

## Next Phase Readiness

- `Rig.scenes` is a first-class field, enabling phase 34-02 (controller-less apply) to be built cleanly
- `Scene.tempo` survives loader round-trip (ready for tempo-aware features)
- All cross-reference validation (`_validate_references`) works transparently with the new field
- `MC6Config.extra="forbid"` enforces the new schema boundary at load time

## Self-Check: PASSED

All commits verified in git log:
- `e342a86` — test(34-01): add RED tests for Rig.scenes field and MC6Config cutover
- `b239418` — feat(34-01): promote Rig.scenes to real field, MC6Config hard cutover
- `ff6f16e` — test(34-01): add RED tests for top-level scene loading
- `38a6659` — feat(34-01): loader reads top-level scenes, wraps pydantic ValidationError
- `a410add` — refactor(34-01): migrate fixtures and test builders to top-level scenes schema

All 406 tests pass: `make test` green.

---
*Phase: 34-first-class-scenes*
*Completed: 2026-07-02*
