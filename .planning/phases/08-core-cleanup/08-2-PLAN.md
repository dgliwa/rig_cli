---
phase: 8
plan: 2
name: Move Plugin-Specific Interactions to Plugin Packages
wave: 1
depends_on:
  - 08-1
requirements:
  - CLEANUP-03
  - CLEANUP-04
  - CLEANUP-06
files_modified:
  - packages/rig/src/rig/interaction/cba.py (move)
  - packages/rig/src/rig/interaction/analog.py (move)
  - packages/rig/src/rig/interaction/__init__.py (update imports)
  - packages/rig/src/rig/engine/ports.py (remove methods)
  - packages/rig/tests/fakes.py (remove stubs)
  - packages/rig-chasebliss/src/rig_chasebliss/applier.py (update imports)
  - packages/rig-chasebliss/src/rig_chasebliss/interaction.py (create)
  - packages/rig-analog/src/rig_analog/device.py (update imports)
  - packages/rig-analog/src/rig_analog/interaction.py (create)
  - packages/rig/tests/test_apply.py (update)
  - packages/rig/tests/test_appliers.py (update)
autonomous: true
---

# Plan 2: Move Plugin-Specific Interactions to Plugin Packages

## Must Haves
- CBA prompts (`prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_register`) moved to `rig-chasebliss`
- Analog prompt (`prompt_analog`) moved to `rig-analog`
- `ConfirmationIO` Protocol no longer has plugin-specific methods
- Plugin appliers import prompts directly from their own packages
- `ConfirmationIO` generic interface: only `prompt_device` and `prompt_mc6_navigate` remain

## Tasks

### Task 2.1: Create `rig_chasebliss/interaction.py`

<read_first>
- packages/rig/src/rig/interaction/cba.py
- packages/rig-chasebliss/src/rig_chasebliss/__init__.py
</read_first>

<action>
1. Copy `packages/rig/src/rig/interaction/cba.py` to `packages/rig-chasebliss/src/rig_chasebliss/interaction.py`
   - Same content, same functions: `prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_register`
   - No import changes needed within the file (it imports from `typing` and `rich.console` — both available as plugin deps)
2. Export the three functions from `rig_chasebliss/__init__.py` for convenience:
   ```python
   from rig_chasebliss.interaction import prompt_cba_build_preset, prompt_cba_channel, prompt_cba_register
   ```
3. Delete `packages/rig/src/rig/interaction/cba.py`
</action>

<acceptance_criteria>
- `packages/rig-chasebliss/src/rig_chasebliss/interaction.py` exists with all 3 functions
- `packages/rig/src/rig/interaction/cba.py` does not exist
- All 3 prompt functions importable from `rig_chasebliss`
</acceptance_criteria>

### Task 2.2: Create `rig_analog/interaction.py`

<read_first>
- packages/rig/src/rig/interaction/analog.py
- packages/rig-analog/src/rig_analog/__init__.py
</read_first>

<action>
1. Copy `packages/rig/src/rig/interaction/analog.py` to `packages/rig-analog/src/rig_analog/interaction.py`
2. Export `prompt_analog` from `rig_analog/__init__.py`:
   ```python
   from rig_analog.interaction import prompt_analog
   ```
3. Delete `packages/rig/src/rig/interaction/analog.py`
</action>

<acceptance_criteria>
- `packages/rig-analog/src/rig_analog/interaction.py` exists with `prompt_analog`
- `packages/rig/src/rig/interaction/analog.py` does not exist
- `prompt_analog` importable from `rig_analog`
</acceptance_criteria>

### Task 2.3: Remove plugin-specific prompt methods from `ConfirmationIO` Protocol

<read_first>
- packages/rig/src/rig/engine/ports.py
</read_first>

<action>
From the `ConfirmationIO` Protocol class and `RichConfirmationIO` implementation in `ports.py`:

1. Remove these methods entirely from both the Protocol and `RichConfirmationIO`:
   - `prompt_cba_channel`
   - `prompt_cba_preset` (named `prompt_cba_preset` in Protocol but `prompt_cba_build_preset` in rich impl — remove both)
   - `prompt_cba_register`
   - `prompt_analog`
2. Remove the imports that fed them:
   - `from rig.interaction.cba import prompt_cba_build_preset, prompt_cba_channel, prompt_cba_register`
   - `from rig.interaction.analog import prompt_analog`
3. Keep these remaining Protocol methods:
   - `prompt_device`
   - `prompt_mc6_navigate`
</action>

<acceptance_criteria>
- `ports.py` has no imports from `rig.interaction.cba` or `rig.interaction.analog`
- `ConfirmationIO` Protocol has no `prompt_cba_*` or `prompt_analog` methods
- `RichConfirmationIO` has no `prompt_cba_*` or `prompt_analog` implementations
</acceptance_criteria>

### Task 2.4: Update `InMemoryConfirmationIO` in `tests/fakes.py`

<read_first>
- packages/rig/tests/fakes.py
</read_first>

<action>
1. Remove `prompt_cba_channel`, `prompt_cba_preset`, `prompt_cba_register`, `prompt_analog` methods from `InMemoryConfirmationIO` class
2. Keep `prompt_device` and `prompt_mc6_navigate` methods
</action>

<acceptance_criteria>
- `InMemoryConfirmationIO` no longer has CBA/analog prompt methods
- Check that no test calls `in_memory_confirmation_io.prompt_cba_*` or `.prompt_analog`
</acceptance_criteria>

### Task 2.5: Update `rig_chasebliss/applier.py` to import prompts directly

<read_first>
- packages/rig-chasebliss/src/rig_chasebliss/applier.py
</read_first>

<action>
1. Replace all `ctx.confirmation_io.prompt_cba_*()` calls with direct function calls:
   - `ctx.confirmation_io.prompt_cba_channel(...)` → `prompt_cba_channel(...)` (import from `rig_chasebliss.interaction`)
   - `ctx.confirmation_io.prompt_cba_preset(...)` → `prompt_cba_build_preset(...)` (import from `rig_chasebliss.interaction`)
   - `ctx.confirmation_io.prompt_cba_register(...)` → `prompt_cba_register(...)` (import from `rig_chasebliss.interaction`)
2. Add import at top of file: `from rig_chasebliss.interaction import prompt_cba_build_preset, prompt_cba_channel, prompt_cba_register`
</action>

<acceptance_criteria>
- `rig_chasebliss/applier.py` imports prompt functions from `rig_chasebliss.interaction`
- No calls to `ctx.confirmation_io.prompt_cba_*` remain
- CBA applier tests pass
</acceptance_criteria>

### Task 2.6: Update `rig_analog/device.py` to import prompt directly

<read_first>
- packages/rig-analog/src/rig_analog/device.py
</read_first>

<action>
1. Replace `res = ctx.confirmation_io.prompt_analog(action.device, action.preset_name)` with `res = prompt_analog(action.device, action.preset_name)` imported directly
2. Add import: `from rig_analog.interaction import prompt_analog`
</action>

<acceptance_criteria>
- `rig_analog/device.py` imports `prompt_analog` from `rig_analog.interaction`
- No `ctx.confirmation_io.prompt_analog` call remains
- Analog device tests pass
</acceptance_criteria>

### Task 2.7: Update `rig/interaction/__init__.py`

<read_first>
- packages/rig/src/rig/interaction/__init__.py
</read_first>

<action>
1. Remove imports and re-exports for:
   - `prompt_cba_build_preset`, `prompt_cba_channel`, `prompt_cba_register`
   - `prompt_analog`
2. Keep: `prompt_analog`, `prompt_device`, `prompt_midi_connect` (midi ones)
</action>

<acceptance_criteria>
- `rig/interaction/__init__.py` no longer references CBA or analog modules
- No stale imports
</acceptance_criteria>

### Task 2.8: Update test files

<read_first>
- packages/rig/tests/test_apply.py
- packages/rig/tests/test_appliers.py
</read_first>

<action>
1. Check `test_apply.py`: remove any `InMemoryConfirmationIO` setup that uses removed prompt methods (CBA/analog side effects)
   - The test's side_effect arrays already only use "confirm"/"skip" strings — they'll now go through `prompt_device` and `prompt_mc6_navigate` only, since the plugin classes handle their own prompts
   - Verify test assertions still match after the change
2. Check `test_appliers.py`: the `ChaseBlissApplier` tests now use direct imports from `rig_chasebliss` — verify they still pass
</action>

<acceptance_criteria>
- All tests pass: `uv run pytest packages/ -q`
</acceptance_criteria>

## Verification
- `uv run pytest packages/ -q` passes
- `uv run ruff check packages/` passes
- `rg "from rig\.(interaction\.(cba|analog)|engine\.ports import.*prompt_cba|prompt_analog)" packages/rig/src/` returns zero results
