---
id: "phase-12"
plan_id: "01"
wave: 1
depends_on: []
requirements_addressed: [DEFER-01, DEFER-02]
autonomous: true
status: planned
---

# Plan 01: Remove Deferred Items

Remove the vestigial `rig generate mc6` CLI command and the unused `composes` validation from the loader.

## Objective

Two independent deletions:

1. **DEFER-01**: Delete `rig generate mc6` — the CLI command, the `gen_app` Typer group, the `rig_morningstar.generator` module, and all associated tests
2. **DEFER-02**: Delete `composes` validation — the `_get_composes()` helper and the composes validation block in `_validate_references()`

## Tasks

### Task 1: Remove `rig_morningstar.generator` module

<read_first>
- packages/rig-morningstar/src/rig_morningstar/generator.py
</read_first>

<action>
Delete the file `packages/rig-morningstar/src/rig_morningstar/generator.py` (75 lines). It exports `generate_mc6()` and `write_mc6_config()`. Both are unused outside of tests.
</action>

<acceptance_criteria>
- `packages/rig-morningstar/src/rig_morningstar/generator.py` no longer exists
- `generate_mc6` and `write_mc6_config` are not imported anywhere in source (only tests — those are removed in tasks below)
</acceptance_criteria>

---

### Task 2: Remove `gen_app` and the generate CLI command

<read_first>
- packages/rig/src/rig/cli/commands/generate.py
- packages/rig/src/rig/cli/_shared.py
- packages/rig/src/rig/cli/__init__.py
</read_first>

<action>
Three files need changes:

1. **Delete** `packages/rig/src/rig/cli/commands/generate.py` (41 lines, entire file — single `mc6` command on `gen_app`)
2. **Remove `gen_app`** from `packages/rig/src/rig/cli/_shared.py`:
   - Delete the line `gen_app = typer.Typer(help="Generate artifacts from config")`
   - Remove `gen_app` from the import in `__init__.py` (see step 3)
3. **Update** `packages/rig/src/rig/cli/__init__.py`:
   - Remove `gen_app` from `from rig.cli._shared import app, gen_app`
   - Delete the line `from rig.cli.commands import apply, diff, generate, plan, status, validate  # noqa: F401`
     (or just remove `generate` from the list)
   - Delete `app.add_typer(gen_app, name="generate")`
</action>

<acceptance_criteria>
- `packages/rig/src/rig/cli/commands/generate.py` does not exist
- `_shared.py` has no `gen_app` definition
- `cli/__init__.py` has no `gen_app` import, no `generate` module import, and no `app.add_typer(gen_app, ...)`
- `grep -rn "gen_app" packages/rig/src/` returns zero results
</acceptance_criteria>

---

### Task 3: Remove composes validation from loader

<read_first>
- packages/rig/src/rig/config/loader.py (lines 144-191)
</read_first>

<action>
In `packages/rig/src/rig/config/loader.py`:

1. Delete the `_get_composes()` function (lines 144-149)
2. Delete the composes validation block from `_validate_references()` (lines 183-191):
   ```
   logger.debug("Validating controller composes references")
   for device in rig.devices.values():
       if device.type == DeviceType.CONTROLLER:
           composed_ids = _get_composes(device)
           for cid in composed_ids:
               if cid not in device_ids:
                   raise MissingReferenceError(
                       f"Controller '{device.id}' composes unknown device '{cid}'"
                   )
   ```
</action>

<acceptance_criteria>
- `_get_composes` is not defined in `loader.py`
- No import, reference, or call to `_get_composes` exists in source
- `grep -rn "composes" packages/rig/src/` returns zero results
- All existing validation (`_validate_references`) still works — signal chain, scene preset refs, etc.
</acceptance_criteria>

---

### Task 4: Remove associated tests

<read_first>
- packages/rig/tests/test_mc6_generator.py
- packages/rig/tests/test_catalog.py
- packages/rig/tests/test_cli.py (TestGenerateMC6 class)
- packages/rig/tests/test_loader.py (composes tests)
</read_first>

<action>
Four test files need changes:

1. **Delete** `packages/rig/tests/test_mc6_generator.py` (93 lines, entire file — all 5 tests are for `generate_mc6`/`write_mc6_config`)
2. **Remove generate tests from** `packages/rig/tests/test_catalog.py`:
   - Delete line 10: `from rig_morningstar.generator import generate_mc6`
   - Delete the `test_generates_pc_for_hx_and_mood` method and `test_generates_pc_for_empty_scene` method (lines 133-150)
3. **Remove** the `TestGenerateMC6` class from `packages/rig/tests/test_cli.py` (lines 139-145)
4. **Remove composes tests** from `packages/rig/tests/test_loader.py`:
   - Delete `test_controller_composes_validation` method (lines 262-267)
   - Delete `test_controller_composes_unknown_device` method (lines 269-273)
</action>

<acceptance_criteria>
- `test_mc6_generator.py` does not exist
- `test_catalog.py` has no `generate_mc6` import or test methods
- `test_cli.py` has no `TestGenerateMC6` class
- `test_loader.py` has no composes test methods
- `grep -rn "generate_mc6\|composes" packages/rig/tests/` returns zero results
- All remaining tests pass: `uv run pytest tests/ -q`
</acceptance_criteria>

## Verification

```bash
# No composes references in source
grep -rn "composes" packages/rig/src/ | grep -v __pycache__ && echo "FAIL: composes still referenced" || echo "PASS: composes removed"

# No gen_app references in source
grep -rn "gen_app" packages/rig/src/ | grep -v __pycache__ && echo "FAIL: gen_app still referenced" || echo "PASS: gen_app removed"

# No generate_mc6 references anywhere
grep -rn "generate_mc6" packages/ | grep -v __pycache__ && echo "FAIL: generate_mc6 still referenced" || echo "PASS: generate_mc6 removed"

# All tests pass
uv run pytest tests/ -q
```

## Wave Assignment

Wave 1 — all tasks are independent, can be executed concurrently:
- Task 1 (delete generator) ⟹ Wave 1
- Task 2 (remove CLI) ⟹ Wave 1
- Task 3 (remove composes) ⟹ Wave 1
- Task 4 (remove tests) ⟹ Wave 1

## must_haves

- `rig generate mc6` no longer exists as a command
- `_get_composes()` and composes validation are removed from loader
- All tests pass with zero `generate_mc6`, `gen_app`, or `composes` references remaining

## Artifacts this phase produces

- Files deleted: `generate.py`, `generator.py`, `test_mc6_generator.py`
- Files modified: `_shared.py`, `cli/__init__.py`, `loader.py`, `test_catalog.py`, `test_cli.py`, `test_loader.py`
- No new symbols created — this is a removal-only phase
