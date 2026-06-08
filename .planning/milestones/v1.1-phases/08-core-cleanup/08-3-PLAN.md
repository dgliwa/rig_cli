---
phase: 8
plan: 3
name: Refactor Controller Model and Final Cleanup
wave: 2
depends_on:
  - 08-2
requirements:
  - CLEANUP-05
files_modified:
  - packages/rig/src/rig/models/controller.py (delete)
  - packages/rig/src/rig/models/__init__.py (update exports)
  - packages/rig/tests/test_models.py (update imports)
  - packages/rig/tests/test_mc6_generator.py (update imports)
  - packages/rig/src/rig/config/loader.py (verify ControllerConfig still works)
autonomous: true
---

# Plan 3: Refactor Controller Model and Final Cleanup

## Must Haves
- `rig/models/controller.py` deleted
- `Controller`, `ControllerType`, `MC6Config` no longer exported from `rig.models`
- `ControllerConfig` stays in `device.py` (part of discriminated union — used by loader and rig)
- All tests passing
- No stale import paths

## Tasks

### Task 3.1: Delete `rig/models/controller.py` and update exports

<read_first>
- packages/rig/src/rig/models/controller.py
- packages/rig/src/rig/models/__init__.py
</read_first>

<action>
1. Delete `packages/rig/src/rig/models/controller.py`
2. Update `packages/rig/src/rig/models/__init__.py`:
   - Remove `from rig.models.controller import Controller, ControllerType, MC6Config`
   - Remove `"Controller"`, `"ControllerType"`, `"MC6Config"` from `__all__`
</action>

<acceptance_criteria>
- `packages/rig/src/rig/models/controller.py` does not exist
- `rig.models.__init__` no longer exports `Controller`, `ControllerType`, `MC6Config`
</acceptance_criteria>

### Task 3.2: Update test imports

<read_first>
- packages/rig/tests/test_models.py
- packages/rig/tests/test_mc6_generator.py
</read_first>

<action>
1. Update `packages/rig/tests/test_models.py`:
   - Remove `from rig.models.controller import Controller, ControllerType, MC6Config`
   - Remove any tests that reference `Controller`, `ControllerType`, or `MC6Config` directly:
     - `import MC6Config` reference
     - `assert MC6Config is not None` test line
     - `Controller` reconstruction test
   - Keep `ControllerConfig` tests (this lives in `device.py` and stays)
   - The `test_controller_config_serde` test should remain (it tests `ControllerConfig` from `device.py`)
2. Update `packages/rig/tests/test_mc6_generator.py`:
   - The comment about `Controller, ControllerType, MC6Config` backward compat can be updated to remove that note
</action>

<acceptance_criteria>
- No imports from `rig.models.controller` in any test file
- `ControllerConfig` tests still work (from `rig.models.device`)
- Test count before and after is minimally different (only MC6Config/Controller tests removed)
</acceptance_criteria>

### Task 3.3: Final verification

<read_first>
- Full test suite
</read_first>

<action>
1. Run `rg "from rig\.models\.controller|from rig.models import.*Controller[^C]" packages/` — must return zero results
2. Run `rg "rig\.models\.controller" packages/` — must return zero results
3. Run full test suite: `uv run pytest packages/ -q`
4. Run lint: `uv run ruff check packages/`
5. Run format check: `uv run ruff format packages/ --check`
</action>

<acceptance_criteria>
- Zero references to `rig.models.controller` anywhere
- All tests pass
- Ruff clean
</acceptance_criteria>

## Verification
- `uv run pytest packages/ -q` passes (294+ tests — may lose 1-2 MC6Config/Controller-specific tests)
- `uv run ruff check packages/` passes
- No `rig.models.controller` references exist
