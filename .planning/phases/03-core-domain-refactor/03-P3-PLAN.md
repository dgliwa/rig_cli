---
phase: 3
plan: P3
type: execute
wave: 3
depends_on: [03-P1, 03-P2]
files_modified:
  - src/rig/config/loader.py
  - tests/test_loader.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "loader.py routes YAML devices with config.type==controller through _parse_device (not legacy controller path)"
    - "load_rig() no longer passes controller= or scenes= fields to Rig constructor"
    - "After loading, scenes from the scenes/ directory are injected into the Controller device's ControllerConfig"
    - "rig.scenes works via compat shim after load_rig()"
    - "_parse_controller_legacy is removed or clearly marked dead with TODO: remove"
    - "test_loader.py adds a Controller-as-device test (rig_dir writes devices/mc6.yaml)"
    - "All existing loader tests pass"
  artifacts:
    - path: "src/rig/config/loader.py"
      provides: "Updated loader that builds Controller as Device"
      contains: "ControllerConfig"
    - path: "tests/test_loader.py"
      provides: "Tests for controller-as-device loading and scenes compat via loader"
      contains: "controller_as_device"
  key_links:
    - from: "src/rig/config/loader.py"
      to: "src/rig/models/device.py"
      via: "Device(**data) handles type: controller via discriminated union"
      pattern: "_parse_device"
    - from: "src/rig/config/loader.py"
      to: "src/rig/models/rig.py"
      via: "Rig constructor no longer receives controller= or scenes="
      pattern: "Rig("
---

<objective>
Update load_rig() and _load_devices_dir() so the Controller is loaded as a Device (via the discriminated union introduced in P1) instead of via _parse_controller_legacy. Remove the separate controller.yaml / mc6.yaml loading paths. Inject scenes loaded from the scenes/ directory into the Controller device's ControllerConfig after loading. Remove the Controller, ControllerType, MC6Config imports from loader.py.

Purpose: The loader is the last caller that constructs the old Controller model. After this plan, the full data path from YAML → Rig uses the new device graph model. All compat shims in Rig (from P2) remain in place so engine and CLI callers require no changes.

Output: Updated loader.py with scene injection; updated test_loader.py with controller-as-device tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-core-domain-refactor/03-CONTEXT.md
@.planning/phases/03-core-domain-refactor/03-RESEARCH.md
@.planning/phases/03-core-domain-refactor/03-P1-SUMMARY.md
@.planning/phases/03-core-domain-refactor/03-P2-SUMMARY.md
@src/rig/config/loader.py
@src/rig/models/device.py
@src/rig/models/rig.py
@tests/test_loader.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update loader — route controller YAML through _parse_device + scene injection</name>
  <files>src/rig/config/loader.py</files>
  <behavior>
    - Test (pre-existing): load_rig() with a rig_dir containing a controller device in devices/ puts that device in rig.devices
    - Test (pre-existing): rig.scenes returns scenes loaded from scenes/ dir via compat shim
    - Test (new): rig.devices contains the controller device when devices/mc6.yaml has type: controller
    - Test (new): rig.controller returns a Device with type==CONTROLLER after load_rig()
    - Test (new): rig.scenes returns the scenes injected into ControllerConfig after load_rig()
    - Test (new): rig.controller.config.banks contains the banks from the controller YAML
  </behavior>
  <action>
In src/rig/config/loader.py, make the following changes:

1. Remove from the imports:
   - `from rig.models.controller import Controller, ControllerType, MC6Config`

2. Add to the imports:
   - `from rig.models.device import ChaseBlissConfig, ControllerConfig, Device, DeviceType` (ControllerConfig is new)

3. Update _load_devices_dir signature and body:
   - Remove the `mc6_data: dict` parameter (no longer needed — the controller YAML is self-contained)
   - Change return type from `tuple[dict[str, Device], Controller | None]` to `dict[str, Device]`
   - Remove the `controller: Controller | None = None` local variable
   - Remove the `if data.get("type") == "controller": controller = _parse_controller_legacy(...)` branch
   - Let _parse_device(data) handle ALL YAML files including those with type: controller (Pydantic discriminator takes care of it)
   - Return just `devices` (not a tuple)
   - Keep the logger.debug calls, update the log for each device to show type

4. Remove _parse_controller_legacy entirely (or mark it `# TODO: remove — replaced by _parse_device + ControllerConfig discriminated union` if you want to leave a breadcrumb, but removal is preferred per D-06).

5. Update load_rig() in the following ways:
   a. Remove the controller_path / mc6_path loading block (lines ~210-221 in the original). This entire section:
      ```
      controller_path = _resolve(root, "controller.yaml")
      mc6_path = _resolve(root, "mc6.yaml")
      if controller_path.exists(): ...
      else: mc6_data = ...; devices, controller = _load_devices_dir(...)
      ```
      ...is replaced by a single call: `devices = _load_devices_dir(devices_dir)`

   b. Keep `devices = _merge_presets(devices_dir, devices)` unchanged.

   c. Keep `scenes = _load_scenes(scenes_dir)` unchanged — scenes are still loaded from their YAML directory.

   d. Add scene injection after loading: iterate devices.values(), find any device with type==DeviceType.CONTROLLER, and use model_copy to inject the scenes into its ControllerConfig:
      ```python
      for device_id, device in list(devices.items()):
          if device.type == DeviceType.CONTROLLER and isinstance(device.config, ControllerConfig):
              updated_config = device.config.model_copy(update={"scenes": scenes})
              devices[device_id] = device.model_copy(update={"config": updated_config})
              break
      ```
      Use model_copy (not direct mutation) — Pydantic v2 models are immutable by default.

   e. Update the Rig(...) constructor call to remove `controller=controller` and `scenes=scenes` kwargs (those fields no longer exist on Rig). Keep name, description, midi_channel, signal_chain, devices.

   f. The logger.info completion log (`"Rig '%s' loaded successfully (%d devices, %d scenes)"`) should continue to work because len(rig.scenes) uses the compat property. No change needed there.

6. Update _validate_references:
   - The line `controller_id = rig.controller.id if rig.controller else None` now returns a Device|None from the compat property. Device has an .id attribute, so this still works.
   - `valid_chain_ids = device_ids | ({controller_id} if controller_id else set())` — but after Phase 3, the controller IS in rig.devices (it has a device ID), so it's already in device_ids. The controller_id inclusion is now redundant but harmless. Leave it as-is to avoid regressions.
   - `rig.scenes.items()` works via compat property. No change needed.
  </action>
  <verify>
    <automated>uv run pytest tests/test_loader.py -q 2>&1 | tail -15</automated>
  </verify>
  <done>test_loader.py passes. loader.py no longer imports Controller/ControllerType/MC6Config. _parse_controller_legacy is gone. _load_devices_dir returns dict (not tuple).</done>
</task>

<task type="auto">
  <name>Task 2: Update test_loader.py — add controller-as-device fixture and tests</name>
  <files>tests/test_loader.py</files>
  <action>
In tests/test_loader.py, make the following changes:

1. Update the rig_dir fixture to add a controller device YAML. The existing fixture uses the old pedals/ layout with no controller. Add a controller device file to the fixture:
   ```python
   _write(
       d,
       "pedals/mc6.yaml",
       "id: mc6\nmanufacturer: Morningstar\nmodel: MC6\ntype: controller\n"
       "config:\n  type: controller\n  midi_channel: 1\n  banks: []\n",
   )
   ```
   Note: use pedals/ (not devices/) because the existing rig_dir uses pedals/ directory. The loader supports both pedals/ and devices/ via the existing fallback.

2. Add a test_loads_controller_as_device test method in TestLoadRig that:
   - Calls load_rig(str(rig_dir))
   - Asserts "mc6" in config.devices
   - Asserts config.devices["mc6"].type.value == "controller"
   - Asserts config.controller is not None
   - Asserts config.controller.id == "mc6"

3. Add a test_scenes_accessible_via_controller test method that:
   - Calls load_rig(str(rig_dir))
   - Asserts "billy-clean" in config.scenes (via compat shim — scenes were injected into controller config)
   - This test passes because: the rig_dir fixture writes scenes/billy-clean.yaml, the loader loads it, and injects it into the mc6 controller's ControllerConfig.scenes

4. Check whether any existing test in test_loader.py constructs Rig or Controller directly with the old fields. If so, update those constructions. Most tests call load_rig() and assert on the result, so they should work via the compat shim. The key one is the test_loads_scenes test (which asserts "billy-clean" in config.scenes) — this should still pass because of the compat property.

5. Run the full suite after changes:
   uv run pytest tests/ -q

   All 167+ tests must pass. The controller-as-device tests are additive.
  </action>
  <verify>
    <automated>uv run pytest tests/ -q 2>&1 | tail -15</automated>
  </verify>
  <done>Full suite passes (167+ tests). test_loader.py has tests for controller-as-device loading and scenes accessible via compat shim. loader.py is clean of Controller/ControllerType/MC6Config imports.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML → Device | YAML with type: controller is validated by Pydantic discriminated union |
| Scene injection | model_copy is used; no mutable state shared across model instances |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03P3-01 | Tampering | Scene injection in loader | mitigate | Use device.model_copy(update={"config": ...}) not direct field mutation; Pydantic v2 model immutability enforced |
| T-03P3-02 | Information Disclosure | _validate_references sees controller in devices | accept | Controller device in rig.devices.keys() is expected and correct; validation still works |
| T-03P3-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in Phase 3 |
</threat_model>

<verification>
Run full suite to confirm loader + model changes are regression-free:

```
uv run pytest tests/ -q
```

Expected: 167+ tests pass.

Spot-check loader end-to-end via a temp directory:
```
uv run python -c "
from rig.config.loader import load_rig
import tempfile, os, pathlib
d = pathlib.Path(tempfile.mkdtemp()) / 'rig'
d.mkdir()
(d / 'rig.yaml').write_text('name: test\n')
(d / 'signal-chain.yaml').write_text('chain: []\n')
(d / 'devices').mkdir()
(d / 'devices' / 'mc6.yaml').write_text(
  'id: mc6\nmanufacturer: Morningstar\nmodel: MC6\ntype: controller\n'
  'config:\n  type: controller\n  midi_channel: 1\n  banks: []\n'
)
(d / 'scenes').mkdir()
rig = load_rig(str(d))
print('controller id:', rig.controller.id if rig.controller else None)
print('devices:', list(rig.devices.keys()))
print('scenes:', list(rig.scenes.keys()))
"
```
Expected: `controller id: mc6`, `devices: ['mc6']`, `scenes: []`
</verification>

<success_criteria>
- loader.py has no import of Controller, ControllerType, or MC6Config
- _parse_controller_legacy is removed from loader.py
- _load_devices_dir returns dict[str, Device] (not a tuple)
- load_rig() calls Rig(...) without controller= or scenes= kwargs
- Scenes are injected into ControllerConfig via model_copy after loading
- test_loader.py passes with new controller-as-device tests
- Full suite: 167+ tests pass
</success_criteria>

<output>
Create `.planning/phases/03-core-domain-refactor/03-P3-SUMMARY.md` when done
</output>
