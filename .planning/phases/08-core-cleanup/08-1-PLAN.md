---
phase: 8
plan: 1
name: Remove Dead/Duplicate Core Code
wave: 1
depends_on: []
requirements:
  - CLEANUP-01
  - CLEANUP-02
files_modified:
  - packages/rig/src/rig/midi/mc6.py (delete)
  - packages/rig/src/rig/generators/mc6_presets.py (delete)
  - packages/rig/src/rig/catalog/chase_bliss.py (delete)
  - packages/rig/src/rig/engine/appliers/chase_bliss.py (delete)
  - packages/rig/tests/test_mc6_sysex.py (update imports)
  - packages/rig/tests/test_mc6_generator.py (update imports)
  - packages/rig/tests/test_catalog.py (update imports)
  - packages/rig/tests/test_appliers.py (update imports)
  - packages/rig/tests/test_logging.py (update logger ref)
  - packages/rig/tests/test_base_helpers.py (remove dead path check)
autonomous: true
---

# Plan 1: Remove Dead/Duplicate Core Code

## Must Haves
- All 4 dead core files deleted
- Tests updated to import from plugin packages
- No stale imports remain
- Full test suite passes

## Tasks

### Task 1.1: Delete `rig/midi/mc6.py` and update tests

<read_first>
- packages/rig/src/rig/midi/mc6.py
- packages/rig-morningstar/src/rig_morningstar/sysex.py
- packages/rig/tests/test_mc6_sysex.py
</read_first>

<action>
1. Delete `packages/rig/src/rig/midi/mc6.py`
2. Update `packages/rig/tests/test_mc6_sysex.py`:
   - Change `from rig.midi.mc6 import (...)` to `from rig_morningstar.sysex import (...)`
   - Keep all test function bodies unchanged
3. If `packages/rig/src/rig/midi/__init__.py` re-exports from `mc6`, clean up that import
</action>

<acceptance_criteria>
- `packages/rig/src/rig/midi/mc6.py` does not exist
- `packages/rig/tests/test_mc6_sysex.py` passes with imports from `rig_morningstar.sysex`
- No other file imports `rig.midi.mc6`
</acceptance_criteria>

### Task 1.2: Delete `rig/generators/mc6_presets.py` and update tests

<read_first>
- packages/rig/src/rig/generators/mc6_presets.py
- packages/rig-morningstar/src/rig_morningstar/generator.py
- packages/rig/tests/test_mc6_generator.py
- packages/rig/tests/test_catalog.py
- packages/rig/tests/test_logging.py
</read_first>

<action>
1. Delete `packages/rig/src/rig/generators/mc6_presets.py`
2. Update `packages/rig/tests/test_mc6_generator.py`:
   - Change `from rig.generators.mc6_presets import generate_mc6, write_mc6_config` to `from rig_morningstar.generator import generate_mc6, write_mc6_config`
3. Update `packages/rig/tests/test_catalog.py`:
   - Change `from rig.generators.mc6_presets import generate_mc6` to `from rig_morningstar.generator import generate_mc6`
4. Update `packages/rig/tests/test_logging.py`:
   - Change `"rig.generators.mc6_presets"` to `"rig_morningstar.generator"`
5. If `packages/rig/src/rig/generators/__init__.py` re-exports from `mc6_presets`, clean up
</action>

<acceptance_criteria>
- `packages/rig/src/rig/generators/mc6_presets.py` does not exist
- Tests import from `rig_morningstar.generator`
- All updated tests pass
</acceptance_criteria>

### Task 1.3: Delete `rig/catalog/chase_bliss.py` and update tests

<read_first>
- packages/rig/src/rig/catalog/chase_bliss.py
- packages/rig-chasebliss/src/rig_chasebliss/catalog.py
- packages/rig/tests/test_catalog.py
- packages/rig/src/rig/models/device.py
</read_first>

<action>
1. Delete `packages/rig/src/rig/catalog/chase_bliss.py`
2. Update `packages/rig/tests/test_catalog.py`:
   - Change `from rig.catalog.chase_bliss import MOOD_MKII_CONTROLS` to `from rig_chasebliss.catalog import MOOD_MKII_CONTROLS`
3. Update `packages/rig/src/rig/models/device.py`:
   - The lazy import `from rig.catalog.chase_bliss import get_controls` in `Device._populate_cba_controls` must change to `from rig_chasebliss.catalog import get_controls`
4. If `packages/rig/src/rig/catalog/__init__.py` is now empty, keep it (empty __init__.py is fine — `catalog` directory serves no purpose after this, but removing it is lower priority)
</action>

<acceptance_criteria>
- `packages/rig/src/rig/catalog/chase_bliss.py` does not exist
- Tests import `MOOD_MKII_CONTROLS` from `rig_chasebliss.catalog`
- `Device._populate_cba_controls` imports `get_controls` from `rig_chasebliss.catalog`
</acceptance_criteria>

### Task 1.4: Delete `rig/engine/appliers/chase_bliss.py` and update tests

<read_first>
- packages/rig/src/rig/engine/appliers/chase_bliss.py
- packages/rig/tests/test_appliers.py
</read_first>

<action>
1. Delete `packages/rig/src/rig/engine/appliers/chase_bliss.py`
2. Update `packages/rig/tests/test_appliers.py`:
   - Change `from rig.engine.appliers.chase_bliss import ChaseBlissApplier` to `from rig_chasebliss.applier import ChaseBlissApplier`
3. Update `packages/rig/tests/test_base_helpers.py`:
   - The `test_no_direct_presets_saved_mutations` test checks AST of `rig.engine.appliers.chase_bliss` file. Since that file is deleted, this test needs updating: remove the `chase_bliss_src` path check for the deleted file (the source is now `rig_chasebliss/applier.py`)
</action>

<acceptance_criteria>
- `packages/rig/src/rig/engine/appliers/chase_bliss.py` does not exist
- `test_appliers.py` imports from `rig_chasebliss.applier`
- `test_base_helpers.py` no longer references core `chase_bliss.py` path
- All tests pass
</acceptance_criteria>

### Task 1.5: Verify no stale references remain

<read_first>
- All files modified above
</read_first>

<action>
1. Run `rg "from rig\.(midi\.mc6|generators\.mc6_presets|catalog\.chase_bliss|engine\.appliers\.chase_bliss)" packages/rig/src/` — must return zero results
2. Run `rg "rig\.midi\.mc6|rig\.generators\.mc6_presets|rig\.catalog\.chase_bliss|rig\.engine\.appliers\.chase_bliss" packages/rig/tests/` — should only return test files already updated above (verify imports actually changed)
3. Run full test suite: `uv run pytest packages/ -q`
</action>

<acceptance_criteria>
- Zero remaining references to deleted modules in source
- All tests pass (expecting 302+)
</acceptance_criteria>

## Verification
- `uv run pytest packages/ -q` passes
- `uv run ruff check packages/` passes
- No imports reference deleted modules
