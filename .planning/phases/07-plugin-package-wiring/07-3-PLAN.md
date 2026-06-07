# Plan 3: Test Updates & Verification

**Wave:** 2
**Depends on:** Plan 1 (Core Protocol & Engine Cleanup), Plan 2 (Plugin Device Wiring)
**Files modified:**
- `packages/rig/tests/test_devices.py` — Rewrite to import from plugin packages
- `packages/rig/tests/test_apply.py` — Update imports from `rig.engine.devices` to plugin packages
- `packages/rig-chasebliss/tests/` — Add tests if directory exists or create
- `packages/rig-hx/tests/` — Add tests if directory exists or create
**Files created:** None new
**Requirements:** ANLG-01, CHASE-01, MC6-01, HX-01

---

## Task 3.1: Update Core Test Imports in test_devices.py

The core tests in `test_devices.py` import from `rig.engine.devices` which no longer exists. Update them to import from plugin packages. For tests that verify all 4 device types, use the PluginRegistry to discover them.

<read_first>
- `packages/rig/tests/test_devices.py` — Current file, reads from `rig.engine.devices`
- `packages/rig-analog/src/rig_analog/device.py` — AnalogDevice
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — ChaseBlissDevice
- `packages/rig-hx/src/rig_hx/device.py` — HXStompDevice
- `packages/rig-morningstar/src/rig_morningstar/device.py` — MC6Device
</read_first>

<action>
1. Remove all imports from `rig.engine.devices` — replace with imports from the respective plugin packages:
   - `from rig_analog.device import AnalogDevice`
   - `from rig_chasebliss.device import ChaseBlissDevice`
   - `from rig_hx.device import HXStompDevice` (if tests reference it)
   - `from rig_morningstar.device import MC6Device`
2. For the protocol conformance tests, either:
   - (a) Test each device type independently via its plugin package import
   - (b) Use `reload_registry()` from `rig.engine.plugin_registry` to discover all registered types and test them generically
3. Option (b) is preferred — it proves that entry-point discovery works end-to-end.
4. For the import tests (`test_*_device_importable`), update to point to the plugin paths.
</action>

<acceptance_criteria>
- `test_devices.py` has zero imports from `rig.engine.devices`
- All existing test semantics are preserved: Protocol conformance, apply behavior, setup behavior, get_scene_pc_command
- `pytest tests/test_devices.py -q` passes
</acceptance_criteria>

---

## Task 3.2: Update Core Test Imports in test_apply.py

<read_first>
- `packages/rig/tests/test_apply.py` — Check for any imports from `rig.engine.devices`
</read_first>

<action>
1. Search `test_apply.py` for imports from `rig.engine.devices` (likely `ChaseBlissDevice`, `MidiDevice`).
2. Replace with imports from plugin packages:
   - `from rig_chasebliss.device import ChaseBlissDevice`
   - `from rig_hx.device import HXStompDevice` (was `MidiDevice`)
3. Update any test code that references `MidiDevice` to use `HXStompDevice` instead.
4. Remove `midi_connection_io` argument from `apply_plan()` calls in test fixtures — the parameter no longer exists after Plan 1 Task 2.
</action>

<acceptance_criteria>
- `test_apply.py` has zero imports from `rig.engine.devices`
- `apply_plan()` calls have no `midi_connection_io=` argument
- `pytest tests/test_apply.py -q` passes
</acceptance_criteria>

---

## Task 3.3: Fix Any Remaining Core Imports

Search the entire `packages/rig/` directory for any remaining references to `rig.engine.devices`.

<read_first>
- Search results from `rg "rig.engine.devices" packages/rig/ --no-heading`
</read_first>

<action>
1. Run `rg "rig.engine.devices" packages/rig/` to find all remaining references.
2. Update each reference:
   - In test files → plugin package imports
   - In `pyproject.toml` → entry points already updated in Plan 2
   - In any remaining source file → remove or replace
3. Remove imports of `MidiDevice` from `rig.engine.devices` — the `HXStompDevice` replaces it. Any code that used `MidiDevice` (generic MIDI device) now uses `HXStompDevice` (specific HX Stomp device).
</action>

<acceptance_criteria>
- `rg "rig.engine.devices" packages/rig/` returns zero hits (excluding archive files)
- Full test suite passes
</acceptance_criteria>

---

## Task 3.4: Remove `collect_midi_devices` and Clean Up Unused MIDI Interaction

The `collect_midi_devices()` function in `interaction/midi.py` was only used by the Phase -1 loop.

<read_first>
- `packages/rig/src/rig/interaction/midi.py` — `collect_midi_devices` function
- Search results from `rg "collect_midi_devices" packages/rig/`
</read_first>

<action>
1. Search for all callers of `collect_midi_devices`.
2. If only used by `apply.py` (now removed in Plan 1), remove the function.
3. If referenced in any test, remove those references.
</action>

<acceptance_criteria>
- No callers of `collect_midi_devices` remain in production code
- Test suite passes without `collect_midi_devices`
</acceptance_criteria>

---

## Task 3.5: Remove `MidiConnectionIO` Protocol and `InteractiveMidiConnectionIO`

After Plan 1 removes Phase -1, the `MidiConnectionIO` Protocol and its adapters are no longer needed.

<read_first>
- `packages/rig/src/rig/engine/ports.py` — `MidiConnectionIO` Protocol and `InteractiveMidiConnectionIO`
- `packages/rig/tests/fakes.py` — `InMemoryMidiConnectionIO`
- Search results from `rg "MidiConnectionIO" packages/rig/`
</read_first>

<action>
1. Remove `MidiConnectionIO` Protocol from `ports.py`.
2. Remove `InteractiveMidiConnectionIO` class from `ports.py`.
3. Remove `InMemoryMidiConnectionIO` from `tests/fakes.py`.
4. Remove any remaining references in test code.
</action>

<acceptance_criteria>
- `MidiConnectionIO` no longer exists in `ports.py`
- `InteractiveMidiConnectionIO` no longer exists
- `InMemoryMidiConnectionIO` no longer exists in `fakes.py`
- Test suite passes
</acceptance_criteria>

---

## Verification

```bash
cd /Users/derekgliwa/dev/rig-cli

# Full test suite
uv run pytest packages/rig/tests/ -q --timeout=30

# Plugin-specific tests
uv run pytest packages/rig-analog/tests/ -q --timeout=30 2>/dev/null || echo "No analog tests yet"
uv run pytest packages/rig-chasebliss/tests/ -q --timeout=30 2>/dev/null || echo "No chasebliss tests yet"
uv run pytest packages/rig-hx/tests/ -q --timeout=30 2>/dev/null || echo "No hx tests yet"
uv run pytest packages/rig-morningstar/tests/ -q --timeout=30 2>/dev/null || echo "No morningstar tests yet"

# Lint
uv run ruff check packages/rig/src/ packages/rig/tests/
```

## Artifacts this phase produces

- Updated test file: `tests/test_devices.py` — imports from plugin packages
- Updated test file: `tests/test_apply.py` — imports from plugin packages, no `midi_connection_io`
- Removed function: `collect_midi_devices()` in `interaction/midi.py` (if no other callers)
- Removed Protocol: `MidiConnectionIO` in `ports.py`
- Removed class: `InteractiveMidiConnectionIO` in `ports.py`
- Removed fake: `InMemoryMidiConnectionIO` in `tests/fakes.py`
