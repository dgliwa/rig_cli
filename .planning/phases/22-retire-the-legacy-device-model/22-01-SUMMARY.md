---
phase: 22-retire-the-legacy-device-model
plan: 01
subsystem: models
tags: [pydantic, protocol, device, refactor, migration]

# Dependency graph
requires:
  - phase: 21-concrete-types-plugin-boundary
    provides: concrete device plugin types (HXStompDevice, ChaseBlissDevice, AnalogDevice)
provides:
  - Single Device type surface (Device Protocol in rig.engine.plugin, not BaseModel in models/)
  - DeviceType StrEnum in rig.engine.plugin as canonical home
  - FakeDevice dataclass in packages/rig/tests/conftest.py for structural test substitution
  - Rig.devices typed as dict[str, Device] (Device Protocol)
  - Zero hasattr guards in engine code
affects: [future phases consuming Rig.devices, tests that construct Device-like objects]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@runtime_checkable Protocol for Pydantic field typing — allows isinstance() validation against Protocol classes"
    - "SimpleNamespace for controller config in tests — satisfies getattr(cfg, 'scenes', {}) pattern"
    - "FakeDevice dataclass in conftest.py — structural Protocol satisfier for unit tests"

key-files:
  created:
    - packages/rig/tests/conftest.py
  modified:
    - packages/rig/src/rig/engine/plugin.py
    - packages/rig/src/rig/models/rig.py
    - packages/rig/tests/test_models.py
    - packages/rig/tests/test_plan.py
    - packages/rig/tests/test_diff.py
    - packages/rig/tests/test_graph.py
    - packages/rig/tests/test_catalog.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_appliers.py
    - packages/rig/tests/test_loader.py
    - packages/rig-chasebliss/tests/test_applier.py
  deleted:
    - packages/rig/src/rig/models/device.py

key-decisions:
  - "Added @runtime_checkable to Device Protocol so Pydantic v2 can build isinstance validator for dict[str, Device] fields"
  - "FakeDevice imports explicitly in each test file via from tests.conftest import FakeDevice — conftest auto-discovery only applies to pytest fixtures, not class constructors"
  - "test_catalog.py TestGetScenePcCommand uses HXStompDevice/ChaseBlissDevice (concrete types) because FakeDevice.get_scene_pc_command() always returns None"
  - "rig-chasebliss/tests/test_applier.py _FakeDevice extended with setup/apply/get_scene_pc_command/from_raw_yaml to satisfy Device Protocol for isinstance check"

patterns-established:
  - "All Device consumers import from rig.engine.plugin, not rig.models.device"
  - "Controller configs in tests use SimpleNamespace(scenes=..., type=...) to satisfy getattr pattern"
  - "FakeDevice is the canonical test double for the Device Protocol when concrete behavior is not needed"

requirements-completed:
  - TYPE-01

# Metrics
duration: 35min
completed: 2026-06-15
---

# Phase 22 Plan 01: Retire Legacy Device Model Summary

**Deleted `models/device.py` and unified Device type on the `Device` Protocol in `rig.engine.plugin` — zero hasattr guards, typed `Rig.devices: dict[str, Device]`, 8 test files migrated to `FakeDevice`**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-15T00:00:00Z
- **Completed:** 2026-06-15T00:35:00Z
- **Tasks:** 2 (Task 1 was committed by prior executor; Task 2 executed in this session)
- **Files modified:** 14

## Accomplishments

- Deleted `packages/rig/src/rig/models/device.py` — the legacy `Device(BaseModel)` no longer exists
- `Rig.devices` is now `dict[str, Device]` with `Device` imported from `rig.engine.plugin`
- All 8 test files migrated from `Device(BaseModel)` to `FakeDevice` dataclass with `SimpleNamespace` for controller configs
- Zero hasattr guards remain in `packages/rig/src/rig/engine/apply.py`
- `DeviceType` StrEnum lives exclusively in `rig.engine.plugin`
- 306 tests pass; only the 3 pre-existing stdin-capture failures remain

## Task Commits

1. **Task 1: Add DeviceType to plugin.py; update all non-test importers** - `3d82d8d` (refactor)
2. **Task 2: Remove hasattr guards, FakeDevice, migrate tests, delete device.py** - `b4203c0` (refactor)

## Files Created/Modified

- `packages/rig/tests/conftest.py` — New: FakeDevice dataclass satisfying Device Protocol
- `packages/rig/src/rig/engine/plugin.py` — Added `@runtime_checkable` to Device Protocol; added `DeviceType` StrEnum
- `packages/rig/src/rig/models/rig.py` — `devices: dict[str, Device]`; Device imported unconditionally from plugin
- `packages/rig/src/rig/models/device.py` — DELETED
- `packages/rig/tests/test_models.py` — Migrated to FakeDevice; SimpleNamespace for controller config
- `packages/rig/tests/test_plan.py` — Migrated to FakeDevice; SimpleNamespace for controller config
- `packages/rig/tests/test_diff.py` — Migrated to FakeDevice; SimpleNamespace for controller config
- `packages/rig/tests/test_graph.py` — Migrated to FakeDevice
- `packages/rig/tests/test_catalog.py` — Migrated; kept HXStompDevice/ChaseBlissDevice for PC command tests
- `packages/rig/tests/test_apply.py` — Migrated; FakeDevice for MC6 controller only
- `packages/rig/tests/test_appliers.py` — Migrated inline import to ChaseBlissDevice + FakeDevice
- `packages/rig/tests/test_loader.py` — Updated inline import from plugin module
- `packages/rig-chasebliss/tests/test_applier.py` — Extended _FakeDevice to satisfy Device Protocol

## Decisions Made

- `@runtime_checkable` added to `Device` Protocol: Pydantic v2 builds an `isinstance` validator for `dict[str, Device]` fields. Without `@runtime_checkable`, the validator fails with `SchemaError: 'cls' must be valid as the first argument to 'isinstance'`.
- FakeDevice imports explicitly in each test file (not relying on conftest auto-discovery): pytest conftest auto-discovery only injects pytest fixtures; using `FakeDevice` as a class constructor requires explicit import.
- `test_catalog.py` `TestGetScenePcCommand` uses real `HXStompDevice`/`ChaseBlissDevice`: FakeDevice always returns `None` from `get_scene_pc_command()`, making it unsuitable for tests that assert specific PC command dicts.
- `rig-chasebliss/tests/test_applier.py` `_FakeDevice` extended: the chasebliss package has its own `_FakeDevice` that was missing `setup`, `apply`, `get_scene_pc_command`, and `from_raw_yaml` — all required by the Device Protocol for isinstance check to return True.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added @runtime_checkable to Device Protocol**
- **Found during:** Task 2 (Update rig.py to `devices: dict[str, Device]`)
- **Issue:** Pydantic v2 builds a `is-instance-of` validator for `dict[str, Device]`. Without `@runtime_checkable`, `isinstance(x, Device)` raises `TypeError: Protocols with non-method members don't support issubclass()`, causing 14 test collection errors.
- **Fix:** Added `@runtime_checkable` decorator to `class Device(Protocol)` in `plugin.py` and imported `runtime_checkable` from typing.
- **Files modified:** `packages/rig/src/rig/engine/plugin.py`
- **Verification:** `make test` passes with 306 tests
- **Committed in:** `b4203c0`

**2. [Rule 1 - Bug] Extended _FakeDevice in rig-chasebliss tests to satisfy Device Protocol**
- **Found during:** Task 2 (after adding @runtime_checkable)
- **Issue:** `rig-chasebliss/tests/test_applier.py::_FakeDevice` was missing `setup`, `apply`, `get_scene_pc_command`, and `from_raw_yaml` — causing 11 validation errors when constructing `Rig(devices={...})`.
- **Fix:** Added the four missing methods to `_FakeDevice` in that file.
- **Files modified:** `packages/rig-chasebliss/tests/test_applier.py`
- **Verification:** All 11 previously failing tests now pass
- **Committed in:** `b4203c0`

**3. [Rule 2 - Missing Critical] Explicit FakeDevice imports in each test file**
- **Found during:** Task 2 (first test run after creating conftest.py)
- **Issue:** Plan stated "FakeDevice is injected via pytest conftest.py auto-discovery — no import needed in test files." This is true for pytest fixtures but NOT for using FakeDevice as a class constructor. Test files use `FakeDevice(...)` directly, requiring an explicit import.
- **Fix:** Added `from tests.conftest import FakeDevice` to each test file that constructs FakeDevice instances.
- **Files modified:** test_models.py, test_plan.py, test_diff.py, test_graph.py, test_catalog.py, test_apply.py, test_appliers.py
- **Verification:** No NameError on collection
- **Committed in:** `b4203c0`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing critical)
**Impact on plan:** All auto-fixes necessary for the migration to work correctly with Pydantic v2 Protocol typing. No scope creep.

## Issues Encountered

- Pydantic v2 + Protocol + isinstance is subtle: `arbitrary_types_allowed=True` alone is not enough — the Protocol must be `@runtime_checkable` for Pydantic's isinstance validator to function.

## Self-Check: PASSED

Files verified:
- `packages/rig/tests/conftest.py` — exists, contains `class FakeDevice`
- `packages/rig/src/rig/models/device.py` — deleted (confirmed)
- `packages/rig/src/rig/engine/plugin.py` — contains `class DeviceType(StrEnum)` and `@runtime_checkable`
- `packages/rig/src/rig/models/rig.py` — contains `dict[str, Device]`
- Commits `3d82d8d` and `b4203c0` — present in git log

## Next Phase Readiness

- The legacy `Device(BaseModel)` is fully retired; all code uses the Device Protocol
- `Rig.devices` is strongly typed; type checkers will flag non-Protocol-satisfying objects
- Test infrastructure has a clean `FakeDevice` pattern in conftest.py for future test files
- No blockers

---
*Phase: 22-retire-the-legacy-device-model*
*Completed: 2026-06-15*
