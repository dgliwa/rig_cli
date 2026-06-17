---
phase: 23-applycontext-consolidation-test-capture-fixes
plan: 01
subsystem: engine
tags: [refactor, appliers, ports, tests, cba]

# Dependency graph
requires:
  - phase: 22-retire-the-legacy-device-model
    provides: Device Protocol, DeviceType in plugin.py
provides:
  - DeviceApplyResult, update_device_state, mark_preset_saved consolidated into rig.engine.plugin
  - appliers/base.py deleted
  - ConfirmationIO.prompt(text: str) -> str on Protocol and all implementations
  - All 4 CBA interaction functions routed through ConfirmationIO (no raw input() calls)
  - 3 previously failing stdin-capture tests fixed; make test fully green
affects: [all applier consumers, CBA interaction tests, any future plugin authors]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "prompt_cba_build_preset must accept 'confirm' not just 'c'/'done' — InMemoryPromptAdapter returns full words"
    - "TYPE_CHECKING guard for ConfirmationIO in interaction.py — avoids circular import from chasebliss → rig.engine"

key-files:
  modified:
    - packages/rig/src/rig/engine/plugin.py
    - packages/rig/src/rig/engine/apply.py
    - packages/rig/src/rig/engine/ports.py
    - packages/rig-analog/src/rig_analog/device.py
    - packages/rig-hx/src/rig_hx/device.py
    - packages/rig-morningstar/src/rig_morningstar/device.py
    - packages/rig-chasebliss/src/rig_chasebliss/applier.py
    - packages/rig-chasebliss/src/rig_chasebliss/device.py
    - packages/rig-chasebliss/src/rig_chasebliss/interaction.py
    - packages/rig/tests/conftest.py
    - packages/rig/tests/fakes.py
    - packages/rig/tests/test_apply.py
    - packages/rig/tests/test_appliers.py
    - packages/rig/tests/test_base_helpers.py
    - packages/rig-chasebliss/tests/test_applier.py
  deleted:
    - packages/rig/src/rig/engine/appliers/base.py

key-decisions:
  - "prompt_cba_build_preset response check extended to include 'confirm' — InMemoryPromptAdapter returns full-word strings, not single-char shortcuts"
  - "appliers/base.py deleted entirely; __init__.py kept for package discoverability"
  - "_patch_cba_prompts removed from test_apply.py; tests now rely on InMemoryPromptAdapter.default + side_effect queue"
  - "ApplyContext dataclass retired; apply.py now builds SetupContext and DeviceApplyContext directly"

patterns-established:
  - "All applier importers source DeviceApplyResult/helpers from rig.engine.plugin, not a separate base module"
  - "ConfirmationIO.prompt() is the single choke-point for all text-input prompts in CBA flow"
  - "InMemoryPromptAdapter is the canonical fake for all ConfirmationIO call sites"

requirements-completed:
  - TYPE-05
  - TEST-02

# Metrics
duration: ~45min
completed: 2026-06-16
---

# Phase 23 Plan 01: ApplyContext Consolidation & Test Capture Fixes — Summary

**Consolidated `DeviceApplyResult`/helpers into `plugin.py`, deleted `appliers/base.py`, threaded `ConfirmationIO` through CBA prompts, and fixed all 3 stdin-capture test failures — 309 tests now pass**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-06-16
- **Tasks:** 3
- **Files modified:** 15, deleted: 1

## Accomplishments

- `packages/rig/src/rig/engine/appliers/base.py` deleted — `DeviceApplyResult`, `update_device_state`, `mark_preset_saved` now live in `plugin.py`
- `ApplyContext` dataclass retired from `apply.py`; setup and device contexts built directly
- `ConfirmationIO` Protocol and `RichConfirmationIO` gain `prompt(text: str) -> str`
- `InMemoryPromptAdapter.prompt()` added to fakes.py
- All 4 CBA interaction functions (`prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_after_pc`, `prompt_cba_register`) accept `confirmation_io` kwarg; raw `input()` calls removed
- `_patch_cba_prompts` deleted from `test_apply.py`; all affected tests updated to use `InMemoryPromptAdapter`
- 309 tests pass; zero failures

## Task Commits

1. **Task 1: Consolidate DeviceApplyResult/helpers; retire ApplyContext** — `b11bd89`
2. **Task 2: Add prompt() to ConfirmationIO; thread through CBA interaction functions** — `8a8d26e`
3. **Task 3: Fix 3 stdin-capture test failures; delete _patch_cba_prompts** — `6b97e93`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] prompt_cba_build_preset infinite loop on "confirm" response**
- **Found during:** Task 3 (tests hung instead of passing)
- **Issue:** `prompt_cba_build_preset` checked for `("c", "done")` but not `"confirm"`. `InMemoryPromptAdapter` returns full-word strings; the while loop never matched, causing an infinite hang.
- **Fix:** Extended check to `("c", "confirm", "done")` — consistent with the other 3 interaction functions.
- **Files modified:** `packages/rig-chasebliss/src/rig_chasebliss/interaction.py`
- **Committed in:** `6b97e93`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)

## Self-Check: PASSED

- `grep -r 'from rig.engine.appliers.base' packages/` → zero hits
- `grep -r 'ApplyContext' packages/rig/src/` → only `DeviceApplyContext` (the new class, not the retired dataclass)
- `packages/rig/src/rig/engine/appliers/base.py` → does not exist
- `make test` → 309 passed

---
*Phase: 23-applycontext-consolidation-test-capture-fixes*
*Completed: 2026-06-16*
