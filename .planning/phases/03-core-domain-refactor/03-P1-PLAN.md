---
phase: 3
plan: P1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/rig/models/device.py
  - src/rig/models/controller.py
  - tests/fixtures/sample_rig/devices/mc6.yaml
  - tests/fixtures/sample_rig/controller.yaml
autonomous: true
requirements: []
must_haves:
  truths:
    - "DeviceType.CONTROLLER exists with value 'controller'"
    - "ControllerConfig parses via the DeviceConfig discriminated union"
    - "Device with type=controller and config.type=controller round-trips through Pydantic"
    - "controller.py re-exports ControllerType, MC6Config, Controller so existing imports keep working"
    - "Sample rig fixture has devices/mc6.yaml with type: controller (no top-level controller.yaml)"
  artifacts:
    - path: "src/rig/models/device.py"
      provides: "DeviceType.CONTROLLER + ControllerConfig class + extended discriminated union"
      contains: "CONTROLLER"
    - path: "src/rig/models/controller.py"
      provides: "Backward-compat re-exports of ControllerType, MC6Config, Controller"
      contains: "ControllerType"
    - path: "tests/fixtures/sample_rig/devices/mc6.yaml"
      provides: "Controller-as-device fixture YAML"
      contains: "type: controller"
  key_links:
    - from: "src/rig/models/device.py"
      to: "src/rig/models/scene.py"
      via: "ControllerConfig.scenes field import"
      pattern: "from rig.models.scene import Scene"
    - from: "src/rig/models/controller.py"
      to: "src/rig/models/device.py"
      via: "re-export of ControllerConfig"
      pattern: "from rig.models.device import ControllerConfig"
---

<objective>
Add ControllerConfig to the DeviceConfig discriminated union and DeviceType.CONTROLLER to the enum so a YAML device with `config.type: controller` deserializes into a first-class Device model. Update controller.py as a backward-compat re-export shim so all existing test imports continue to work. Migrate the sample_rig fixture to the new Controller-as-device layout.

Purpose: Establishes the model foundation that Wave 2 (Rig.apply_order) and Wave 3 (loader) depend on. No existing tests should break — all structural additions only.

Output: Extended device.py with ControllerConfig, compat controller.py shim, updated fixture YAML.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-core-domain-refactor/03-CONTEXT.md
@.planning/phases/03-core-domain-refactor/03-RESEARCH.md
@.planning/phases/03-core-domain-refactor/03-PATTERNS.md
@src/rig/models/device.py
@src/rig/models/controller.py
@src/rig/models/scene.py
@tests/test_models.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add ControllerConfig + DeviceType.CONTROLLER to device.py</name>
  <files>src/rig/models/device.py, tests/test_models.py</files>
  <behavior>
    - Test: DeviceType.CONTROLLER.value == "controller"
    - Test: Device with id="mc6", type=DeviceType.CONTROLLER, config={"type":"controller","midi_channel":1,"banks":[],"scenes":{}} parses without error
    - Test: ControllerConfig.scenes defaults to empty dict
    - Test: ControllerConfig.banks defaults to empty list
    - Test: Device.config discriminated union resolves ControllerConfig when config.type == "controller"
    - Test: Existing DeviceType values (DIGITAL, ANALOG, MODELER) are unchanged
  </behavior>
  <action>
In src/rig/models/device.py, make the following changes per D-04:

1. Add `from rig.models.scene import Scene` to the imports (after the preset imports). scene.py imports only from pydantic and typing — no circular risk.

2. Add `Any` to the `typing` import if not already there (it is present in the existing file).

3. Add `CONTROLLER = "controller"` to the DeviceType StrEnum, following the same UPPER_CASE = "lowercase" convention as the existing members.

4. Add a new ControllerConfig class after ChaseBlissConfig, following the Literal discriminator pattern used by ManualConfig/MidiConfig/ChaseBlissConfig:
   - Inherits from DeviceConfig
   - type: Literal["controller"] = "controller"
   - midi_channel: int = 1 (overrides DeviceConfig's `int | None` with a concrete default)
   - banks: list[dict[str, Any]] = []
   - scenes: dict[str, Scene] = {} (use Field(default_factory=dict) to avoid mutable default)

5. Extend the Device.config discriminated union to include ControllerConfig:
   - Change the Annotated type from `ManualConfig | MidiConfig | ChaseBlissConfig` to `ManualConfig | MidiConfig | ChaseBlissConfig | ControllerConfig`
   - Leave the Field(discriminator="type") unchanged

In tests/test_models.py, add tests verifying the above behavior. Follow the existing inline-construction pattern from TestPedalModels. Add to the existing test_device_type_enum_values test (add the CONTROLLER assertion) and add new test methods for ControllerConfig construction and discriminated union parsing. Import ControllerConfig from rig.models.device.
  </action>
  <verify>
    <automated>uv run pytest tests/test_models.py -q -k "controller" 2>&1 | tail -10</automated>
  </verify>
  <done>DeviceType.CONTROLLER exists, ControllerConfig parses via discriminated union, new tests pass, existing test_models.py tests still pass (run uv run pytest tests/test_models.py -q)</done>
</task>

<task type="auto">
  <name>Task 2: Update controller.py as compat shim + migrate fixture YAML</name>
  <files>src/rig/models/controller.py, tests/fixtures/sample_rig/devices/mc6.yaml, tests/fixtures/sample_rig/controller.yaml</files>
  <action>
In src/rig/models/controller.py, restructure it as a backward-compat re-export shim per the Option A recommendation in RESEARCH.md:

1. Keep ControllerType StrEnum with MC6 = "mc6" (tests/test_models.py imports this and tests/test_mc6_generator.py imports Controller, ControllerType, MC6Config from here).

2. Keep MC6Config BaseModel definition as-is (tests import it directly). Do NOT remove it — it stays as its own Pydantic model here for backward compat.

3. Keep the Controller BaseModel as-is. In Phase 3, Controller remains a peer model for test_mc6_generator.py fixture building. The loader will stop using it (that is Wave 3's job); tests that still construct Controller directly continue to work.

4. Add re-exports of ControllerConfig from device.py so callers can import it from either location:
   - `from rig.models.device import ControllerConfig as ControllerConfig`

For the fixture YAML files:

5. Create tests/fixtures/sample_rig/devices/mc6.yaml with this exact content:
   ```yaml
   id: mc6
   manufacturer: Morningstar
   model: MC6
   type: controller
   config:
     type: controller
     midi_channel: 1
     banks:
       - bank: 1
         name: Bank 1
         switches:
           A:
             scene: lead
   ```
   Note: no `scenes` key in this fixture — scenes are loaded separately from the scenes/ directory by the loader and injected in Wave 3.

6. Delete tests/fixtures/sample_rig/controller.yaml. This file used the old top-level Controller model format. After deletion, any code that loads this fixture path will correctly fail if it still looks for controller.yaml (which is the right behavior — the loader update in Wave 3 removes that path).
  </action>
  <verify>
    <automated>uv run pytest tests/ -q --tb=short 2>&1 | tail -15</automated>
  </verify>
  <done>All 167+ tests pass. controller.py still exports ControllerType, MC6Config, Controller (existing imports work). tests/fixtures/sample_rig/devices/mc6.yaml exists with type: controller. tests/fixtures/sample_rig/controller.yaml is gone.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML → Pydantic | YAML fixture files are parsed by yaml.safe_load then validated by Pydantic |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03P1-01 | Tampering | ControllerConfig.scenes mutable default | mitigate | Use Field(default_factory=dict) not a bare {} default to prevent shared state across instances |
| T-03P1-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in Phase 3 |
</threat_model>

<verification>
Run full test suite to confirm no regressions:

```
uv run pytest tests/ -q
```

Expected: 167+ tests pass (new controller tests added on top of baseline).

Spot-check discriminated union manually:
```
uv run python -c "
from rig.models.device import Device, DeviceType, ControllerConfig
d = Device(id='mc6', manufacturer='Morningstar', model='MC6', type=DeviceType.CONTROLLER, config={'type':'controller','midi_channel':1,'banks':[],'scenes':{}})
print(d.type, type(d.config).__name__)
"
```
Expected output: `controller ControllerConfig`
</verification>

<success_criteria>
- DeviceType.CONTROLLER == "controller"
- Device(type=CONTROLLER, config={type: controller, ...}) constructs without error
- ControllerConfig.scenes defaults to {}; .banks defaults to []
- All existing 167 tests continue to pass
- controller.py still exports ControllerType, MC6Config, Controller for backward compat
- tests/fixtures/sample_rig/devices/mc6.yaml exists with `type: controller` config
- tests/fixtures/sample_rig/controller.yaml is deleted
</success_criteria>

<output>
Create `.planning/phases/03-core-domain-refactor/03-P1-SUMMARY.md` when done
</output>
