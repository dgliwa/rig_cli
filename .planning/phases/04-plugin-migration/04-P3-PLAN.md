---
phase: 4
plan: P3
type: execute
wave: 3
depends_on: [P1, P2]
files_modified:
  - src/rig/config/loader.py
  - src/rig/engine/apply.py
  - src/rig/engine/appliers/registry.py
  - src/rig/engine/appliers/analog.py
  - src/rig/engine/appliers/midi_device.py
  - src/rig/engine/appliers/chase_bliss.py
  - src/rig/engine/appliers/mc6.py
  - tests/test_loader.py
  - tests/test_apply.py
  - tests/test_appliers.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "loader.py uses registry.get_model(config_type) to parse device YAML instead of Device(**data) discriminated union"
    - "apply.py routes scene actions through device.apply(ctx) — no get_scene_applier() call remains"
    - "apply.py has no import from rig.engine.appliers.registry (get_cba_applier, get_mc6_applier, get_scene_applier)"
    - "MC6 programming phase in apply.py calls mc6_device.apply(ctx) instead of get_mc6_applier().apply_banks()"
    - "CBA setup phase in apply.py still calls ChaseBlissApplier.apply_setup (setup migration deferred)"
    - "Old applier files (analog.py, midi_device.py, mc6.py, registry.py) are deleted"
    - "appliers/chase_bliss.py is kept (apply_setup still used by apply.py for CBA 3-phase setup)"
    - "appliers/base.py is kept (DeviceApplyResult, update_device_state, mark_preset_saved still used)"
    - "All tests pass: uv run pytest tests/ -q"
  artifacts:
    - path: "src/rig/config/loader.py"
      provides: "Registry-driven device YAML dispatch"
      contains: "get_model"
    - path: "src/rig/engine/apply.py"
      provides: "Device-Protocol routing with no direct applier imports"
      contains: "device.apply"
  key_links:
    - from: "src/rig/config/loader.py"
      to: "src/rig/engine/plugin_registry.py"
      via: "get_registry().get_model(config_type)"
      pattern: "from rig.engine.plugin_registry import get_registry"
    - from: "src/rig/engine/apply.py"
      to: "src/rig/engine/plugin.py"
      via: "DeviceApplyContext construction"
      pattern: "from rig.engine.plugin import DeviceApplyContext"
---

<objective>
Wire the plugin architecture end-to-end: update loader.py to use registry-driven dispatch for YAML parsing, update apply.py to route through device.apply(ctx), and delete the old applier files that are superseded (except base.py and chase_bliss.py).

This is the finishing wave. After P3, no direct applier imports remain in apply.py or CLI, and the test suite proves behavior is preserved.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-plugin-migration/04-CONTEXT.md
@src/rig/config/loader.py
@src/rig/engine/apply.py
@src/rig/engine/appliers/registry.py
@src/rig/engine/appliers/chase_bliss.py
@src/rig/engine/appliers/base.py
@src/rig/engine/plugin.py
@src/rig/engine/plugin_registry.py
@src/rig/engine/devices.py
@tests/test_loader.py
@tests/test_apply.py
@tests/test_appliers.py
@tests/fakes.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update loader.py to use registry-driven device YAML dispatch</name>
  <files>src/rig/config/loader.py, tests/test_loader.py</files>
  <behavior>
    Replace the pattern `Device(**device_data)` (which relies on Pydantic's discriminated union on the config field) with registry-driven dispatch:
    1. Read `config_type = device_data.get("config", {}).get("type")` from raw YAML dict
    2. Call `model_class = get_registry().get_model(config_type)`
    3. If model_class is None, raise a ValidationError with clear message: "Unknown device config type '{config_type}' — is the plugin registered?"
    4. Call `model_class(**device_data)` to construct the concrete device instance

    The returned device instance is one of AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device.
    `Rig.devices` field must accommodate these concrete types. Update the type annotation on Rig.devices or use model_config = ConfigDict(arbitrary_types_allowed=True) if Pydantic complains.

    - Test: loading a device with config.type="manual" produces an AnalogDevice instance
    - Test: loading a device with config.type="midi" produces a MidiDevice instance
    - Test: loading a device with config.type="chase_bliss" produces a ChaseBlissDevice instance
    - Test: loading a device with config.type="controller" produces an MC6Device instance
    - Test: loading a device with an unknown config type raises ValidationError with descriptive message
    - Test: full sample_rig loads without error and rig.devices has the right concrete types
    - Test: existing loader tests still pass
  </behavior>
  <action>
    In `src/rig/config/loader.py`:
    1. Add `from rig.engine.plugin_registry import get_registry`
    2. In `_parse_device(data)` (or equivalent function): replace `Device(**data)` with registry dispatch
    3. Import `ValidationError` from `rig.config.errors` for the unknown-type case

    In `src/rig/models/rig.py`:
    - If Pydantic validation fails for `devices: dict[str, Device]` after concrete types replace Device instances,
      change annotation to `devices: dict[str, Any]` and add `model_config = ConfigDict(arbitrary_types_allowed=True)`
      OR use a union type `dict[str, AnalogDevice | MidiDevice | ChaseBlissDevice | MC6Device]`
      Choose the option that keeps test_models.py passing

    Update `tests/test_loader.py`:
    - Add assertion that loaded devices are concrete type instances (e.g. isinstance(device, MidiDevice))
  </action>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Update apply.py to route through device.apply(ctx)</name>
  <files>src/rig/engine/apply.py, tests/test_apply.py</files>
  <behavior>
    Remove all imports from `rig.engine.appliers.registry`. The scene apply loop changes from:
    ```python
    applier = get_scene_applier(config_type)
    action_result = applier.apply_scene(action, ctx)
    ```
    to:
    ```python
    device = rig.devices.get(action.device)
    device_ctx = DeviceApplyContext(
        action=action,
        state=ctx.state,
        rig=rig,
        dry_run=ctx.dry_run,
        confirmation_io=ctx.confirmation_io,
        midi=ctx.midi,
        connected_devices=ctx.connected_devices,
        config_path=ctx.config_path,
    )
    action_result = device.apply(device_ctx)
    ```

    MC6 programming phase changes from:
    ```python
    get_mc6_applier().apply_banks(mc6_banks, ctx)
    ```
    to:
    ```python
    mc6_device = rig.controller  # the MC6Device instance
    if mc6_device:
        mc6_ctx = DeviceApplyContext(action=..., ...)
        mc6_device.apply(mc6_ctx)
    ```
    (MC6 apply reads banks from its own config via ctx.rig, so action can be a sentinel/None-like value)

    CBA setup phase KEEPS calling `get_cba_applier().apply_setup(plan.cba_setup, ctx)` — this is explicitly deferred per CONTEXT.md.

    - Test: apply_plan with a midi device calls device.apply() not get_scene_applier()
    - Test: apply_plan with an analog device calls device.apply()
    - Test: apply_plan dry_run still works end-to-end
    - Test: all existing test_apply.py tests still pass
  </behavior>
  <action>
    In `src/rig/engine/apply.py`:
    1. Remove: `from rig.engine.appliers.registry import get_cba_applier, get_mc6_applier, get_scene_applier`
    2. Add: `from rig.engine.plugin import DeviceApplyContext`
    3. Keep: `from rig.engine.appliers.chase_bliss import ChaseBlissApplier` (or keep get_cba_applier import for setup only)
    4. Rewrite scene apply loop to use device.apply(device_ctx)
    5. Rewrite MC6 programming phase to use mc6_device.apply(...)
    6. Keep CBA setup phase via get_cba_applier().apply_setup() unchanged

    Note: if device is None (unknown device ID in action), fall back to a no-op DeviceApplyResult(status="skipped") with a warning log.
  </action>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Delete superseded applier files and update test_appliers.py</name>
  <files>
    src/rig/engine/appliers/registry.py,
    src/rig/engine/appliers/analog.py,
    src/rig/engine/appliers/midi_device.py,
    src/rig/engine/appliers/mc6.py,
    tests/test_appliers.py
  </files>
  <behavior>
    Delete the four applier files whose logic has moved into concrete device types:
    - `src/rig/engine/appliers/registry.py` — superseded by plugin_registry.py
    - `src/rig/engine/appliers/analog.py` — logic in AnalogDevice.apply()
    - `src/rig/engine/appliers/midi_device.py` — logic in MidiDevice.apply()
    - `src/rig/engine/appliers/mc6.py` — logic in MC6Device.apply()

    Keep:
    - `src/rig/engine/appliers/chase_bliss.py` — apply_setup still used by apply.py
    - `src/rig/engine/appliers/base.py` — DeviceApplyResult, update_device_state, mark_preset_saved still used

    Update `tests/test_appliers.py`:
    - Remove tests for AnalogApplier, MidiApplier, MC6Applier (those classes are deleted)
    - Keep or migrate any coverage that tests behavior now in devices.py to test_devices.py
    - Keep ChaseBlissApplier setup tests

    Verify no remaining imports of deleted modules in the codebase:
    - `grep -r "from rig.engine.appliers.registry import" src/` should return nothing
    - `grep -r "from rig.engine.appliers.analog import" src/` should return nothing
    - `grep -r "from rig.engine.appliers.midi_device import" src/` should return nothing
    - `grep -r "from rig.engine.appliers.mc6 import" src/` should return nothing (except mc6 SysEx helpers if those live in midi/mc6.py not appliers/mc6.py)
  </behavior>
  <action>
    1. Delete: src/rig/engine/appliers/registry.py
    2. Delete: src/rig/engine/appliers/analog.py
    3. Delete: src/rig/engine/appliers/midi_device.py
    4. Delete: src/rig/engine/appliers/mc6.py
    5. Update tests/test_appliers.py: remove tests for deleted classes, keep CBA tests
    6. Run grep checks above to confirm no dangling imports
    7. Run full test suite: uv run pytest tests/ -q
  </action>
</task>

</tasks>

<success_criteria>
- `uv run pytest tests/ -q` passes with 0 failures
- `grep -r "get_scene_applier\|get_mc6_applier" src/` returns nothing
- `grep -r "from rig.engine.appliers.registry import" src/` returns nothing
- `grep -r "from rig.engine.appliers.analog import" src/` returns nothing
- `grep -r "from rig.engine.appliers.midi_device import" src/` returns nothing
- `ls src/rig/engine/appliers/` shows only: __init__.py, base.py, chase_bliss.py (and __pycache__)
- Device YAML loading via loader.py produces concrete device type instances (AnalogDevice, MidiDevice, etc.)
- apply.py applies a scene by calling device.apply(ctx) with no isinstance dispatch
- End-to-end integration: `uv run pytest tests/test_apply.py tests/test_loader.py -v` all pass
</success_criteria>
