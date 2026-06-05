---
phase: 3
plan: P2
type: execute
wave: 2
depends_on: [03-P1]
files_modified:
  - src/rig/models/rig.py
  - tests/test_models.py
  - tests/test_mc6_generator.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Rig no longer has controller or scenes as Pydantic fields"
    - "Rig.scenes property returns scenes from ControllerConfig when a CONTROLLER device exists"
    - "Rig.controller property returns the Device with type==CONTROLLER, or None"
    - "Rig.apply_order() returns non-controller devices in signal-chain position order, then Controller last"
    - "Rig.apply_order() with no controller returns devices sorted by signal-chain position"
    - "All existing tests pass including test_mc6_generator.py after _make_rig() is updated"
  artifacts:
    - path: "src/rig/models/rig.py"
      provides: "apply_order() method + scenes/controller compat properties"
      contains: "apply_order"
    - path: "tests/test_models.py"
      provides: "apply_order tests + rig_scenes_compat test"
      contains: "apply_order"
    - path: "tests/test_mc6_generator.py"
      provides: "Updated _make_rig() fixture that places Controller in devices dict"
      contains: "DeviceType.CONTROLLER"
  key_links:
    - from: "src/rig/models/rig.py"
      to: "src/rig/models/device.py"
      via: "DeviceType.CONTROLLER + ControllerConfig import"
      pattern: "DeviceType.CONTROLLER"
    - from: "Rig.scenes property"
      to: "ControllerConfig.scenes"
      via: "rig._controller_device.config.scenes"
      pattern: "_controller_device"
---

<objective>
Remove the `controller` and `scenes` Pydantic fields from Rig, add backward-compat properties for both (per D-05), and add the `apply_order()` DFS method (per D-02, D-03). Fix the two test files that break because they construct `Rig(controller=..., scenes=...)` directly.

Purpose: Rig becomes the device graph per D-01. The compat properties ensure all downstream callers (engine, CLI, generators) continue to work without changes — rig.scenes and rig.controller still resolve correctly via the new properties.

Output: Updated rig.py with apply_order + compat properties; updated test_models.py and test_mc6_generator.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-core-domain-refactor/03-CONTEXT.md
@.planning/phases/03-core-domain-refactor/03-RESEARCH.md
@.planning/phases/03-core-domain-refactor/03-P1-SUMMARY.md
@src/rig/models/rig.py
@src/rig/models/device.py
@tests/test_models.py
@tests/test_mc6_generator.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update Rig model — remove fields, add compat properties + apply_order()</name>
  <files>src/rig/models/rig.py, tests/test_models.py</files>
  <behavior>
    - Test: Rig(name="t", signal_chain=[]) constructs without error (no controller or scenes args required)
    - Test: Rig.scenes returns {} when no CONTROLLER device in devices dict
    - Test: Rig.scenes returns the ControllerConfig.scenes dict when a CONTROLLER device is present
    - Test: Rig.controller returns None when no CONTROLLER device exists
    - Test: Rig.controller returns the Device with type==CONTROLLER when one exists
    - Test: apply_order() with empty devices/signal_chain returns []
    - Test: apply_order() with two devices (positions 1, 2) and no controller returns them in ascending position order
    - Test: apply_order() with two devices + controller device returns non-controller devices in chain order, then controller last
    - Test: apply_order() device not in signal_chain appears after chain-ordered devices (before controller)
  </behavior>
  <action>
In src/rig/models/rig.py, make the following changes:

1. Remove the `controller: Controller | None = None` Pydantic field.

2. Remove the `scenes: dict[str, Scene] = {}` Pydantic field.

3. Remove the import `from rig.models.controller import Controller`. Keep the import of `Device` (already there via device.py).

4. Add imports needed for the new properties:
   - `from rig.models.device import ControllerConfig, DeviceType` (ControllerConfig is new from P1)
   - Keep `from rig.models.scene import Scene` if not already there (needed for the scenes property return type annotation)

5. Add a private helper property `_controller_device` that returns the first Device with type==DeviceType.CONTROLLER from self.devices.values(), or None.

6. Add a `scenes` property (replacing the removed field) that:
   - Calls self._controller_device
   - If found and its config is ControllerConfig, returns ctrl.config.scenes
   - Otherwise returns {}
   - Return type annotation: dict[str, Scene]

7. Add a `controller` property (replacing the removed field) that:
   - Returns self._controller_device (Device | None)
   - Return type annotation: Device | None
   - This preserves rig.controller access for engine/apply.py (rig.controller.config.banks still works because ControllerConfig has banks)

8. Add `apply_order() -> list[Device]` method per D-03:
   - Find the controller via self._controller_device
   - Build a chain_order dict mapping device_ref -> position from self.signal_chain
   - Separate non-controller devices from the controller device
   - Sort non-controller devices: first those in the signal chain (by position ascending), then those NOT in the signal chain (by dict insertion order / append order)
   - Return sorted_non_controllers + [controller] if controller exists, else just sorted_non_controllers
   - If devices dict is empty, return []

9. Update the existing `mc6` property if it uses `self.controller.config.banks` to instead use `self._controller_device` and check isinstance(ctrl.config, ControllerConfig).

In tests/test_models.py, update the test_rig_config_with_scenes test:
- Old: Rig(name="Test", signal_chain=[], scenes={"test": scene}) — this will break
- New: Build a Device with DeviceType.CONTROLLER and ControllerConfig(scenes={"test": scene}), then construct Rig with devices={"mc6": controller_device}. Assert rig.scenes["test"].name == "test" via the compat property.

Add new test methods for apply_order (see behavior block above). Import ControllerConfig, DeviceType from rig.models.device.
  </action>
  <verify>
    <automated>uv run pytest tests/test_models.py -q 2>&1 | tail -15</automated>
  </verify>
  <done>test_models.py passes fully. New apply_order and scenes compat tests pass. Rig no longer accepts controller= or scenes= constructor args. rig.scenes and rig.controller still work via properties.</done>
</task>

<task type="auto">
  <name>Task 2: Fix test_mc6_generator.py _make_rig() — move Controller into devices dict</name>
  <files>tests/test_mc6_generator.py</files>
  <action>
In tests/test_mc6_generator.py, update _make_rig() so it builds the Rig in the new way (Controller as a Device in the devices dict, scenes on ControllerConfig) per D-05.

Current _make_rig() constructs a Controller via the old model and passes controller= and scenes= to Rig. Both of those Rig fields are gone after Task 1.

New _make_rig() must:

1. Import ControllerConfig and DeviceType from rig.models.device (add to existing imports). Keep the existing imports of Controller, ControllerType, MC6Config from rig.models.controller — they are tested elsewhere and keeping the import proves the re-export still works. But _make_rig() will NOT use Controller() to build the rig anymore.

2. Build the controller device as:
   - Device(id="mc6", manufacturer="Morningstar", model="MC6", type=DeviceType.CONTROLLER, config=ControllerConfig(midi_channel=1, banks=[...same banks as before...], scenes={...same scenes as before...}))
   - The scenes dict contains the two Scene objects that were previously passed to Rig(scenes=...).

3. Build the Rig with:
   - devices={"hx-stomp": hx, "mc6": controller_device}
   - Remove controller= and scenes= kwargs (they no longer exist on Rig)
   - Keep signal_chain, name unchanged

4. Update the test_no_mc6_config_returns_empty test: it constructs Rig with controller=None which no longer exists. Change it to: Rig(name="test", signal_chain=[], devices={}) — no controller device in devices means rig.scenes == {} and rig.controller == None, which is what generate_mc6 checks.

After this change, all test_mc6_generator.py tests should pass because:
- generate_mc6 accesses rig.scenes and rig.controller.config.banks via the compat properties on Rig
- rig.scenes returns ControllerConfig.scenes (the two Scene objects)
- rig.controller returns the mc6 Device, whose config.banks has the bank definitions
  </action>
  <verify>
    <automated>uv run pytest tests/test_mc6_generator.py tests/test_models.py tests/test_diff.py tests/test_plan.py -q 2>&1 | tail -15</automated>
  </verify>
  <done>test_mc6_generator.py passes. test_diff.py and test_plan.py pass (compat shim covers rig.scenes access in those engines). Full suite: uv run pytest tests/ -q shows 167+ passing.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Rig.scenes property | Returns data from ControllerConfig; no external input crosses here |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03P2-01 | Information Disclosure | Rig.scenes fallback | accept | Returns empty dict when no controller — correct behavior, no data leakage |
| T-03P2-02 | Tampering | apply_order DFS loop | accept | signal_chain positions are validated by loader; no external input in Phase 3 |
| T-03P2-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in Phase 3 |
</threat_model>

<verification>
Run the full test suite to confirm no regressions from Rig field removal:

```
uv run pytest tests/ -q
```

Expected: 167+ tests pass (new tests added on top of baseline).

Verify compat properties work end-to-end:
```
uv run python -c "
from rig.models.device import Device, DeviceType, ControllerConfig
from rig.models.rig import Rig
from rig.models.scene import Scene
ctrl = Device(id='mc6', manufacturer='Morningstar', model='MC6', type=DeviceType.CONTROLLER,
    config=ControllerConfig(scenes={'s1': Scene(name='s1', presets={})}))
rig = Rig(name='t', signal_chain=[], devices={'mc6': ctrl})
print('scenes:', list(rig.scenes.keys()))
print('controller id:', rig.controller.id)
print('apply_order:', [d.id for d in rig.apply_order()])
"
```
Expected: `scenes: ['s1']`, `controller id: mc6`, `apply_order: ['mc6']`
</verification>

<success_criteria>
- Rig does NOT accept controller= or scenes= as constructor kwargs (Pydantic fields removed)
- rig.scenes returns {} when no controller device, returns ControllerConfig.scenes when present
- rig.controller returns Device|None (not Controller|None)
- apply_order() returns non-controller devices in ascending signal-chain position, controller device last
- All 167+ tests pass including test_mc6_generator.py (after _make_rig() update) and test_diff.py, test_plan.py (via compat shim)
</success_criteria>

<output>
Create `.planning/phases/03-core-domain-refactor/03-P2-SUMMARY.md` when done
</output>
