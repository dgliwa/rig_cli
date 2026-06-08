---
phase: 09-core-model-cleanup
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/rig/src/rig/models/scene.py
  - packages/rig/src/rig/models/rig.py
  - packages/rig/src/rig/config/loader.py
  - packages/rig/src/rig/cli/commands/status.py
  - packages/rig/src/rig/cli/commands/validate.py
  - packages/rig-morningstar/src/rig_morningstar/device.py
autonomous: true
requirements:
  - MODEL-03
  - MODEL-04

must_haves:
  truths:
    - "Scene model has no mc6_bank or mc6_switch fields"
    - "rig.scenes returns dict[str, Scene] as a direct Pydantic field, not a property routing through ControllerConfig"
    - "rig.pedals, rig.digital_presets, rig.hx_presets, rig.analog_presets, rig.mc6, rig._controller_device properties are all absent from Rig"
    - "rig.controller property is present and works without _controller_device"
    - "status.py and validate.py reference rig.devices (not rig.pedals)"
    - "morningstar device.py references rig.devices (not rig.pedals)"
    - "All 289 tests pass"
  artifacts:
    - path: "packages/rig/src/rig/models/scene.py"
      provides: "Scene model"
      contains: "class Scene"
    - path: "packages/rig/src/rig/models/rig.py"
      provides: "Rig model with scenes as direct field"
      contains: "scenes: dict[str, Scene]"
    - path: "packages/rig/src/rig/config/loader.py"
      provides: "Loader that populates rig.scenes directly"
      contains: "scenes=scenes"
  key_links:
    - from: "packages/rig/src/rig/config/loader.py"
      to: "packages/rig/src/rig/models/rig.py"
      via: "Rig(scenes=scenes, ...)"
      pattern: "scenes=scenes"
    - from: "packages/rig/src/rig/models/rig.py"
      to: "packages/rig/src/rig/models/scene.py"
      via: "dict[str, Scene] field annotation"
      pattern: "dict\\[str, Scene\\]"
---

<objective>
Wave 1: Remove leaf-level backwards-compat shims from Scene and Rig. This wave makes
`rig.scenes` a real Pydantic field (not a property routing through ControllerConfig),
removes the six dead compat properties from Rig, and updates the two CLI commands plus
the morningstar device that still reference `rig.pedals`.

These changes have no upstream dependencies — Scene and Rig are the leaves of the
removal graph. The key constraint is that `scenes` must become a real field AND the
loader must be updated in the same commit (Pitfall 1: if one is done without the other,
`rig.scenes` returns empty dict and every test that accesses scenes breaks).

Purpose: MODEL-03 (remove compat shims from Rig) and MODEL-04 (remove mc6_bank/mc6_switch from Scene).
Output: Clean Scene model, clean Rig model with direct scenes field, updated loader, updated CLI commands and morningstar plugin.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@packages/rig/src/rig/models/scene.py
@packages/rig/src/rig/models/rig.py
@packages/rig/src/rig/config/loader.py
@packages/rig/src/rig/cli/commands/status.py
@packages/rig/src/rig/cli/commands/validate.py
@packages/rig-morningstar/src/rig_morningstar/device.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove mc6_bank/mc6_switch from Scene; make rig.scenes a direct field; update loader</name>
  <files>
    packages/rig/src/rig/models/scene.py
    packages/rig/src/rig/models/rig.py
    packages/rig/src/rig/config/loader.py
  </files>
  <action>
**scene.py** — Remove `mc6_bank: int | None = None` and `mc6_switch: Literal[...] | None = None`
fields entirely. Remove the `Literal` import since nothing else uses it in this file.
Final shape: `Scene(name, description, tempo, presets, tags)` only.

**rig.py** — Make the following changes atomically:

1. Remove imports: `ControllerConfig` from `rig.models.device`, `SignalChainPosition` from
   `rig.models.signal_chain`, `AnalogPreset`, `DigitalPreset`, `HXStompPreset` from
   `rig.models.preset` (only needed by the compat preset properties being deleted).
   Keep: `Device`, `DeviceType` from `rig.models.device`; `Scene` from `rig.models.scene`.

2. Add `scenes: dict[str, Scene] = {}` as a declared Pydantic model field on `Rig` (not a
   property). Place it after `midi_channel`.

3. Delete the following properties entirely:
   - `pedals` (returns `self.devices`)
   - `_controller_device` (returns first CONTROLLER device)
   - `digital_presets` (filters DigitalPreset from all devices)
   - `hx_presets` (filters HXStompPreset from all devices)
   - `analog_presets` (filters AnalogPreset from all devices)
   - `mc6` (returns `{"banks": ctrl.config.banks}`)
   - The `scenes` property (routes through ControllerConfig) — replaced by the field above

4. Simplify `controller` property to not depend on deleted `_controller_device`:
   ```
   @property
   def controller(self) -> Any | None:
       for device in self.devices.values():
           if getattr(device, "type", None) == DeviceType.CONTROLLER:
               return device
       return None
   ```
   Keep the `apply_order` method unchanged.

**CRITICAL**: Do NOT add `scenes` to `model_fields` check in any test — the test
`test_rig_controller_and_scenes_are_not_pydantic_fields` currently asserts
`"scenes" not in Rig.model_fields`. That test must be updated in Wave 4's test-cleanup
task to assert the opposite (scenes IS a model field). For now, that test will fail after
this change — that is expected and is fixed in Wave 4's test update task.

Actually: fix that test here since it directly tests what we are changing. In
`packages/rig/tests/test_models.py`, update the test
`test_rig_controller_and_scenes_are_not_pydantic_fields` to:
- Assert `"controller" not in Rig.model_fields` (still true — controller is a property)
- Assert `"scenes" in Rig.model_fields` (now true — scenes is a real field)
- Also update `test_rig_scenes_returns_empty_when_no_controller` to pass `scenes={}` explicitly
  to `Rig(name="Test", signal_chain=[], devices={}, scenes={})` — or just assert `rig.scenes == {}`
  which works because the default is `{}`.
- Update `test_rig_scenes_returns_controller_config_scenes`: `rig.scenes` is now a direct
  field, not wired via controller. Change the test to: create `Rig(name="Test", signal_chain=[],
  devices={"mc6": ctrl}, scenes={"test": scene})` and assert `rig.scenes["test"].name == "test"`.
  The `ctrl` device can be a plain `Device` with `ControllerConfig` — that's still valid at
  this wave since ControllerConfig is not yet removed.

**loader.py** — Three changes:

1. Remove the import of `SignalChainPosition` from `rig.models.signal_chain` (not yet
   removing the class itself — that is Wave 2).

2. Remove the scene-wiring block (currently ~lines 217-225):
   ```python
   # Wire scenes into device's ControllerConfig so Rig.scenes resolves correctly.
   if scenes:
       ctrl_device = next(...)
       if ctrl_device is not None and isinstance(ctrl_device.config, ControllerConfig):
           updated_config = ctrl_device.config.model_copy(update={"scenes": scenes})
           devices[ctrl_device.id] = ctrl_device.model_copy(update={"config": updated_config})
   ```
   Also remove the `ControllerConfig` import from loader (it was only used in this block).

3. Pass `scenes=scenes` directly to the `Rig(...)` constructor call:
   ```python
   rig = Rig(
       name=rig_data.get("name", ""),
       description=rig_data.get("description"),
       midi_channel=rig_data.get("midi_channel"),
       signal_chain=chain,
       devices=devices,
       scenes=scenes,
   )
   ```
   Note: `chain` is still `[SignalChainPosition(**pos) for pos in ...]` at this point —
   Wave 2 changes this. Do not change it here.

   Also update `_validate_references`: anywhere it reads `pos.device_ref` from `rig.signal_chain`
   (line ~146) that still works because we are not yet changing `signal_chain` type. Leave as is.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/rig/tests/test_models.py packages/rig/tests/test_loader.py -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    Scene has no mc6_bank or mc6_switch fields. Rig has `scenes: dict[str, Scene]` as a model
    field (verified via `"scenes" in Rig.model_fields`). Loader passes `scenes=scenes` to Rig
    constructor. No ControllerConfig import in loader. test_models.py and test_loader.py pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update status.py, validate.py, morningstar device.py to use rig.devices</name>
  <files>
    packages/rig/src/rig/cli/commands/status.py
    packages/rig/src/rig/cli/commands/validate.py
    packages/rig-morningstar/src/rig_morningstar/device.py
  </files>
  <action>
**status.py** — Two changes:

1. JSON branch: replace `rig.pedals.items()` with `rig.devices.items()`. The JSON key
   `"pedals"` in the output dict can stay as-is (it is a CLI display string, not a model field).

2. Table branch: replace `rig.pedals.items()` with `rig.devices.items()`. Remove the
   `preset_count` calculation that uses `rig.digital_presets.get(pid, [])`,
   `rig.analog_presets.get(pid, [])`, and `rig.hx_presets.get(pid, [])`. Replace with
   `preset_count = len(pedal.presets)` (works for all device types since every plugin device
   exposes `presets: list[Any]`).

   The variable is named `pedal` in the loop — rename to `device` for clarity, or leave as
   `pedal` if rename is not needed to pass tests (either is acceptable).

**validate.py** — Two changes:

1. `"pedals": len(rig.pedals)` in JSON branch → `"pedals": len(rig.devices)`
2. `f"... {len(rig.pedals)} pedals ..."` in text branch → `len(rig.devices)`

**morningstar/device.py** — In the `apply` method, at the line that reads
`pedal = rig.pedals.get(pedal_id)`, change to `pedal = rig.devices.get(pedal_id)`.
This is the only `rig.pedals` reference in this file. Leave all other code unchanged.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/ -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    All 289 tests pass. `uv run pytest packages/ -q` exits 0. No `rig.pedals`,
    `rig.digital_presets`, `rig.hx_presets`, `rig.analog_presets`, or `rig.mc6` references
    remain in status.py, validate.py, or morningstar/device.py.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML config → loader | YAML is user-controlled input; Pydantic validates on model construction |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-01 | Tampering | Scene.presets dict | accept | Pydantic validates field types on load; no new surface introduced by this wave |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this phase |
</threat_model>

<verification>
After both tasks complete:

```bash
cd /Users/derekgliwa/dev/rig-cli

# MODEL-04: Scene has no mc6_bank or mc6_switch
grep -v '^#' packages/rig/src/rig/models/scene.py | grep -c "mc6_bank\|mc6_switch"
# Expected: 0

# MODEL-03: Rig compat properties gone
grep -v '^#' packages/rig/src/rig/models/rig.py | grep -c "def pedals\|def _controller_device\|def digital_presets\|def hx_presets\|def analog_presets\|def mc6"
# Expected: 0

# scenes is a real field
python -c "from rig.models.rig import Rig; assert 'scenes' in Rig.model_fields, 'scenes must be a model field'"

# Full test suite
uv run pytest packages/ -q --tb=short
# Expected: 289 passed
```
</verification>

<success_criteria>
- `grep -c "mc6_bank\|mc6_switch" packages/rig/src/rig/models/scene.py` returns 0 (after filtering comments)
- `"scenes" in Rig.model_fields` is True
- `hasattr(Rig, "pedals")` is False
- `uv run pytest packages/ -q` exits 0 with 289 tests passing
- Wave 1 commit created: `refactor(models): remove Scene mc6 fields; make Rig.scenes direct field; remove compat shims (MODEL-03, MODEL-04)`
</success_criteria>

<output>
Create `.planning/phases/09-core-model-cleanup/09-01-SUMMARY.md` when done
</output>

---
phase: 09-core-model-cleanup
plan: 02
type: execute
wave: 2
depends_on:
  - "09-01"
files_modified:
  - packages/rig/src/rig/models/rig.py
  - packages/rig/src/rig/config/loader.py
  - packages/rig/src/rig/models/graph.py
  - packages/rig/src/rig/models/signal_chain.py
  - packages/rig/src/rig/models/__init__.py
  - packages/rig/tests/test_models.py
  - packages/rig/tests/test_graph.py
autonomous: true
requirements:
  - SCHEMA-03

must_haves:
  truths:
    - "Rig.signal_chain is typed as list[str] (ordered device ID strings)"
    - "signal_chain.py file is deleted"
    - "SignalChainPosition is absent from models/__init__.py"
    - "DeviceGraph iterates list[str] not list[SignalChainPosition]"
    - "Loader extracts device IDs from YAML chain entries"
    - "All 289 tests pass"
  artifacts:
    - path: "packages/rig/src/rig/models/rig.py"
      provides: "Rig with signal_chain: list[str]"
      contains: "signal_chain: list[str]"
    - path: "packages/rig/src/rig/models/graph.py"
      provides: "DeviceGraph iterating list[str]"
  key_links:
    - from: "packages/rig/src/rig/models/graph.py"
      to: "packages/rig/src/rig/models/rig.py"
      via: "self._rig.signal_chain iteration"
      pattern: "for.*device_id.*in.*signal_chain"
    - from: "packages/rig/src/rig/config/loader.py"
      to: "packages/rig/src/rig/models/rig.py"
      via: "list[str] chain construction"
      pattern: "pos.get.*device.*pedal"
---

<objective>
Wave 2: Simplify the signal chain from `list[SignalChainPosition]` to `list[str]`.
`SignalChainPosition` was a model that tracked device order plus `loop`/`stereo` metadata —
that metadata is not used by the current plan/apply engine. This wave strips it out.

The three files that change together (atomically to avoid Pitfall 2):
- `rig.py`: type annotation changes
- `loader.py`: extracts device IDs instead of constructing SignalChainPosition objects
- `graph.py`: iterates strings instead of objects with `.device_ref`

Then `signal_chain.py` is deleted and `models/__init__.py` is cleaned up.

Purpose: SCHEMA-03 (remove SignalChainPosition).
Output: signal_chain.py deleted, Rig.signal_chain is list[str], DeviceGraph uses string iteration, loader produces list[str].
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@packages/rig/src/rig/models/rig.py
@packages/rig/src/rig/config/loader.py
@packages/rig/src/rig/models/graph.py
@packages/rig/src/rig/models/signal_chain.py
@packages/rig/src/rig/models/__init__.py
@.planning/phases/09-core-model-cleanup/09-01-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Change signal_chain to list[str] in Rig, loader, and graph — then delete signal_chain.py</name>
  <files>
    packages/rig/src/rig/models/rig.py
    packages/rig/src/rig/config/loader.py
    packages/rig/src/rig/models/graph.py
    packages/rig/src/rig/models/signal_chain.py
  </files>
  <action>
Make all four changes in a single pass to prevent test failures between edits.

**rig.py**:
- Change `signal_chain: list[SignalChainPosition]` → `signal_chain: list[str] = []`
- Remove the `SignalChainPosition` import (already removed in Wave 1, but confirm it's gone)

**loader.py**:
- Remove `from rig.models.signal_chain import SignalChainPosition` import (if still present
  after Wave 1 — it should be gone already, but double-check)
- Change chain construction from:
  ```
  chain = [SignalChainPosition(**pos) for pos in signal_data.get("chain", [])]
  ```
  to:
  ```
  chain = [
      pos.get("device") or pos.get("pedal") or pos.get("device_ref") or pos.get("pedal_ref")
      for pos in signal_data.get("chain", [])
      if pos.get("device") or pos.get("pedal") or pos.get("device_ref") or pos.get("pedal_ref")
  ]
  ```
  This handles existing `{pedal: id, position: N}` YAML format as well as any `{device: id}` format.

- Update `_validate_references` where it reads `pos.device_ref` from `rig.signal_chain` (line ~146):
  Change `for pos in rig.signal_chain: if pos.device_ref not in valid_chain_ids:` to
  `for device_id in rig.signal_chain: if device_id not in valid_chain_ids:`.
  Update the error message to reference `device_id` instead of `pos.device_ref`.

**graph.py**:
- In `apply_order` method: replace the dict comprehension that reads `sc.device_ref` and
  `sc.position`:
  ```python
  chain_positions: dict[str, int] = {
      sc.device_ref: sc.position for sc in self._rig.signal_chain
  }
  ```
  Change to enumerate-based ordering:
  ```python
  chain_positions: dict[str, int] = {
      device_id: i for i, device_id in enumerate(self._rig.signal_chain)
  }
  ```

- In the cycle-detection loop (currently reads `for sc in self._rig.signal_chain:
  device_ref = sc.device_ref`), change to:
  ```python
  for device_id in self._rig.signal_chain:
      if device_id in seen:
          raise CycleError(f"Device '{device_id}' appears multiple times in signal chain")
      seen.add(device_id)
  ```

- Remove the `SignalChainPosition` import if graph.py imports it (check — it likely does not,
  but the `Device` import from `rig.models.device` stays).

**signal_chain.py** — Delete the file. Use `Bash("rm packages/rig/src/rig/models/signal_chain.py")`.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/rig/tests/test_graph.py packages/rig/tests/test_loader.py -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    `signal_chain.py` file does not exist. `Rig.signal_chain` is annotated as `list[str]`.
    DeviceGraph iterates string IDs. Loader builds list of strings from YAML chain entries.
    test_graph.py and test_loader.py pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Clean models/__init__.py and update signal-chain tests</name>
  <files>
    packages/rig/src/rig/models/__init__.py
    packages/rig/tests/test_models.py
    packages/rig/tests/test_graph.py
  </files>
  <action>
**models/__init__.py**:
- Remove `from rig.models.signal_chain import SignalChainPosition`
- Remove `"SignalChainPosition"` from `__all__`
- Leave all other imports and exports unchanged

**packages/rig/tests/test_models.py**:
- Remove `from rig.models.signal_chain import SignalChainPosition`
- Delete the entire `TestSignalChainModel` class (4 tests: `test_signal_chain_position_defaults`,
  `test_signal_chain_fx_loop`, `test_signal_chain_stereo`, `test_signal_chain_pedal_ref_compat`)
- Update `TestApplyOrder` tests that construct `signal_chain` as `[SignalChainPosition(...)]`:
  - `test_apply_order_no_controller_returns_devices_by_position`: change
    `signal_chain=[SignalChainPosition(device_ref="brothers", position=2), SignalChainPosition(device_ref="tumnus", position=1)]`
    to `signal_chain=["brothers", "tumnus"]` — note the order flips! The test asserts
    `["tumnus", "brothers"]` because tumnus has position=1. After switching to list[str],
    the order in the list IS the signal chain order. So pass `signal_chain=["tumnus", "brothers"]`
    to produce the expected `["tumnus", "brothers"]` apply order.
  - `test_apply_order_controller_comes_last`: change
    `signal_chain=[SignalChainPosition(device_ref="tumnus", position=1)]` to
    `signal_chain=["tumnus"]`
  - `test_apply_order_device_not_in_chain_after_chain_ordered`: change
    `signal_chain=[SignalChainPosition(device_ref="tumnus", position=1)]` to
    `signal_chain=["tumnus"]`

**packages/rig/tests/test_graph.py**:
- Remove `from rig.models.signal_chain import SignalChainPosition`
- Update the `_make_rig` helper (or equivalent fixture): change
  `signal_chain=[SignalChainPosition(device_ref=id, position=i) for i, id in enumerate(signal_chain_ids)]`
  to `signal_chain=list(signal_chain_ids)` (signal_chain_ids is already in order).
- Also remove `ControllerConfig`, `ManualConfig`, `MidiConfig` imports from test_graph.py and
  update `_make_device` helper: since `config` on `Device` will eventually be `Any`, for now
  just pass a plain dict or simple object. The easiest approach: remove the per-type config
  branching and pass `config={"type": "manual"}` for all devices in graph tests, OR keep the
  imports temporarily if ControllerConfig/ManualConfig/MidiConfig still exist (they do at this
  wave). Check what test_graph.py actually needs: if it only needs to build `Device` objects
  with different `type` values, use `config={}` with `model_config = ConfigDict(arbitrary_types_allowed=True)`
  already set on `Device`.

  Simplest correct approach for this wave: keep `ManualConfig`, `MidiConfig`, `ControllerConfig`
  imports in test_graph.py (they still exist). Only remove `SignalChainPosition` import and
  update the signal_chain construction. The config type removal from test_graph.py happens in
  Wave 4's test-cleanup task.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/ -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    `from rig.models.signal_chain import SignalChainPosition` does not appear anywhere in
    models/__init__.py or test_models.py. `SignalChainPosition` is not in `models.__all__`.
    Full test suite passes (expect ~285 tests: 4 SignalChainModel tests removed, 289 - 4 = 285).
    Wave 2 commit created: `refactor(models): replace SignalChainPosition with list[str] signal chain (SCHEMA-03)`
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML signal-chain.yaml → loader | User-controlled chain list; loader extracts device ID strings |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-02 | Information Disclosure | signal_chain list | accept | Device IDs are not secrets; no new exposure |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this phase |
</threat_model>

<verification>
After both tasks complete:

```bash
cd /Users/derekgliwa/dev/rig-cli

# SCHEMA-03: signal_chain.py deleted
test ! -f packages/rig/src/rig/models/signal_chain.py && echo "PASS: signal_chain.py deleted"

# signal_chain is list[str]
python -c "
from rig.models.rig import Rig
import inspect
src = inspect.getsource(Rig)
assert 'signal_chain: list[str]' in src, 'signal_chain must be list[str]'
print('PASS: signal_chain is list[str]')
"

# SignalChainPosition absent from __init__
grep -v '^#' packages/rig/src/rig/models/__init__.py | grep -c "SignalChainPosition"
# Expected: 0

# Full test suite
uv run pytest packages/ -q --tb=short
# Expected: ~285 passed (4 SignalChainModel tests removed)
```
</verification>

<success_criteria>
- `packages/rig/src/rig/models/signal_chain.py` does not exist
- `Rig.signal_chain` annotation is `list[str]`
- `DeviceGraph` iterates `for device_id in self._rig.signal_chain` (no `.device_ref`)
- `uv run pytest packages/ -q` exits 0
</success_criteria>

<output>
Create `.planning/phases/09-core-model-cleanup/09-02-SUMMARY.md` when done
</output>

---
phase: 09-core-model-cleanup
plan: 03
type: execute
wave: 3
depends_on:
  - "09-02"
files_modified:
  - packages/rig-chasebliss/src/rig_chasebliss/catalog.py
  - packages/rig-chasebliss/src/rig_chasebliss/device.py
  - packages/rig-morningstar/src/rig_morningstar/generator.py
  - packages/rig/src/rig/models/device.py
  - packages/rig/src/rig/config/loader.py
  - packages/rig/src/rig/engine/plan/compute.py
  - packages/rig/src/rig/engine/plan/models.py
  - packages/rig/src/rig/cli/commands/plan.py
autonomous: true
requirements:
  - MODEL-01
  - MODEL-02

must_haves:
  truths:
    - "ChaseBlissConfig is defined in rig_chasebliss/device.py (not imported from core)"
    - "Control and ControlType are defined in rig_chasebliss/catalog.py (not imported from core)"
    - "ControllerConfig is absent from device.py"
    - "ManualConfig, MidiConfig, ChaseBlissConfig, ControllerConfig are all absent from device.py"
    - "detect_cba_setup is absent from plan/compute.py"
    - "cba_setup field is absent from Plan model"
    - "plan.py CLI does not render a Setup Actions section"
    - "rig.mc6 is gone from morningstar/generator.py"
    - "All tests pass (test count reduced due to CBA plan tests being removed or updated)"
  artifacts:
    - path: "packages/rig-chasebliss/src/rig_chasebliss/catalog.py"
      provides: "Control, ControlType, MOOD_MKII_CONTROLS, get_controls"
      contains: "class Control"
    - path: "packages/rig-chasebliss/src/rig_chasebliss/device.py"
      provides: "ChaseBlissConfig, ChaseBlissDevice"
      contains: "class ChaseBlissConfig"
    - path: "packages/rig/src/rig/engine/plan/models.py"
      provides: "Plan without cba_setup"
  key_links:
    - from: "packages/rig-chasebliss/src/rig_chasebliss/device.py"
      to: "packages/rig-chasebliss/src/rig_chasebliss/catalog.py"
      via: "from rig_chasebliss.catalog import Control"
      pattern: "from rig_chasebliss.catalog import"
    - from: "packages/rig-chasebliss/src/rig_chasebliss/device.py"
      to: "packages/rig/src/rig/engine/plan/models.py"
      via: "from rig.engine.plan.models import CbaSetupAction"
      pattern: "from rig.engine.plan.models import CbaSetupAction"
---

<objective>
Wave 3: Move plugin config types out of core and remove the CBA plan-time detection.

Three independent migration streams:
1. CBA: `Control`/`ControlType` move to `rig_chasebliss/catalog.py`; `ChaseBlissConfig` moves
   to `rig_chasebliss/device.py`; core `device.py` loses these types.
2. Morningstar: `ControllerConfig` removed from core; `generator.py` stops using `rig.mc6`.
3. Plan engine: `detect_cba_setup` removed from `compute.py`; `cba_setup` removed from `Plan`;
   CBA Setup Actions section removed from `plan.py` CLI.

ManualConfig and MidiConfig removal (MODEL-01 remainder) also happens here — they have no
downstream callers in core outside of tests.

Purpose: MODEL-01 (remove all plugin configs from device.py), MODEL-02 (remove Control/ControlType from core).
Output: core device.py has no plugin-specific types; CBA types live in rig-chasebliss; plan engine has no CBA-specific logic.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@packages/rig-chasebliss/src/rig_chasebliss/catalog.py
@packages/rig-chasebliss/src/rig_chasebliss/device.py
@packages/rig-morningstar/src/rig_morningstar/generator.py
@packages/rig/src/rig/models/device.py
@packages/rig/src/rig/config/loader.py
@packages/rig/src/rig/engine/plan/compute.py
@packages/rig/src/rig/engine/plan/models.py
@packages/rig/src/rig/cli/commands/plan.py
@.planning/phases/09-core-model-cleanup/09-02-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move Control/ControlType to catalog.py; define ChaseBlissConfig in device.py (plugin)</name>
  <files>
    packages/rig-chasebliss/src/rig_chasebliss/catalog.py
    packages/rig-chasebliss/src/rig_chasebliss/device.py
  </files>
  <action>
**rig_chasebliss/catalog.py** — Define `Control` and `ControlType` natively here (copy exact
class definitions from core `device.py`). Replace the import line
`from rig.models.device import Control, ControlType` with the inline class definitions:

```python
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ControlType(StrEnum):
    KNOB = "knob"
    SWITCH = "switch"
    TOGGLE = "toggle"
    DIPSWITCH = "dipswitch"


class Control(BaseModel):
    name: str = Field(..., min_length=1)
    type: ControlType
    midi_cc: int | None = None
    min: float | str | bool | None = None
    max: float | str | bool | None = None
    positions: list[str] = []
    expression_assignable: bool = False
```

Then keep `MOOD_MKII_CONTROLS` and `get_controls` exactly as they are (they reference `Control`
and `ControlType` from the same file now, so no import change needed there).

**rig_chasebliss/device.py** — Two changes:

1. Replace `from rig.models.device import ChaseBlissConfig, DeviceType` with:
   ```python
   from rig.models.device import DeviceType
   from rig_chasebliss.catalog import Control
   ```
   Then define `ChaseBlissConfig` locally:
   ```python
   from pydantic import BaseModel
   from typing import Literal, Any

   class ChaseBlissConfig(BaseModel):
       type: Literal["chase_bliss"] = "chase_bliss"
       midi_channel: int | None = None
       controls: list[Control] = []

       def get_cc_params(self, parameters: dict[str, Any]) -> list[dict[str, int]]:
           result = []
           for ctrl in self.controls:
               if ctrl.midi_cc is not None and ctrl.name in parameters:
                   result.append({"cc": ctrl.midi_cc, "value": int(parameters[ctrl.name])})
           return result
   ```
   Verify the `get_cc_params` signature matches what it was in core `ChaseBlissConfig`
   (check `device.py` before editing — the method must be identical).

2. The `_detect_cba_setup_for_device` function uses `isinstance(device.config, ChaseBlissConfig)`.
   After this change, it references the locally-defined `ChaseBlissConfig`. Correct.

3. The `setup` method uses `isinstance(self.config, ChaseBlissConfig)`. Correct.

Do NOT change the import `from rig.engine.plan.models import CbaSetupAction` inside
`_detect_cba_setup_for_device` — `CbaSetupAction` stays in core until Phase 11.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/rig/tests/test_catalog.py packages/rig/tests/test_devices.py -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    `catalog.py` defines `Control` and `ControlType` locally (no import from rig.models.device).
    `device.py` (rig-chasebliss) defines `ChaseBlissConfig` locally and imports `DeviceType`
    from core. test_catalog.py and test_devices.py pass for CBA-related tests.
  </done>
</task>

<task type="auto">
  <name>Task 2: Remove plugin configs from core device.py; remove ControllerConfig from loader; fix generator.py; remove CBA from plan engine</name>
  <files>
    packages/rig/src/rig/models/device.py
    packages/rig/src/rig/config/loader.py
    packages/rig-morningstar/src/rig_morningstar/generator.py
    packages/rig/src/rig/engine/plan/compute.py
    packages/rig/src/rig/engine/plan/models.py
    packages/rig/src/rig/cli/commands/plan.py
  </files>
  <action>
These six files change together because they form a single logical removal: eliminating
CBA-at-plan-time detection and stripping plugin configs from core.

**device.py** (core) — Remove the following in order:
1. `ControlType` StrEnum class — deleted
2. `Control` BaseModel class — deleted
3. `DeviceConfig` BaseModel base class — deleted (nothing references it after subclasses are gone)
4. `ManualConfig(DeviceConfig)` class — deleted
5. `MidiConfig(DeviceConfig)` class — deleted
6. `ChaseBlissConfig(DeviceConfig)` class — deleted
7. `ControllerConfig(DeviceConfig)` class — deleted
8. Remove `_populate_cba_controls` model_validator on `Device` — deleted
9. Change `Device.config` type: remove the `Annotated[ManualConfig | MidiConfig | ...,
   Field(discriminator="type")]` annotation. Change to `config: Any = None`.
10. Update imports at top of file: remove `Literal` (only used by config classes),
    remove `model_validator` (only used by `_populate_cba_controls`). Keep:
    `from __future__ import annotations`, `from enum import StrEnum`, `from typing import Any`,
    `from pydantic import BaseModel, Field`, and the preset imports.
11. Keep `DeviceType`, `Preset`, `Device` — these are the only exports remaining.

After removal, `device.py` should export only: `DeviceType`, `Device`, `Preset`.

**loader.py** — Remove the CBA parameter validation block inside `_validate_references`.
Find the block that uses `isinstance(device.config, ChaseBlissConfig)` and remove it entirely.
Also remove the `ChaseBlissConfig` import (already done in Wave 1 for `ControllerConfig`;
verify `ChaseBlissConfig` import is also gone — it may still be present here).
The `ControllerConfig` import was removed in Wave 1. Confirm no remaining plugin config imports.

**generator.py** (morningstar) — Replace `rig.mc6`:
- Change `mc6_config = rig.mc6` and `banks = mc6_config.get("banks", [])` to:
  ```python
  controller = rig.controller
  banks = controller.config.banks if controller and hasattr(controller.config, "banks") else []
  ```
  Remove the `mc6_config` variable. The rest of the loop body (`for bank in banks:`) stays identical.

**compute.py** — Remove:
1. The `detect_cba_setup` function entirely (lines ~25-47)
2. The import `from rig.engine.plan.models import CbaSetupAction, DeviceAction, Plan, ScenePlan`
   → change to `from rig.engine.plan.models import DeviceAction, Plan, ScenePlan` (drop `CbaSetupAction`)
3. Any inline import of `ChaseBlissConfig` inside `detect_cba_setup` (removed with the function)
4. The call `cba_setup = detect_cba_setup(rig, actual)` and the related debug log line
5. The `cba_setup=cba_setup` argument in the `Plan(...)` constructor call

After removal, `Plan(...)` is constructed without `cba_setup`.

**plan/models.py** — Remove `cba_setup: list[CbaSetupAction] = []` from the `Plan` model.
Keep `CbaSetupAction` class itself (needed by `rig_chasebliss/device.py` until Phase 11).

**plan.py** (CLI) — Remove the Setup Actions rendering block:
```python
# --- Setup Actions section (before scenes) ---
# TODO: 1.2 ...
if result.cba_setup:
    console.print("\n[bold]Setup Actions:[/bold]")
    for action in result.cba_setup:
        if action.type == "establish_channel":
            ...
        elif action.type == "build_preset":
            ...
        elif action.type == "register_scenes":
            ...
```
Delete all of that block (lines 67-82 approximately). The scenes section immediately follows.

Also update the plan summary count line: currently `configure_count` does not include CBA
setup actions in its tally. After removal, this is already correct — no change needed to
the summary line math.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/ -q --tb=short 2>&1 | tail -30</automated>
  </verify>
  <done>
    `device.py` exports only `DeviceType`, `Device`, `Preset`. No `ManualConfig`, `MidiConfig`,
    `ChaseBlissConfig`, `ControllerConfig`, `Control`, `ControlType`, `DeviceConfig` in device.py.
    `Plan.cba_setup` field does not exist. `detect_cba_setup` does not exist in compute.py.
    `generator.py` uses `rig.controller.config.banks`. Tests pass (expect reductions from
    removed CBA plan tests and CBA CLI plan tests).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plugin device.py → core device.py | Plugin imports DeviceType from core; core no longer imports back |
| rig.controller.config → Any | Config is untyped; attribute access via hasattr guards required |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-03 | Elevation of Privilege | Device.config: Any | accept | Config objects constructed by loader via validated plugin models; no arbitrary user data reaches config fields |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this phase |
</threat_model>

<verification>
After both tasks complete:

```bash
cd /Users/derekgliwa/dev/rig-cli

# MODEL-01: plugin configs absent from core device.py
for TYPE in ManualConfig MidiConfig ChaseBlissConfig ControllerConfig; do
  COUNT=$(grep -v '^#' packages/rig/src/rig/models/device.py | grep -c "$TYPE")
  echo "$TYPE: $COUNT (expected 0)"
done

# MODEL-02: Control and ControlType absent from core device.py
grep -v '^#' packages/rig/src/rig/models/device.py | grep -c "class Control\|class ControlType"
# Expected: 0

# CBA types defined in plugin
grep -c "class ChaseBlissConfig" packages/rig-chasebliss/src/rig_chasebliss/device.py
# Expected: 1
grep -c "class Control" packages/rig-chasebliss/src/rig_chasebliss/catalog.py
# Expected: 1

# detect_cba_setup gone from compute.py
grep -c "detect_cba_setup" packages/rig/src/rig/engine/plan/compute.py
# Expected: 0

# cba_setup gone from Plan
grep -c "cba_setup" packages/rig/src/rig/engine/plan/models.py
# Expected: 1 (CbaSetupAction class definition stays, field is gone)

uv run pytest packages/ -q --tb=short
```
</verification>

<success_criteria>
- `grep -c "class ManualConfig\|class MidiConfig\|class ChaseBlissConfig\|class ControllerConfig" packages/rig/src/rig/models/device.py` returns 0
- `grep -c "class Control\b\|class ControlType" packages/rig/src/rig/models/device.py` returns 0
- `grep -c "cba_setup" packages/rig/src/rig/engine/plan/models.py` returns 1 (only the class def)
- `grep -c "detect_cba_setup" packages/rig/src/rig/engine/plan/compute.py` returns 0
- `uv run pytest packages/ -q` exits 0
- Wave 3 commit created: `refactor(models): move plugin configs to packages; remove CBA plan-time detection (MODEL-01, MODEL-02)`
</success_criteria>

<output>
Create `.planning/phases/09-core-model-cleanup/09-03-SUMMARY.md` when done
</output>

---
phase: 09-core-model-cleanup
plan: 04
type: execute
wave: 4
depends_on:
  - "09-03"
files_modified:
  - packages/rig/src/rig/models/device.py
  - packages/rig/src/rig/models/__init__.py
  - packages/rig/tests/test_models.py
  - packages/rig/tests/test_plan.py
  - packages/rig/tests/test_diff.py
  - packages/rig/tests/test_apply.py
  - packages/rig/tests/test_appliers.py
  - packages/rig/tests/test_graph.py
  - packages/rig/tests/test_catalog.py
  - packages/rig/tests/test_devices.py
  - packages/rig/tests/test_loader.py
  - packages/rig/tests/test_cli_plan.py
  - packages/rig/tests/test_mc6_generator.py
autonomous: true
requirements:
  - SCHEMA-06

must_haves:
  truths:
    - "Device has no manufacturer or model fields"
    - "_populate_cba_controls validator is absent from Device"
    - "models/__init__.py exports only DeviceType, Device, Preset (plus preset types, Rig, Scene, RigConfig)"
    - "All test files that use removed types (ManualConfig, MidiConfig, ChaseBlissConfig, ControllerConfig, manufacturer, model) are updated to use plugin types or plain dicts"
    - "All remaining tests pass"
  artifacts:
    - path: "packages/rig/src/rig/models/device.py"
      provides: "Clean Device model with config: Any, no manufacturer/model"
      contains: "class Device"
    - path: "packages/rig/src/rig/models/__init__.py"
      provides: "Clean __init__ with no removed types"
  key_links:
    - from: "packages/rig/tests/test_plan.py"
      to: "packages/rig-chasebliss/src/rig_chasebliss/device.py"
      via: "ChaseBlissDevice instead of Device+ChaseBlissConfig"
      pattern: "ChaseBlissDevice"
    - from: "packages/rig/tests/test_apply.py"
      to: "packages/rig-chasebliss/src/rig_chasebliss/device.py"
      via: "ChaseBlissDevice in rig fixture"
      pattern: "ChaseBlissDevice"
---

<objective>
Wave 4: Remove `manufacturer` and `model` from core `Device`, clean up `models/__init__.py`,
and update all test files that still reference removed types.

This is the largest wave by test-change volume. Every test that builds `Device(manufacturer=...,
model=..., config=ManualConfig(...))` must be updated. The migration strategy per file:

- Tests that test plan/apply behavior with CBA devices: migrate to `ChaseBlissDevice`
- Tests that test plan/apply behavior with MIDI devices: migrate to `HXStompDevice` or keep
  `Device` with `config={"type": "midi", "midi_channel": N}` (plain dict)
- Tests that test plan/apply behavior with analog devices: use `Device` with `config={"type": "manual"}`
- Tests that test plan/apply behavior with controller devices: use `MC6Device` with config as dict
- Tests that directly test `ControllerConfig`/`ManualConfig` behavior: replace with equivalent
  assertions on plugin types or remove if they test now-deleted behavior

Purpose: SCHEMA-06 (remove manufacturer/model from Device), MODEL-02 completion (remove from __init__).
Output: Device is clean — `id`, `name`, `type`, `config: Any`, `presets`. All tests pass.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@packages/rig/src/rig/models/device.py
@packages/rig/src/rig/models/__init__.py
@packages/rig/tests/test_models.py
@packages/rig/tests/test_plan.py
@packages/rig/tests/test_diff.py
@packages/rig/tests/test_apply.py
@packages/rig/tests/test_appliers.py
@packages/rig/tests/test_graph.py
@packages/rig/tests/test_catalog.py
@packages/rig/tests/test_devices.py
@packages/rig/tests/test_cli_plan.py
@.planning/phases/09-core-model-cleanup/09-03-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove manufacturer/model from Device; clean models/__init__.py</name>
  <files>
    packages/rig/src/rig/models/device.py
    packages/rig/src/rig/models/__init__.py
  </files>
  <action>
**device.py** — At this point (after Wave 3), `device.py` should already have no plugin config
classes. Remaining changes:

1. Remove `manufacturer: str | None = None` field from `Device`
2. Remove `model: str | None = None` field from `Device`
3. Confirm `from pydantic import BaseModel, Field` is still needed (yes — `Device` uses Field
   for `presets`). Ensure `model_validator` is no longer in pydantic imports (removed in Wave 3).
4. The import `from rig.models.scene import Scene` was at the top of device.py. Check if
   it is still needed — `Device` no longer has `scenes` anywhere. If `Scene` is not referenced
   in device.py after removal, remove that import.

Final `Device` class should have exactly these fields:
- `id: str`
- `name: str = ""`
- `type: DeviceType`
- `config: Any = None`
- `presets: list[Any] = Field(default_factory=list)`

Plus the `get_scene_pc_command` method if it exists on `Device` (check — it calls
`self.config.midi_channel` via `getattr` or direct access; keep if present).

**models/__init__.py** — Remove these imports and `__all__` entries (they were deleted from
device.py in Wave 3):
- `Control`, `ControlType`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`
- `DeviceConfig` (base class — removed in Wave 3)

Final `__all__` should contain: `"Device"`, `"DeviceType"`, `"Rig"`, `"Preset"`,
`"AnalogPreset"`, `"DigitalPreset"`, `"HXStompPreset"`, `"Scene"`, `"RigConfig"`.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && python -c "from rig.models.device import Device, DeviceType, Preset; d = Device(id='test', type=DeviceType.ANALOG); print('Device fields:', list(d.model_fields.keys()))" 2>&1</automated>
  </verify>
  <done>
    `Device.model_fields` contains `id`, `name`, `type`, `config`, `presets` — and NOT
    `manufacturer` or `model`. `models/__init__.py` has no imports of removed types.
    `python -c "from rig.models.device import Device"` succeeds without error.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update all test files to remove references to deleted types</name>
  <files>
    packages/rig/tests/test_models.py
    packages/rig/tests/test_plan.py
    packages/rig/tests/test_diff.py
    packages/rig/tests/test_apply.py
    packages/rig/tests/test_appliers.py
    packages/rig/tests/test_graph.py
    packages/rig/tests/test_catalog.py
    packages/rig/tests/test_devices.py
    packages/rig/tests/test_loader.py
    packages/rig/tests/test_cli_plan.py
  </files>
  <action>
Work through each file systematically. The goal: every test that constructed
`Device(manufacturer=..., model=..., config=SomePluginConfig(...))` must be updated.

**test_models.py**:
- Remove imports: `Control`, `ControllerConfig`, `ControlType`, `ManualConfig` from
  `rig.models.device`. Keep: `Device`, `DeviceType`.
- Delete class `TestControllerConfig` entirely — tests `ControllerConfig` behavior which
  no longer exists in core.
- In `TestPedalModels`:
  - Delete `test_invalid_control_rejected` — tests `Control` which is now in rig-chasebliss
  - Delete `test_control_with_positions`, `test_control_with_midi_cc`,
    `test_control_expression_defaults_to_false` — same reason
  - Update `test_pedal_definition_round_trips`: remove `manufacturer="Wampler", model="Tumnus"`,
    change `config=ManualConfig(controls=[...])` to `config={"type": "manual"}` or `config=None`
- Update helper `_make_controller_device`: remove `manufacturer`, `model`; change
  `config=ControllerConfig(...)` to `config={"type": "controller", "midi_channel": 1, "banks": []}`.
  Import `MC6Device` from `rig_morningstar.device` instead of building a `Device` with
  `ControllerConfig`. OR: keep it as `Device(id="mc6", type=DeviceType.CONTROLLER, config={"type":"controller","banks":[]})`.
  The `TestApplyOrder` tests only care about `device.id`, `device.type`, not the config type —
  so plain `Device` with a dict config is fine.
- Update helper `_make_analog_device`: remove `manufacturer="Wampler", model="Tumnus"`.
- In `TestRigConfig`:
  - `test_rig_controller_and_scenes_are_not_pydantic_fields`: update per Wave 1 note — assert
    `"controller" not in Rig.model_fields` (still true) and `"scenes" in Rig.model_fields`
    (true after Wave 1).
- `TestApplyOrder` uses `_make_controller_device` and `_make_analog_device` — they'll work once
  helpers are updated.

**test_plan.py**:
- Remove imports: `ChaseBlissConfig`, `ControllerConfig`, `ManualConfig`, `MidiConfig` from
  `rig.models.device`, `SignalChainPosition` from `rig.models.signal_chain`.
- The `_make_rig` helper (or inline fixture code) that builds `Device(manufacturer=..., config=...)`:
  - HX Stomp device: change to `HXStompDevice(id="hx-stomp", config={"type":"midi","midi_channel":1})`
    from `rig_hx.device import HXStompDevice`
  - CBA device: change to `ChaseBlissDevice(id="brothers", config=ChaseBlissConfig(midi_channel=3))`
    from `rig_chasebliss.device import ChaseBlissDevice, ChaseBlissConfig`
  - Analog device: change to `Device(id="tumnus", type=DeviceType.ANALOG, config={"type":"manual"})`
  - Controller device: change to `MC6Device(id="mc6", config={"type":"controller","midi_channel":1,"banks":[]})`
    from `rig_morningstar.device import MC6Device`
  - `signal_chain` already updated in Wave 2 to `list[str]`. Confirm existing updates.
- Tests that assert `plan.cba_setup` behavior: these tests test the now-removed
  `detect_cba_setup` / `plan.cba_setup` field. Delete:
  - `test_cba_channel_not_established_triggers_setup`
  - `test_cba_preset_not_saved_triggers_build_preset`
  - `test_cba_setup_when_presets_already_saved`
  - `test_cba_registration_not_done_triggers_register`
  - `test_cba_fully_initialized_no_actions`
  - Any other tests asserting on `plan.cba_setup`
  These behaviors now live in `ChaseBlissDevice.setup()` — the plan engine no longer surfaces them.
- Remaining tests that assert scene plans, missing refs, unused presets: keep these, just update
  the device construction.

**test_diff.py**:
- Remove `ChaseBlissConfig`, `ControllerConfig`, `MidiConfig` imports from `rig.models.device`
- Remove `SignalChainPosition` import
- Update `_make_rig` / inline fixtures: same migration as test_plan.py above
  (HXStompDevice, ChaseBlissDevice, MC6Device)
- `signal_chain=[SignalChainPosition(...)]` → `signal_chain=["hx-stomp"]` (or whichever IDs)

**test_apply.py**:
- Remove `ChaseBlissConfig`, `ControllerConfig`, `MidiConfig` imports from `rig.models.device`
- Remove `SignalChainPosition` import
- Update `_make_rig` helper or inline fixtures: migrate to plugin device types
- `signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)]` → `signal_chain=["hx-stomp"]`

**test_appliers.py**:
- Remove `ChaseBlissConfig`, `ControllerConfig` imports from `rig.models.device`
- Remove `SignalChainPosition` import from `rig.models.signal_chain`
- Remove `manufacturer` kwargs from `Device(...)` calls
- Change `config=ChaseBlissConfig(midi_channel=3)` → import `ChaseBlissConfig` from
  `rig_chasebliss.device` and use that
- Change `config=ControllerConfig(...)` → use `{"type":"controller","midi_channel":1,"banks":[]}`
  or import `MC6Device` — but `test_appliers.py` tests the old applier classes (`ChaseBlissApplier`)
  which require the config type. The `ChaseBlissApplier` uses `isinstance(action, CbaSetupAction)` —
  check what config type it expects. Use locally-imported `ChaseBlissConfig` from plugin.
- `signal_chain=[SignalChainPosition(...)]` → `signal_chain=["cba-mood"]`

**test_graph.py**:
- Remove `ControllerConfig`, `ManualConfig`, `MidiConfig` imports from `rig.models.device`
- Remove `SignalChainPosition` import (already done in Wave 2, confirm)
- Update `_make_device` helper: remove `manufacturer`, `model` kwargs; change config to
  `config=None` or a simple dict: `config={"type": "manual"}` for ANALOG,
  `config={"type": "midi", "midi_channel": 1}` for DIGITAL,
  `config={"type": "controller"}` for CONTROLLER.

**test_catalog.py**:
- Remove `MidiConfig`, `ManualConfig`, `ChaseBlissConfig` imports from `rig.models.device`
- In `TestDevicePresets`: update device construction to use plain `Device(id=..., type=..., config={...})`
  without `manufacturer`/`model`
- Replace `ManualConfig()` → `{"type": "manual"}` or `None`
- Replace `MidiConfig(midi_channel=1)` → `{"type": "midi", "midi_channel": 1}`
- Replace `ChaseBlissConfig(midi_channel=2)` → import from `rig_chasebliss.device`
- In `TestLoaderValidation.test_valid_fixture_loads`: update assertions that used
  `rig.pedals` → `rig.devices`, `rig.digital_presets` → inline isinstance filter,
  `rig.hx_presets` → inline isinstance filter. Already done in Wave 1? Confirm.
- The test at line ~157 that writes YAML with `manufacturer:` and `model:` fields:
  the loader reads YAML and passes it to the plugin model class. After removing `manufacturer`
  and `model` from core `Device`, these YAML fields are silently ignored by Pydantic
  (because `Device` uses `model_config = ConfigDict(arbitrary_types_allowed=True)` and
  does NOT set `extra="forbid"`). Confirm this behavior — extra fields on Device YAML should
  be silently ignored, allowing existing YAML files with `manufacturer`/`model` to continue
  loading without error. If `Device` does have `extra="forbid"`, add `extra="ignore"` to
  `Device.model_config`. The goal is backward compat for YAML files that still have the fields.

**test_devices.py**:
- The CBA tests at lines ~424-455 that import `MidiConfig`, `ChaseBlissConfig` from
  `rig.models.device`: update to import from `rig_chasebliss.device`
- The MC6Device tests at lines ~312-327 that import `ControllerConfig` from `rig.models.device`:
  update to use a plain dict config `{"type":"controller","midi_channel":1,"banks":[...]}`
  since `MC6Device.config` is `Any`

**test_loader.py**:
- YAML strings in test fixtures that include `manufacturer:` and `model:` fields: these should
  continue to load successfully because `Device` (or the plugin model) silently ignores extra
  fields. Confirm no loader test fails due to unexpected `manufacturer`/`model` in YAML.
- Remove the comment "Controller device: scenes are wired to ControllerConfig by the loader"
  and update the mc6.yaml fixture string to not include `config: {type: controller, ...}` if
  ControllerConfig is gone — but actually the loader still reads this config, dispatches to
  `MC6Device` via plugin registry, and `MC6Device.config` accepts anything. The YAML config
  type `"controller"` dispatches to the `MC6Device` plugin model. Confirm the registry still
  has `"controller"` → `MC6Device` registered. If not, this is the source of test failure here.

**test_cli_plan.py**:
- Tests `test_cba_setup_actions_shown_in_setup_actions_section` and
  `test_cba_setup_action_uses_tilde_marker`: these test the "Setup Actions" section that was
  removed in Wave 3. Delete both tests. Also delete `test_cba_plan_summary_reflects_nonzero_count`.
- The `_write_cba_rig` helper and `_write_analog_rig` helper: keep these — other tests use them.
  But the CBA rig now will NOT produce "Setup Actions" in plan output (that's removed).
- Update `_write_cba_rig`: remove `manufacturer:` and `model:` fields from the YAML it writes
  (they will be silently ignored, but clean them up).

**test_mc6_generator.py**:
- Remove imports: `ControllerConfig`, `MidiConfig` from `rig.models.device`;
  `SignalChainPosition` from `rig.models.signal_chain`.
- Add imports: `MC6Device` from `rig_morningstar.device`; `HXStompDevice` from `rig_hx.device`.
- In `_make_rig()`:
  - Change `hx = Device(id="hx-stomp", manufacturer="Line6", model="HX Stomp", type=DeviceType.MODELER, config=MidiConfig(midi_channel=1), ...)` to `hx = Device(id="hx-stomp", type=DeviceType.MODELER, config={"type":"midi","midi_channel":1}, ...)` (keep presets unchanged).
  - Change `controller_device = Device(id="mc6", manufacturer=..., type=DeviceType.CONTROLLER, config=ControllerConfig(...))` to `controller_device = Device(id="mc6", type=DeviceType.CONTROLLER, config={"type":"controller","midi_channel":1,"banks":[...]})` — keep the banks list structure as-is, just replace `ControllerConfig(...)` with a dict.
  - Change `signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)]` → `signal_chain=["hx-stomp"]`.
- After updates, confirm `generate_mc6(rig)` still works — it accesses `rig.mc6` which is removed in Wave 1. Verify `rig_morningstar/generator.py` was already updated in Wave 3 to use direct controller lookup. If `generate_mc6` breaks, fix by having the test build the rig with the controller accessible via `rig.controller`.

After all test updates, run the full suite.
  </action>
  <verify>
    <automated>cd /Users/derekgliwa/dev/rig-cli && uv run pytest packages/ -q --tb=short 2>&1 | tail -30</automated>
  </verify>
  <done>
    All tests pass. `grep -rn "manufacturer\|ManualConfig\|MidiConfig\|ChaseBlissConfig\|ControllerConfig\|SignalChainPosition" packages/rig/tests/ | grep -v __pycache__ | grep "from rig.models"` returns zero lines.
    Wave 4 commit created: `refactor(models): remove manufacturer/model from Device; purge deprecated type refs from tests (SCHEMA-06)`
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML device files → Device model | Extra fields like manufacturer/model in YAML are silently ignored after removal |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-04 | Information Disclosure | Device.model_fields | accept | Removing fields reduces attack surface; no PII involved |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this phase |
</threat_model>

<verification>
After both tasks complete — run all six success criteria checks:

```bash
cd /Users/derekgliwa/dev/rig-cli

# Success criterion 1: device.py imports contain no removed config types
for TYPE in ManualConfig MidiConfig ChaseBlissConfig ControllerConfig; do
  COUNT=$(grep -v '^#' packages/rig/src/rig/models/device.py | grep -c "$TYPE" || true)
  echo "$TYPE in device.py: $COUNT (expected 0)"
done

# Success criterion 2: Control and ControlType absent from models/
grep -rn "class Control\b\|class ControlType" packages/rig/src/rig/models/ | grep -v __pycache__
# Expected: no output

# Success criterion 3: Rig has no compat shim properties
python -c "
from rig.models.rig import Rig
for attr in ['pedals','digital_presets','hx_presets','analog_presets','mc6','_controller_device']:
    assert not hasattr(Rig, attr) or not isinstance(getattr(Rig, attr, None), property), f'{attr} should not be a property on Rig'
print('PASS: all compat properties removed')
"

# Success criterion 4: Scene has no mc6_bank or mc6_switch
python -c "
from rig.models.scene import Scene
assert 'mc6_bank' not in Scene.model_fields
assert 'mc6_switch' not in Scene.model_fields
print('PASS: Scene clean')
"

# Success criterion 5: SignalChainPosition absent from models/signal_chain.py
test ! -f packages/rig/src/rig/models/signal_chain.py && echo "PASS: signal_chain.py deleted"

# Success criterion 6: All tests pass
uv run pytest packages/ -q
```
</verification>

<success_criteria>
All six acceptance criteria from the phase requirements:

1. `grep -c "ManualConfig\|MidiConfig\|ChaseBlissConfig\|ControllerConfig" packages/rig/src/rig/models/device.py` returns 0
2. `grep -rn "class Control\b\|class ControlType" packages/rig/src/rig/models/` returns no output
3. `hasattr(Rig, "pedals")` is False (and all other compat properties)
4. `"mc6_bank" not in Scene.model_fields` and `"mc6_switch" not in Scene.model_fields`
5. `packages/rig/src/rig/models/signal_chain.py` does not exist
6. `uv run pytest packages/ -q` exits 0

Wave 4 commit created:
`refactor(models): remove manufacturer/model from Device; purge deprecated type refs from tests (SCHEMA-06)`
</success_criteria>

<output>
Create `.planning/phases/09-core-model-cleanup/09-04-SUMMARY.md` when done
</output>
