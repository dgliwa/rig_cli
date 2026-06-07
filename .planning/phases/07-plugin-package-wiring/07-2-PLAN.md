# Plan 2: Plugin Device Wiring

**Wave:** 1 (parallel with Plan 1)
**Depends on:** None
**Files modified:**
- `packages/rig-analog/pyproject.toml` — Update entry point
- `packages/rig-analog/src/rig_analog/device.py` — Verify class exists (already does)
- `packages/rig-hx/pyproject.toml` — Update entry point
- `packages/rig-hx/src/rig_hx/device.py` — Create HXStompDevice
- `packages/rig-chasebliss/pyproject.toml` — Update entry point
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — Create full ChaseBlissDevice with MIDI setup
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — Refactor into device (may remain as helper)
- `packages/rig-morningstar/pyproject.toml` — Update entry point
- `packages/rig-morningstar/src/rig_morningstar/device.py` — Verify MC6Device setup()
**Files created:** `packages/rig-hx/src/rig_hx/device.py`
**Requirements:** ANLG-01, CHASE-01, MC6-01, HX-01

---

## Task 2.1: Update rig-analog Entry Point

The AnalogDevice class already lives in `rig_analog.device` and it already implements the Protocol correctly. Only the entry point needs updating.

<read_first>
- `packages/rig-analog/pyproject.toml` — Current entry point
- `packages/rig-analog/src/rig_analog/device.py` — Existing class
- `packages/rig/src/rig/engine/plugin.py` — Device Protocol for conformance
</read_first>

<action>
1. In `packages/rig-analog/pyproject.toml`, change the entry point from:
   `manual = "rig.engine.devices:AnalogDevice"` → `manual = "rig_analog.device:AnalogDevice"`
</action>

<acceptance_criteria>
- Entry point resolves: `rig.engine.plugin_registry._discover()` loads `AnalogDevice` from `rig_analog.device`
- No import of `rig.engine.devices` from `rig-analog`
- `pip install -e packages/rig-analog && rig status` works without any core dependency on the analog plugin
</acceptance_criteria>

---

## Task 2.2: Update rig-morningstar Entry Point

The MC6Device class already lives in `rig_morningstar.device` with a `setup()` method that handles MIDI connection. The entry point needs updating.

<read_first>
- `packages/rig-morningstar/pyproject.toml` — Current entry point
- `packages/rig-morningstar/src/rig_morningstar/device.py` — Existing device with setup()
- `packages/rig/src/rig/engine/plugin.py` — Device Protocol for conformance
</read_first>

<action>
1. In `packages/rig-morningstar/pyproject.toml`, change the entry point from:
   `controller = "rig.engine.devices:MC6Device"` → `controller = "rig_morningstar.device:MC6Device"`
2. Verify `MC6Device.setup()` in `rig_morningstar.device`:
   - Already prompts for MIDI connection via `prompt_midi_connect`
   - Already caches port via `update_device_state`
   - Already adds itself to `ctx.connected_devices`
   - No changes needed to the setup() logic itself
</action>

<acceptance_criteria>
- Entry point resolves: `rig.engine.plugin_registry._discover()` loads `MC6Device` from `rig_morningstar.device`
- MC6 `setup()` produces a working MIDI connection in `apply()` phase
- `pip install -e packages/rig-morningstar && rig status` works independently
</acceptance_criteria>

---

## Task 2.3: Create HXStompDevice in rig-hx

The HX Stomp is a simple PC-message-based device (like MidiDevice but named for extensibility). Create the device class and update the entry point.

<read_first>
- `packages/rig-hx/pyproject.toml` — Entry point
- `packages/rig-hx/src/rig_hx/__init__.py` — Package init
- `packages/rig/src/rig/engine/plugin.py` — Device Protocol
- `packages/rig/src/rig/engine/appliers/base.py` — DeviceApplyResult, update_device_state
- `packages/rig-morningstar/src/rig_morningstar/device.py` — Reference for setup() with MIDI
- `packages/rig-analog/src/rig_analog/device.py` — Reference for minimal Device class
- `packages/rig/src/rig/models/preset.py` — HXStompPreset model
</read_first>

<action>
1. **Create** `packages/rig-hx/src/rig_hx/device.py` with an `HXStompDevice` class following the same BaseModel pattern as `AnalogDevice`/`MC6Device`:
   - `model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")`
   - Fields: `id: str`, `name: str`, `config: Any`, `type: DeviceType = DeviceType.MODELER`, `presets: list[Any]`
   - `plan()` → raise `NotImplementedError`
   - `diff()` → raise `NotImplementedError`
   - `setup()` → Prompt MIDI connection via `prompt_midi_connect()` from `rig.interaction.midi`, cache port in state, add to `connected_devices`. On dry-run, just add to connected_devices.
   - `get_scene_pc_command()` → Same logic as current `MidiDevice.get_scene_pc_command()`: look up preset by id, if it's a `DigitalPreset` or `HXStompPreset` with a `preset_number`, return `{"type": "pc", "channel": ch, "value": preset_number, "label": ...}`
   - `apply()` → Same logic as current `MidiDevice.apply()`: try PC send, prompt with retry/skip/quit loop
2. In `packages/rig-hx/pyproject.toml`, update the entry point from:
   `midi = "rig.engine.devices:MidiDevice"` → `midi = "rig_hx.device:HXStompDevice"`
</action>

<acceptance_criteria>
- `packages/rig-hx/src/rig_hx/device.py` contains `HXStompDevice` class
- HXStompDevice has `setup()`, `apply()`, `get_scene_pc_command()`, `plan()`, `diff()`
- HXStompDevice's setup() handles dry_run, MIDI connection via prompt_midi_connect, state caching
- Entry point resolves via `_discover()`
- `HXStompDevice` structurally satisfies the `Device` Protocol (no type errors)
</acceptance_criteria>

---

## Task 2.4: Create Full ChaseBlissDevice in rig-chasebliss

This is the most complex task. The current `ChaseBlissDevice` in core delegates `setup()` to `rig_chasebliss.device.cba_setup()`. We need to make `rig_chasebliss.device.ChaseBlissDevice` the real home, merging the core class's `get_scene_pc_command()` and `apply()` with the `cba_setup()` helper and the `ChaseBlissApplier` logic.

<read_first>
- `packages/rig-chasebliss/pyproject.toml` — Current entry point
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — Current cba_setup helper + _detect_cba_setup_for_device
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — ChaseBlissApplier with 3-phase setup (establish_channel, build_preset, register_scenes)
- `packages/rig/src/rig/engine/devices.py` — Core ChaseBlissDevice (lines 145-205: get_scene_pc_command, apply via _midi_device)
- `packages/rig/src/rig/engine/plugin.py` — Device Protocol
- `packages/rig/src/rig/engine/appliers/base.py` — DeviceApplyResult, update_device_state, mark_preset_saved
- `packages/rig/src/rig/engine/plan/models.py` — CbaSetupAction
- `packages/rig/src/rig/interaction/cba.py` — CBA interaction prompts
- `packages/rig/src/rig/models/device.py` — ChaseBlissConfig
</read_first>

<action>
1. **In `packages/rig-chasebliss/src/rig_chasebliss/device.py`:**
   - Convert the file from a helper module to a full `ChaseBlissDevice(BaseModel)` class
   - Import `MidiManager` from `rig.midi.adapter` as a shared utility
   - Fields and BaseModel config match the existing pattern: `model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")`, `id`, `name`, `config`, `type = DeviceType.DIGITAL`, `presets`
   - `plan()` → raise NotImplementedError
   - `diff()` → raise NotImplementedError
   - `get_scene_pc_command()` → Same logic as core ChaseBlissDevice/MidiDevice
   - `setup()` → Full 3-phase CBA setup:
     1. MIDI port connection via `prompt_midi_connect()` (unless dry_run)
     2. Detect CBA setup actions via `_detect_cba_setup_for_device()`
     3. Execute establish_channel → build_preset → register_scenes using the same logic as `ChaseBlissApplier`
     4. Keep `cba_setup()` as a static method or refactor it inline
   - `apply()` → Same as core `ChaseBlissDevice.apply()` which delegates to the same logic as `MidiDevice`: try PC send, prompt with retry/skip/quit

2. **Update pyproject.toml:**
   - Change from `chase_bliss = "rig.engine.devices:ChaseBlissDevice"` → `chase_bliss = "rig_chasebliss.device:ChaseBlissDevice"`

3. **Keep `applier.py` or move logic:** The `ChaseBlissApplier` class methods can remain as private helpers in `device.py` or stay in `applier.py` imported by the device. Either approach works — prefer keeping applier.py and importing the applier helper methods into the device class's setup().
</action>

<acceptance_criteria>
- `ChaseBlissDevice` lives in `rig_chasebliss.device` as a Pydantic BaseModel
- Entry point points to `rig_chasebliss.device:ChaseBlissDevice`
- `setup()` handles MIDI port selection, 3-phase CBA init (channel establish, preset build, scene registration)
- `apply()` sends PC message and prompts user (same behavior as core)
- `get_scene_pc_command()` returns PC dict for DigitalPreset/HXStompPreset presets
- Old core `ChaseBlissDevice` no longer exists (deleted in Plan 1 Task 3)
- Import path `from rig.engine.devices import ChaseBlissDevice` no longer works (expected — tests update in Plan 3)
</acceptance_criteria>

---

## Verification

```bash
# Verify all entry points resolve
cd /Users/derekgliwa/dev/rig-cli && uv run python -c "
from rig.engine.plugin_registry import _discover, get_registry
reg = _discover()
types = ['manual', 'chase_bliss', 'midi', 'controller']
for t in types:
    cls = reg.get_model(t)
    print(f'{t}: {cls.__name__ if cls else \"NOT FOUND\"}')
"

# Verify each plugin installs independently
pip install -e packages/rig-analog -e packages/rig-chasebliss -e packages/rig-hx -e packages/rig-morningstar
uv run rig status 2>&1 | head -5
```

## Artifacts this phase produces

- New file: `packages/rig-hx/src/rig_hx/device.py` — `HXStompDevice` class
- Updated class: `packages/rig-chasebliss/src/rig_chasebliss/device.py` — Full `ChaseBlissDevice` with MIDI setup() + applier logic
- Updated entry points: all 4 `pyproject.toml` files point to plugin-local Device classes
