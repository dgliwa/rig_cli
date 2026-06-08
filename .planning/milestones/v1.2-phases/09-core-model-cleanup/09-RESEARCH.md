# Phase 9: Core Model Cleanup — Research

**Researched:** 2026-06-08
**Domain:** Python/Pydantic model refactoring — removing plugin-specific types from core
**Confidence:** HIGH

---

## Summary

Phase 9 surgically removes all plugin-specific config types (`ManualConfig`, `MidiConfig`,
`ChaseBlissConfig`, `ControllerConfig`), CBA-specific types (`Control`, `ControlType`),
backwards-compat shim properties from `Rig`, MC6-specific fields from `Scene`, and
`SignalChainPosition` from core models. The plugin architecture is already in place — all four
plugin device types (`AnalogDevice`, `HXStompDevice`, `ChaseBlissDevice`, `MC6Device`) are
already implemented as concrete Pydantic models in their respective packages and registered via
entry points. This phase finishes the migration by deleting the old residue that those plugins
were wrapping.

The biggest risk is the `rig.scenes` property: it currently routes through `ControllerConfig`
stored in the controller device. After removing `ControllerConfig` from core, `scenes` must
move to a direct `dict[str, Scene]` field on `Rig`, populated by the loader. The plan/compute
engine, status/validate CLI commands, and both plugin device files use `rig.scenes`
extensively — all of those callers continue to work once `rig.scenes` becomes a real field
rather than a computed property.

The second biggest risk is test breakage: roughly half the test files use `Device` + config
types directly (as test fixtures). These tests must be migrated to use plugin device types or
updated to not depend on the removed types.

**Primary recommendation:** Remove in dependency-order waves, starting with the lowest-risk
leaf removals (`Scene` fields, `SignalChainPosition`) and working upward to the
highest-coupling removals (`Device.config` discriminated union, `ControllerConfig`,
`rig.scenes` routing).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-01 | Remove `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig` from `device.py` | Plugin configs move to or already exist in their packages; `Device.config` becomes `Any` |
| MODEL-02 | Remove `Control` and `ControlType` from core | Already only used by `rig-chasebliss`; move both to `rig_chasebliss/` |
| MODEL-03 | Remove compat shims from `Rig` (`pedals`, `digital_presets`, `hx_presets`, `analog_presets`, `mc6`, `_controller_device`) | All callers can use `rig.devices` and `rig.scenes` directly; `scenes` must become a real field |
| MODEL-04 | Remove `mc6_bank` and `mc6_switch` from `Scene` | No caller outside tests actually reads these fields |
| SCHEMA-03 | Remove `SignalChainPosition` from `signal_chain.py` | `Rig.signal_chain` becomes `list[str]` (ordered device IDs) |
| SCHEMA-06 | Remove `manufacturer` and `model` from core `Device` | `_populate_cba_controls` validator must move to `ChaseBlissDevice`; catalog lookup signature changes |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Python 3.12+, uv, Typer, Pydantic v2, Mido+rtmidi — no dependency changes
- `Protocol`-first abstractions — existing `Device` Protocol in `engine/plugin.py` stays
- All domain models extend `BaseModel`; `model_copy()` / `model_dump_json()` used throughout
- Pydantic discriminated unions use `Annotated` + `Field(discriminator=...)`
- Use `|` union syntax (Python 3.10+ style)
- `from __future__ import annotations` in files with forward references
- Test with `uv run pytest tests/ -q`
- Scope is `refactor(models):` commits

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Plugin config types (`MidiConfig`, `ChaseBlissConfig`, etc.) | Plugin package | — | Plugin owns all knowledge of its device format |
| Control/CC metadata (`Control`, `ControlType`) | Plugin package (`rig-chasebliss`) | — | Only CBA has CC-mapped controls; not a core concern |
| Scene storage on `Rig` | Core (`Rig` model field) | Loader populates | Scenes are cross-cutting (used by plan engine, apply, generators); belong on `Rig` directly |
| Signal chain ordering | Core (`Rig.signal_chain`) | — | `list[str]` of device IDs in order is simpler and sufficient |
| Discriminated dispatch for device construction | Loader + Plugin Registry | — | Entry-point dispatch is already implemented; `Device.config: Any` is the correct core type |

---

## Removal Scope Map

### `packages/rig/src/rig/models/device.py`

**Remove entirely:**
- `ControlType` (StrEnum) — move to `rig_chasebliss/`
- `Control` (BaseModel) — move to `rig_chasebliss/`
- `ManualConfig` — move to `rig_analog/` (or inline in `AnalogDevice` if config is trivially empty)
- `MidiConfig` — move to `rig_hx/` as `HXConfig` (or keep as `MidiConfig` in `rig_hx/`)
- `ChaseBlissConfig` — already imported by `rig_chasebliss/device.py` and `rig_chasebliss/catalog.py`; define natively there
- `ControllerConfig` — move to `rig_morningstar/` as `MC6Config`
- `DeviceConfig` base class — no longer needed once all subclasses are gone
- `_populate_cba_controls` model_validator on `Device` — move to `ChaseBlissDevice.model_validator`

**Change:**
- `Device.config` type annotation: `Annotated[ManualConfig | MidiConfig | ..., Field(discriminator="type")]` → `Any`
- `Device.manufacturer: str` → remove (SCHEMA-06)
- `Device.model: str` → remove (SCHEMA-06)
- `Device.get_scene_pc_command()` — can stay on `Device` (uses `self.config.midi_channel` via `Any`; safe with `getattr`)

**Keep:**
- `DeviceType` (StrEnum) — still used by graph, apply, plan, all plugin devices
- `Preset` type alias — used by loader and plan engine
- `Device` class itself — used by `DeviceGraph`, tests, loader

**New import after removal:**
```python
# device.py post-cleanup — only these remain at top level
from enum import StrEnum
from typing import Annotated, Any
from pydantic import BaseModel, Field
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
```

---

### `packages/rig/src/rig/models/rig.py`

**Remove:**
- `ControllerConfig` import
- `DeviceType` import (only used in `_controller_device`; stays imported if `controller` property kept)
- `SignalChainPosition` import
- `@property pedals` — callers switch to `rig.devices`
- `@property _controller_device` — internal; inline at `controller` property if `controller` property is kept
- `@property digital_presets` — callers switch to inline isinstance filtering
- `@property hx_presets` — same
- `@property analog_presets` — same
- `@property mc6` — generator switches to `rig.controller.config.banks` via plugin config

**Change:**
- `signal_chain: list[SignalChainPosition]` → `signal_chain: list[str]`
- `scenes` becomes a real Pydantic field: `scenes: dict[str, Scene] = {}`
  - Remove the `@property scenes` that routes through `ControllerConfig`
  - Add `scenes: dict[str, Scene] = {}` as a declared field

**Keep `controller` property (reduced):** The apply engine (`engine/apply.py`) at line 180 uses
`rig.controller` to find the MC6 device for programming. This property should stay but simplify:
```python
@property
def controller(self) -> Any | None:
    for device in self.devices.values():
        if getattr(device, "type", None) == DeviceType.CONTROLLER:
            return device
    return None
```

**New imports after cleanup:**
```python
from rig.models.device import Device, DeviceType
from rig.models.scene import Scene
# SignalChainPosition import removed
# ControllerConfig import removed
```

---

### `packages/rig/src/rig/models/scene.py`

**Remove:**
- `mc6_bank: int | None` field
- `mc6_switch: Literal["A", "B", "C", "D", "E", "F"] | None` field
- `Literal` import if no longer used

No callers outside of tests read `mc6_bank` or `mc6_switch` from runtime code. Safe to delete.

---

### `packages/rig/src/rig/models/signal_chain.py`

**Remove entire file** after removing `SignalChainPosition` from `Rig.signal_chain`.

Signal chain becomes `list[str]` — ordered device IDs. The loader currently builds
`[SignalChainPosition(**pos) for pos in signal_data.get("chain", [])]`. After this change,
the loader will parse device order from the new single-file schema (Phase 10 concern) or
keep the chain as a simple list of strings from the YAML.

For Phase 9, the loader can accept `chain: [device_id_1, device_id_2]` format and build
`list[str]` directly. Existing multi-file fixture YAML uses `{pedal: device_id, position: N}`
objects — the loader needs a compatibility read that extracts just the device ID string.

---

### `packages/rig/src/rig/models/__init__.py`

**Remove from `__all__` and imports:**
- `Control`, `ControlType`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`

**Keep:**
- `Device`, `DeviceConfig` (keep empty base or remove if nothing references it), `DeviceType`
- `Rig`, `Preset`, `Scene`
- `AnalogPreset`, `DigitalPreset`, `HXStompPreset`
- `RigConfig` alias

**Remove:**
- `SignalChainPosition`

---

### `packages/rig/src/rig/config/loader.py`

**Remove imports:**
- `ChaseBlissConfig`, `ControllerConfig` from `rig.models.device`
- `SignalChainPosition` from `rig.models.signal_chain`

**Change `load_rig`:**
- `chain = [SignalChainPosition(**pos) for pos in ...]` → `chain = [pos.get("pedal") or pos.get("device") for pos in signal_data.get("chain", [])]`
  (extracts device ID string from the existing `{pedal: id, position: N}` YAML format)
- Remove the `ControllerConfig`-based scene wiring block (lines 217-225). Scenes load directly
  into `Rig.scenes` instead of being stuffed into the controller device's config.
- `_validate_references` uses `rig.controller.id` — update to `getattr(rig.controller, "id", None)`
- `_validate_references` uses `isinstance(device.config, ChaseBlissConfig)` — this CBA-specific
  validation must move. Two options:
  - Move the parameter validation into `rig_chasebliss` (e.g., a `validate()` method on `ChaseBlissDevice` that core calls generically)
  - Move it to Phase 11 (CLEANUP-01) since it's a TODO marker anyway
  - **Recommended:** Remove from core loader now; the validation still happens inside
    `ChaseBlissDevice.setup()` when the device is actually used. Document as known gap.

**New `load_rig` scene wiring:**
```python
# After loading devices and scenes, wire scenes directly onto rig
rig = Rig(
    name=rig_data.get("name", ""),
    description=rig_data.get("description"),
    midi_channel=rig_data.get("midi_channel"),
    signal_chain=chain,
    devices=devices,
    scenes=scenes,   # NEW: direct field, not via ControllerConfig
)
```

---

### `packages/rig/src/rig/engine/plan/compute.py`

**Remove:**
- `detect_cba_setup()` function — moves to `rig_chasebliss/device.py` (already partially
  duplicated there as `_detect_cba_setup_for_device`)
- Local `from rig.models.device import ChaseBlissConfig` import inside `detect_cba_setup`
- `cba_setup` from `Plan` (see `plan/models.py` section)

**Change:**
- `for scene_name, scene in rig.scenes.items()` — already works once `scenes` is a real field
- `pedal.config.midi_channel` access — plan compute already uses `pedal.config.midi_channel`
  which works via `Any` config attribute access (Python duck typing). Safe.

**After removal, `compute_plan` stops calling `detect_cba_setup`. The CBA setup action
detection happens in `ChaseBlissDevice.setup()` at apply time, which is already implemented.**

---

### `packages/rig/src/rig/engine/plan/models.py`

**Remove (or defer to Phase 11):**
- `CbaSetupAction` model — the TODO says "move to cba plugin"

**Decision:** `CbaSetupAction` is used by `plan/compute.py` (`detect_cba_setup`), `engine/apply.py`
(`plan.cba_setup` list), `Plan.cba_setup` field, `cli/commands/plan.py` (renders cba_setup),
and `rig_chasebliss/device.py` (builds `CbaSetupAction` instances). The type is already
imported in `rig_chasebliss/device.py` from `rig.engine.plan.models`. Moving it to the plugin
would create a circular dependency (core `Plan` model references a plugin type).

**Recommended approach:** Keep `CbaSetupAction` in `engine/plan/models.py` for now (it is a
plan artifact type, not a device config type). Remove it in Phase 11 (CLEANUP-01) once the
plan architecture is refactored. This avoids a circular import.

**Change `Plan` model:** Remove `cba_setup: list[CbaSetupAction]` if `detect_cba_setup` is
removed from `compute_plan`. However, `rig_chasebliss/device.py`'s `setup()` does its own
CBA setup at apply time — `Plan` never needs to carry CBA setup actions.

**Recommended minimal change for Phase 9:** Remove `detect_cba_setup` from `compute.py` and
remove `cba_setup` from `Plan`. The CBA setup actions are emitted at apply-time by
`ChaseBlissDevice.setup()`, not at plan-time. The `plan` CLI output currently renders
`cba_setup` — that rendering block must be removed too (`cli/commands/plan.py` lines 69-82).

---

### `packages/rig/src/rig/engine/apply.py`

**Change line 180:**
```python
if rig and rig.controller and not scene:
```
This already uses `rig.controller` property which will stay. No import changes needed.

---

### `packages/rig/src/rig/cli/commands/status.py`

**Change:**
- `rig.pedals` → `rig.devices`
- `rig.digital_presets.get(pid, [])` + `rig.analog_presets.get(pid, [])` + `rig.hx_presets.get(pid, [])` →
  `len(device.presets)`
- `rig.scenes` → already works as a direct field

---

### `packages/rig/src/rig/cli/commands/validate.py`

**Change:**
- `len(rig.pedals)` → `len(rig.devices)`
- `rig.scenes` → already works

---

### `packages/rig-chasebliss/src/rig_chasebliss/catalog.py`

**Change:**
- `from rig.models.device import Control, ControlType` →
  define `Control` and `ControlType` natively in `rig_chasebliss/`
- `get_controls(manufacturer: str, model: str)` — signature must change since `Device` will no
  longer have `manufacturer`/`model` fields. Options:
  1. Keep `get_controls(key: str)` where key is `"Chase Bliss Audio/MOOD MKII"` and callers
     pass it explicitly from YAML data during device construction
  2. Remove the catalog-driven auto-populate entirely; require `controls` to be listed in
     the device YAML (the sample_rig fixture already does this)
  **Recommended:** Remove `_populate_cba_controls` validator from core `Device`. The
  sample_rig fixture already has controls inline. Auto-population via catalog was a convenience
  that relied on `manufacturer`/`model` fields being on `Device`. With those gone, controls
  must be explicitly listed in YAML. Document this as a breaking change.

---

### `packages/rig-chasebliss/src/rig_chasebliss/device.py`

**Change:**
- `from rig.models.device import ChaseBlissConfig, DeviceType` →
  define `ChaseBlissConfig` natively in `rig_chasebliss/`, keep `DeviceType` import from core
- The `isinstance(self.config, ChaseBlissConfig)` checks must use the locally-defined type
- `_detect_cba_setup_for_device` already uses `from rig.engine.plan.models import CbaSetupAction`
  — keep this until `CbaSetupAction` moves in Phase 11

---

### `packages/rig-morningstar/src/rig_morningstar/device.py`

**Change:**
- `rig.pedals.get(pedal_id)` → `rig.devices.get(pedal_id)`
- `rig.scenes.get(scene_name)` → already works as direct field

---

### `packages/rig-morningstar/src/rig_morningstar/generator.py`

**Change:**
- `rig.mc6` → `rig.controller.config.banks if rig.controller and hasattr(rig.controller.config, "banks") else []`
  OR: `generator.py` can be updated to accept the controller device directly
- `rig.scenes` → already works

---

### Plugin packages: `rig-analog`, `rig-hx`

**rig-analog/device.py:** Only imports `DeviceType` from core — no changes needed for Phase 9.

**rig-hx/device.py:** Only imports `DeviceType` from core — no changes needed. However,
`HXStompDevice.setup()` accesses `self.config.midi_channel` — since `config: Any`, this
continues to work.

---

## `Device.config` Answer

**After Phase 9, `Device.config` is typed as `Any`.**

This is already partially the case: all plugin device classes (`AnalogDevice`, `ChaseBlissDevice`,
`HXStompDevice`, `MC6Device`) declare `config: Any`. Core `Device` is the only holdout with the
full discriminated union. After removal, `Device.config: Any` follows the same pattern.

The loader uses `PluginRegistry.get_model(config_type)` to dispatch to the correct plugin class —
the plugin class owns its own `config` type. The loader creates a temporary `Device(**data)` to
parse config through Pydantic, then hands off to the plugin model class. After this phase, the
loader will construct plugin models directly from raw YAML data (not through core `Device`).

**Pydantic v2 note:** With `config: Any` and `model_config = ConfigDict(arbitrary_types_allowed=True)`,
Pydantic v2 allows any value — the plugin's own validator handles type enforcement. `[VERIFIED: codebase grep]`

---

## `Rig.signal_chain` Answer

**After Phase 9, `Rig.signal_chain` is `list[str]`.**

Each string is a device ID in signal-chain order. `DeviceGraph` currently reads `pos.device_ref`
from `SignalChainPosition` objects. After the change, it reads each string directly:

```python
# models/graph.py — after SCHEMA-03
chain_positions: dict[str, int] = {}
for i, device_id in enumerate(rig.signal_chain):
    if device_id in seen:
        raise CycleError(...)
    seen.add(device_id)
    chain_positions[device_id] = i
```

The loader currently parses the `signal-chain.yaml` format:
```yaml
chain:
  - pedal: brothers
    position: 1
```
and builds `[SignalChainPosition(**pos)]`. After removal, the loader extracts the device ID:
```python
chain = [
    pos.get("device") or pos.get("pedal") or pos.get("device_ref")
    for pos in signal_data.get("chain", [])
    if pos.get("device") or pos.get("pedal") or pos.get("device_ref")
]
```
This keeps the multi-file `signal-chain.yaml` format readable through Phase 10. Phase 10
switches to single-file ordering (SCHEMA-01/02).

`DeviceGraph` also uses `pos.device_ref` and the `pedal_ref` backward-compat property — both
disappear when `SignalChainPosition` is removed; `DeviceGraph` gets a simpler `list[str]` loop.

---

## `Rig.scenes` Answer

**After Phase 9, `scenes: dict[str, Scene]` is a direct Pydantic field on `Rig`.**

Currently `scenes` is a property that routes through `ControllerConfig.scenes`. The loader at
lines 217-225 wires scenes into the controller device's config. After removing `ControllerConfig`,
the loader places scenes directly on `Rig`:

```python
rig = Rig(
    ...
    scenes=scenes,   # dict[str, Scene] loaded from scenes/ dir
)
```

All existing callers of `rig.scenes` (`compute_plan`, `apply.py`, `morningstar/device.py`,
`morningstar/generator.py`, `rig_chasebliss/device.py`) continue to work without changes to
the call site.

---

## Migration Sequence

Execute in this order to keep tests green at each step:

**Wave 1 — Leaf removals (no callers depend on each other)**
1. `Scene`: remove `mc6_bank`, `mc6_switch` fields (MODEL-04)
2. `Rig`: add `scenes: dict[str, Scene]` as direct field; update loader to populate it directly; remove `ControllerConfig`-wiring block from loader; remove `_controller_device`, `pedals`, `digital_presets`, `hx_presets`, `analog_presets`, `mc6` properties (MODEL-03); keep `controller` property using `DeviceType` check
3. Update `status.py` and `validate.py` to use `rig.devices` and `len(device.presets)` directly

**Wave 2 — Signal chain simplification**
4. Change `Rig.signal_chain` from `list[SignalChainPosition]` to `list[str]`; update loader to extract device IDs; update `DeviceGraph` to iterate `list[str]`; delete `signal_chain.py` (SCHEMA-03)

**Wave 3 — Remove plugin configs from core**
5. Define `ChaseBlissConfig` natively in `rig_chasebliss/device.py`; remove `ChaseBlissConfig` from core `device.py`; update `rig_chasebliss/catalog.py` to define `Control`/`ControlType` locally (MODEL-01, MODEL-02 for CBA part)
6. Define `ControllerConfig` natively in `rig_morningstar/device.py` as `MC6Config`; remove from core; update `morningstar/generator.py` to not use `rig.mc6` (MODEL-01 for controller part); update `morningstar/device.py` to use `rig.devices`
7. Define `MidiConfig` natively in `rig_hx/device.py`; `ManualConfig` natively in `rig_analog/device.py`; remove both from core (MODEL-01 for remaining parts)

**Wave 4 — Remove manufacturer/model and cleanup**
8. Remove `Device.manufacturer` and `Device.model` fields; remove `_populate_cba_controls` validator; remove `Control`, `ControlType` from core; update `device.py` imports; update `models/__init__.py` (SCHEMA-06, MODEL-02)
9. Remove `detect_cba_setup` from `plan/compute.py`; remove `cba_setup` from `Plan` and rendering from `plan.py` CLI command; update `engine/apply.py` to not reference `plan.cba_setup`
10. Update test files to use plugin device types or plain dicts instead of removed core types

---

## Risk: `_populate_cba_controls` Validator

**What it does:** On `Device` construction, if `config` is `ChaseBlissConfig` and `controls` is
empty, it calls `rig_chasebliss.catalog.get_controls(self.manufacturer, self.model)` and
populates `config.controls`.

**Problem:** This validator lives on core `Device` and:
1. Imports `ChaseBlissConfig` at runtime (already a cross-package dependency)
2. Imports from `rig_chasebliss.catalog` (plugin import inside core — architectural violation)
3. Reads `manufacturer`/`model` fields which are being removed by SCHEMA-06

**Fix:** Remove the validator entirely. The `mood.yaml` fixture already has `controls:` listed
inline — confirming the explicit-YAML approach works. The auto-catalog-lookup was a convenience
that depended on `manufacturer`/`model` fields. Without those fields, `ChaseBlissDevice` cannot
perform the lookup anyway (it has no `manufacturer`/`model`).

The `get_controls(manufacturer, model)` function in `rig_chasebliss/catalog.py` still works for
users who call it explicitly with known values. Moving the catalog lookup into `ChaseBlissDevice`
as a model_validator is not recommended — without `manufacturer`/`model` on the device, there
is no lookup key. Controls must be explicitly declared in YAML.

**Action:** Remove `_populate_cba_controls` from core `Device`. Document that CBA devices
require explicit `controls:` in their YAML. The catalog can remain as a reference/helper
for users populating their YAML.

---

## `CbaSetupAction` Placement

**Keep `CbaSetupAction` in `rig/engine/plan/models.py` for Phase 9.**

Reasoning:
- Moving it to `rig-chasebliss` would require the core `Plan` model to import from a plugin,
  creating a circular dependency
- The TODO marker says "move to cba plugin" — this is CLEANUP-01 territory (Phase 11)
- `rig_chasebliss/device.py` already imports `CbaSetupAction` from `rig.engine.plan.models`;
  the import direction is correct (plugin imports from core)

**What does change in Phase 9:** `detect_cba_setup` moves OUT of `plan/compute.py` into
`rig_chasebliss/device.py`'s `setup()` method (already done — `_detect_cba_setup_for_device`
exists there). Remove `detect_cba_setup` from core. Remove `cba_setup` from `Plan` model.
Remove the plan CLI rendering of `cba_setup` (lines 69-82 of `plan.py`). `CbaSetupAction`
type itself stays in `plan/models.py` until Phase 11.

---

## Plugin Impact Summary

| Package | Files Changed | What Changes |
|---------|--------------|-------------|
| `rig-analog` | `device.py` | Define `ManualConfig` locally (trivial — `type="manual"`, no fields needed beyond that); no other changes |
| `rig-hx` | `device.py` | Define `HXConfig` (formerly `MidiConfig`) locally with `midi_channel: int`; `self.config.midi_channel` access continues to work |
| `rig-chasebliss` | `catalog.py`, `device.py` | Define `Control`, `ControlType`, `ChaseBlissConfig` locally; remove import from core; `ChaseBlissConfig` must include `controls: list[Control]` and `get_cc_params()` |
| `rig-morningstar` | `device.py`, `generator.py` | Define `MC6Config` locally with `banks: list[dict]` and `scenes: dict[str, Scene]`; `rig.pedals` → `rig.devices`; `rig.mc6` → access config directly |

No plugin changes are needed for `rig-analog` or `rig-hx` regarding `DeviceType` — both
import it from core and it stays there.

---

## Common Pitfalls

### Pitfall 1: `rig.scenes` stops working

**What goes wrong:** After removing `ControllerConfig` from the loader scene-wiring block,
`rig.scenes` returns `{}` because the `@property` still routes through `ControllerConfig` which
no longer exists.
**Why it happens:** Removing the property before adding the field, or forgetting to update the
loader to populate `scenes=scenes` on `Rig` construction.
**How to avoid:** Wave 1 step 2 — add `scenes` field AND update loader in the same commit.
**Warning signs:** Any test using `rig.scenes` starts returning empty dict.

### Pitfall 2: `DeviceGraph` breaks on `list[str]` signal chain

**What goes wrong:** `DeviceGraph` calls `pos.device_ref` on string objects, raising
`AttributeError: 'str' object has no attribute 'device_ref'`.
**Why it happens:** `graph.py` is not updated in the same wave as `signal_chain.py` removal.
**How to avoid:** Update `graph.py` in Wave 2 step 4 simultaneously with changing `Rig.signal_chain`.
**Warning signs:** `test_graph.py` failures with AttributeError.

### Pitfall 3: Tests break because `Device` requires `manufacturer`/`model`

**What goes wrong:** All test fixtures that construct `Device(id=..., manufacturer="...", model="..., ...)` fail with Pydantic validation error once those fields are removed.
**Why it happens:** `test_plan.py`, `test_graph.py`, `test_catalog.py`, `test_apply.py`,
`test_appliers.py`, `test_mc6_generator.py`, `test_loader.py`, `test_cli_plan.py`, `test_cli.py`
all use `Device` with `manufacturer`/`model`.
**How to avoid:** Wave 4 step 8 — when removing fields from core `Device`, update ALL test
helpers (`_make_device`, `_make_rig`, inline fixture writes) in the same commit.
**Warning signs:** `test_plan.py` fails en masse with `ValidationError`.

### Pitfall 4: `rig_chasebliss/catalog.py` imports `Control`/`ControlType` from core

**What goes wrong:** After removing from `device.py`, `catalog.py` raises `ImportError`.
**Why it happens:** `Control`, `ControlType` must be defined in `rig_chasebliss/` BEFORE
they are removed from core.
**How to avoid:** In Wave 3 step 5, define them in the plugin first (or in the same commit as
the core removal). The classes are identical to their core counterparts.

### Pitfall 5: `loader.py` CBA validation uses `ChaseBlissConfig`

**What goes wrong:** Removing `ChaseBlissConfig` import from `loader.py` leaves the validation
block at lines 169-188 broken (references removed type).
**Why it happens:** The validation block is inline in `_validate_references`. It will fail at
import time or runtime.
**How to avoid:** Remove the entire CBA-specific validation block from `_validate_references`
in Wave 3 step 5. This validation is not lost — `ChaseBlissDevice.setup()` validates params
when the device is used.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/rig/tests/ -q --tb=short` |
| Full suite command | `uv run pytest packages/rig/tests/ -v` |

**Current baseline:** 289 tests pass. [VERIFIED: codebase run]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | Config types absent from core imports | unit | `uv run pytest packages/rig/tests/test_models.py -x` | ✅ (needs update) |
| MODEL-02 | `Control`/`ControlType` absent from core | unit | `uv run pytest packages/rig/tests/test_catalog.py -x` | ✅ (needs update) |
| MODEL-03 | `rig.pedals` raises `AttributeError` | unit | `uv run pytest packages/rig/tests/test_models.py -x` | ✅ (needs update) |
| MODEL-04 | `Scene` has no `mc6_bank`/`mc6_switch` | unit | `uv run pytest packages/rig/tests/test_models.py -x` | ✅ (needs update) |
| SCHEMA-03 | `signal_chain` is `list[str]` | unit | `uv run pytest packages/rig/tests/test_graph.py -x` | ✅ (needs update) |
| SCHEMA-06 | `Device` has no `manufacturer`/`model` | unit | `uv run pytest packages/rig/tests/test_models.py -x` | ✅ (needs update) |

### Wave 0 Gaps
- No new test files needed; existing tests must be updated to remove use of deleted types
- New negative tests should be added: assert `Device` construction fails if `manufacturer`/`model` passed; assert `Scene` ignores `mc6_bank`; assert `rig.scenes` works as direct field

---

## Environment Availability

Step 2.6 SKIPPED — Phase 9 is pure code/model refactoring with no external tool dependencies.

---

## Security Domain

`security_enforcement` is enabled. Phase 9 is a model cleanup refactor with no new auth,
session, input validation, or cryptography surfaces introduced. ASVS categories V2/V3/V4/V6
do not apply. V5 (Input Validation) is passively maintained: removing fields from Pydantic
models reduces the validation surface (fewer fields = fewer injection vectors), which is
strictly positive.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Removing `detect_cba_setup` from `plan/compute.py` is safe because `ChaseBlissDevice.setup()` already handles CBA setup detection | CbaSetupAction Placement | Plan output would lose CBA setup visibility; `plan` CLI would not warn about uninitialized CBA devices |
| A2 | `rig.mc6` compat property is only used by `morningstar/generator.py` and no test exercises it via `rig.mc6` directly | Rig.py removal scope | If other callers exist, those would break silently |
| A3 | `controls` must be inline in YAML after removing `_populate_cba_controls` — the sample fixture already does this | _populate_cba_controls Risk | Any user with a CBA device YAML relying on auto-populate would get empty controls |

---

## Open Questions

1. **Does `Plan.cba_setup` need to stay for `plan` CLI display?**
   - What we know: `plan.py` CLI renders `cba_setup` at lines 69-82; `detect_cba_setup` populates it from core
   - What's unclear: Whether the plan output should continue to show CBA setup requirements
   - Recommendation: Remove `cba_setup` from `Plan` in Phase 9 along with `detect_cba_setup`. The plan output becomes simpler (just scenes). CBA setup happens silently at apply-time. Users can see what happened in `apply` output.

2. **`morningstar/generator.py` calls `rig.mc6` — what replaces it?**
   - What we know: `rig.mc6` returns `{"banks": ctrl.config.banks}` from `ControllerConfig`
   - What's unclear: After removing `ControllerConfig` from core, `rig.controller.config` is `Any` — `hasattr(rig.controller.config, "banks")` would work
   - Recommendation: In `generator.py`, replace `rig.mc6` with `rig.controller.config.banks if rig.controller and hasattr(rig.controller.config, "banks") else []`

3. **`test_catalog.py` `TestLoaderValidation.test_valid_fixture_loads` uses `rig.pedals`, `rig.digital_presets`, `rig.hx_presets`**
   - What we know: These will be removed from `Rig`
   - Recommendation: Update these test assertions to use `rig.devices` and `isinstance` filtering inline

---

## Sources

### Primary (HIGH confidence)
- Codebase grep: `device.py`, `rig.py`, `scene.py`, `signal_chain.py`, `loader.py`, `plan/compute.py`, `plan/models.py`, `apply.py` — all read directly [VERIFIED: codebase grep]
- Pydantic v2 `arbitrary_types_allowed`, `model_copy()`, `ConfigDict` — confirmed in use throughout codebase [VERIFIED: codebase grep]
- Entry point registration pattern: `pyproject.toml` in all 4 plugin packages [VERIFIED: codebase grep]
- Test suite baseline: 289 passing [VERIFIED: test run]

### Secondary (MEDIUM confidence)
- Pydantic v2 `Any`-typed fields work correctly with attribute access on arbitrary objects [ASSUMED — confirmed by existing plugin device types using `config: Any` successfully]

---

## Metadata

**Confidence breakdown:**
- Removal scope: HIGH — every reference verified by grep across all packages
- Migration sequence: HIGH — dependency order derived from actual import graph
- Plugin impact: HIGH — all plugin source files read directly
- `CbaSetupAction` placement: MEDIUM — architectural judgment call on circular import risk

**Research date:** 2026-06-08
**Valid until:** N/A (internal codebase — stays current until code changes)
