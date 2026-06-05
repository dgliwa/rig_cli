---
phase: 4
plan: P2
type: execute
wave: 2
depends_on: [P1]
files_modified:
  - src/rig/engine/devices.py
  - src/rig/engine/plugin_registry.py
  - tests/test_devices.py
  - tests/test_plugin.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "src/rig/engine/devices.py exists with AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device"
    - "All four concrete types satisfy the Device Protocol structurally (have id, name, config, plan, diff, apply)"
    - "plan() and diff() raise NotImplementedError on all four types"
    - "AnalogDevice.apply() delegates to AnalogApplier.apply_scene logic using DeviceApplyContext"
    - "MidiDevice.apply() delegates to MidiApplier.apply_scene logic using DeviceApplyContext"
    - "ChaseBlissDevice.apply() delegates scene apply to MidiApplier logic; setup logic via apply_setup remains on ChaseBlissApplier for now"
    - "MC6Device.apply() delegates to MC6Applier.apply_banks logic using DeviceApplyContext"
    - "PluginRegistry default instance has all four types registered via register_model()"
    - "Concrete types are Pydantic BaseModel subclasses"
  artifacts:
    - path: "src/rig/engine/devices.py"
      provides: "AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device concrete types"
      contains: "class AnalogDevice"
    - path: "tests/test_devices.py"
      provides: "Protocol compliance and apply() behavior tests"
      contains: "test_analog_device_satisfies_device_protocol"
  key_links:
    - from: "src/rig/engine/devices.py"
      to: "src/rig/engine/appliers/analog.py"
      via: "AnalogDevice.apply() replicates AnalogApplier logic"
      pattern: "apply_scene logic inlined into apply()"
    - from: "src/rig/engine/devices.py"
      to: "src/rig/engine/appliers/midi_device.py"
      via: "MidiDevice.apply() replicates MidiApplier logic"
      pattern: "apply_scene logic inlined into apply()"
    - from: "src/rig/engine/devices.py"
      to: "src/rig/engine/appliers/mc6.py"
      via: "MC6Device.apply() wraps apply_banks logic"
      pattern: "apply_banks logic inlined or delegated"
    - from: "src/rig/engine/plugin_registry.py"
      to: "src/rig/engine/devices.py"
      via: "default registry registration"
      pattern: "_default_registry.register_model(...)"
---

<objective>
Create the four concrete device types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) as Pydantic models that satisfy the Device Protocol. Migrate apply logic from the old appliers into each type's apply() method. Register all four in a module-level default PluginRegistry instance.

Depends on P1 (Device Protocol + DeviceApplyContext + registry model-class registration).
Loader migration (P3) consumes the registered model classes; apply.py migration (P3) consumes device.apply().
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-plugin-migration/04-CONTEXT.md
@src/rig/engine/plugin.py
@src/rig/engine/plugin_registry.py
@src/rig/engine/appliers/analog.py
@src/rig/engine/appliers/midi_device.py
@src/rig/engine/appliers/chase_bliss.py
@src/rig/engine/appliers/mc6.py
@src/rig/engine/appliers/base.py
@src/rig/models/device.py
@tests/fakes.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create AnalogDevice and MidiDevice in devices.py</name>
  <files>src/rig/engine/devices.py, tests/test_devices.py</files>
  <behavior>
    Both types are Pydantic BaseModel subclasses. They carry the same fields as the current `Device` model (id, manufacturer, model, type, config, presets, image, notes) so they can replace Device instances in Rig.devices.

    AnalogDevice:
    - Fields mirror Device fields; config is typed as ManualConfig
    - apply(ctx: DeviceApplyContext) -> DeviceApplyResult — replicates AnalogApplier.apply_scene logic exactly:
      dry_run path: print skip message, return skipped result
      live path: prompt_analog via ctx.confirmation_io, update state, return confirmed/skipped/error
    - plan(ctx: PluginContext) raises NotImplementedError
    - diff(ctx: PluginContext) raises NotImplementedError
    - id, name, config properties satisfied by Pydantic fields (model field "id" satisfies Property "id")

    MidiDevice:
    - Fields mirror Device fields; config is typed as MidiConfig
    - apply(ctx: DeviceApplyContext) -> DeviceApplyResult — replicates MidiApplier.apply_scene logic exactly:
      dry_run path: print skip message, return skipped result
      live path: try PC send, loop prompt_device, handle confirm/retry/skip/quit
    - plan(ctx: PluginContext) raises NotImplementedError
    - diff(ctx: PluginContext) raises NotImplementedError

    - Test: AnalogDevice instance has .id, .name, .config attributes
    - Test: AnalogDevice satisfies Device Protocol (runtime check via isinstance with Protocol or structural check)
    - Test: AnalogDevice.plan(ctx) raises NotImplementedError
    - Test: AnalogDevice.diff(ctx) raises NotImplementedError
    - Test: AnalogDevice.apply() in dry_run mode returns status="skipped"
    - Test: AnalogDevice.apply() with confirm response returns status="confirmed" and updates state
    - Test: AnalogDevice.apply() with quit response returns status="error" with error="quit"
    - Test: MidiDevice same Protocol compliance tests
    - Test: MidiDevice.apply() in dry_run returns status="skipped"
    - Test: MidiDevice.apply() with confirm response returns status="confirmed"
  </behavior>
  <action>
    Create `src/rig/engine/devices.py`:
    1. Import Device Protocol, DeviceApplyContext, PluginContext from plugin.py
    2. Import DeviceApplyResult, update_device_state from appliers/base.py
    3. Import model types (ManualConfig, MidiConfig, etc.) from models/device.py
    4. Define AnalogDevice(BaseModel) with fields matching Device model + apply/plan/diff methods
       - Copy apply logic verbatim from AnalogApplier.apply_scene, replacing (action, ctx: ApplyContext) with (ctx: DeviceApplyContext)
       - Access action fields via ctx.action (e.g. ctx.action.device, ctx.action.preset_name)
    5. Define MidiDevice(BaseModel) similarly
       - Copy apply logic from MidiApplier.apply_scene

    Create `tests/test_devices.py` with Protocol compliance and behavior tests.
    Use InMemoryConfirmationIO from tests/fakes.py for confirmation_io in tests.
  </action>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create ChaseBlissDevice and MC6Device in devices.py</name>
  <files>src/rig/engine/devices.py, tests/test_devices.py</files>
  <behavior>
    ChaseBlissDevice:
    - config typed as ChaseBlissConfig
    - apply(ctx: DeviceApplyContext) handles the scene-level apply (same as MidiApplier.apply_scene since CBA uses MIDI PC for scene switching)
    - ChaseBlissApplier.apply_setup remains in appliers/chase_bliss.py for the 3-phase CBA setup flow — Phase 4 does NOT migrate setup logic into ChaseBlissDevice (it is deferred; apply.py will continue to call get_cba_applier().apply_setup() for setup in P3 migration)
    - plan/diff raise NotImplementedError

    MC6Device:
    - config typed as ControllerConfig
    - apply(ctx: DeviceApplyContext) wraps MC6Applier.apply_banks logic:
      reads banks from ctx.rig.controller.config.banks
      calls midi SysEx send per bank
      returns DeviceApplyResult summarizing outcome
    - plan/diff raise NotImplementedError

    - Test: ChaseBlissDevice.apply() in dry_run returns status="skipped"
    - Test: ChaseBlissDevice.apply() confirm path returns status="confirmed"
    - Test: MC6Device satisfies Device Protocol
    - Test: MC6Device.apply() in dry_run returns status="skipped"
    - Test: MC6Device.apply() with no MIDI returns status="skipped"
    - Test: MC6Device.plan() raises NotImplementedError
    - Test: MC6Device.diff() raises NotImplementedError
  </behavior>
  <action>
    In `src/rig/engine/devices.py` (extend file from Task 1):
    1. Add ChaseBlissDevice(BaseModel): config: ChaseBlissConfig, copy MidiApplier.apply_scene for apply()
    2. Add MC6Device(BaseModel): config: ControllerConfig, inline MC6Applier.apply_banks for apply()
       - MC6 apply: if dry_run or no midi, return skipped; else iterate banks and send SysEx
       - Import MC6 SysEx helpers from rig.midi.mc6 as needed
    3. All four types must be exported at module level

    Extend `tests/test_devices.py` with ChaseBliss and MC6 tests.
    Use InMemoryMidiConnectionIO and InMemoryStateAdapter from fakes.py as needed.
  </action>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Register all four types in a module-level default PluginRegistry</name>
  <files>src/rig/engine/plugin_registry.py</files>
  <behavior>
    Create a module-level `_registry` instance of PluginRegistry and register all four concrete device types by their config_type strings:
    - "manual" → AnalogDevice
    - "midi" → MidiDevice
    - "chase_bliss" → ChaseBlissDevice
    - "controller" → MC6Device

    Expose a `get_registry() -> PluginRegistry` function that returns the default registry.
    This is the single wiring point; loader.py and apply.py import it.

    Avoid circular imports: devices.py imports from plugin.py (Device Protocol), but plugin_registry.py imports from devices.py for registration. This creates: plugin_registry → devices → plugin. plugin.py must NOT import from plugin_registry.py.
  </behavior>
  <action>
    In `src/rig/engine/plugin_registry.py`:
    1. At module bottom (after PluginRegistry class definition), create:
       ```python
       from rig.engine.devices import AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device
       _registry = PluginRegistry()
       _registry.register_model("manual", AnalogDevice)
       _registry.register_model("midi", MidiDevice)
       _registry.register_model("chase_bliss", ChaseBlissDevice)
       _registry.register_model("controller", MC6Device)

       def get_registry() -> PluginRegistry:
           return _registry
       ```
    2. Verify: `python -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(r.get_model('midi'))"` prints MidiDevice class
  </action>
</task>

</tasks>

<success_criteria>
- `uv run pytest tests/test_devices.py -v` all pass
- `uv run pytest tests/test_plugin.py -v` still passes
- `python -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); assert r.get_model('manual') is not None"` exits 0
- All four concrete types have apply() methods that replicate existing applier behavior
- All four concrete types have plan() and diff() that raise NotImplementedError
- No circular import errors: `python -c "from rig.engine.devices import AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device"` exits 0
- Existing test suite still passes: `uv run pytest tests/ -q` (no regressions)
</success_criteria>
