# Phase 9: Core Model Cleanup — Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 15
**Analogs found:** 15 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/rig/src/rig/models/device.py` | model | transform | `packages/rig/src/rig/models/scene.py` | role-match |
| `packages/rig/src/rig/models/rig.py` | model | transform | `packages/rig/src/rig/models/device.py` | exact |
| `packages/rig/src/rig/models/scene.py` | model | transform | `packages/rig/src/rig/models/preset.py` | role-match |
| `packages/rig/src/rig/models/signal_chain.py` | model | — | *(delete)* | n/a |
| `packages/rig/src/rig/models/__init__.py` | config | — | existing `__init__.py` | exact |
| `packages/rig/src/rig/config/loader.py` | service | request-response | existing `loader.py` | exact |
| `packages/rig/src/rig/engine/plan/compute.py` | service | transform | existing `compute.py` | exact |
| `packages/rig/src/rig/engine/plan/models.py` | model | transform | existing `plan/models.py` | exact |
| `packages/rig/src/rig/engine/apply.py` | service | request-response | existing `apply.py` | exact |
| `packages/rig/src/rig/cli/commands/status.py` | controller | request-response | `packages/rig/src/rig/cli/commands/validate.py` | exact |
| `packages/rig/src/rig/cli/commands/validate.py` | controller | request-response | existing `validate.py` | exact |
| `packages/rig-chasebliss/src/rig_chasebliss/device.py` | model+service | request-response | existing `rig_chasebliss/device.py` | exact |
| `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` | utility | transform | existing `catalog.py` | exact |
| `packages/rig-morningstar/src/rig_morningstar/device.py` | model+service | request-response | existing `rig_morningstar/device.py` | exact |
| `packages/rig-morningstar/src/rig_morningstar/generator.py` | service | transform | existing `generator.py` | exact |

---

## Pattern Assignments

### `packages/rig/src/rig/models/device.py`

**Change:** Remove `ControlType`, `Control`, `DeviceConfig`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig` classes, and `manufacturer`/`model` fields from `Device`. Keep `DeviceType`, `Device`, and the `Preset` union type alias.

**Analog:** `packages/rig/src/rig/models/scene.py` (minimal Pydantic model with optional fields)

**Slim model pattern** (scene.py lines 1–16):
```python
from typing import Literal
from pydantic import BaseModel

class Scene(BaseModel):
    name: str
    description: str | None = None
    tempo: int | None = None
    presets: dict[str, str]
    tags: list[str] = []
```

**Target shape for Device after cleanup:**
- Remove: `ControlType`, `Control`, `DeviceConfig`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig`
- Remove from `Device`: `manufacturer: str | None`, `model: str | None`
- Remove `model_validator` that populates CBA controls (it references `manufacturer`/`model`)
- Keep: `DeviceType`, `Device` (with `id`, `name`, `type`, `config: Any`, `presets`), `Preset` union alias

**Imports pattern to keep** (device.py current, trimmed):
```python
from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
```

---

### `packages/rig/src/rig/models/rig.py`

**Change:** Remove compat properties (`pedals`, `_controller_device`, `controller`, `scenes`, `mc6`, `digital_presets`, `hx_presets`, `analog_presets`). Change `signal_chain: list[SignalChainPosition]` → `list[str]`. Add `scenes: dict[str, Scene]` as a real Pydantic field (not a property). Remove `ControllerConfig` and `SignalChainPosition` imports.

**Analog:** Current `rig.py` — the target is a stripped version of the same file.

**Target imports** (remove `ControllerConfig`, `SignalChainPosition`):
```python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict
from rig.models.device import Device, DeviceType
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
```

**Target Rig model shape:**
```python
class Rig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    signal_chain: list[str]          # was list[SignalChainPosition]
    devices: dict[str, Any] = {}
    scenes: dict[str, Scene] = {}    # was a @property reading from ControllerConfig
    midi_channel: int | None = None

    def apply_order(self) -> list[Device]: ...  # keep this, update for list[str] chain
```

**`apply_order` needs updating** — `DeviceGraph` currently reads `sc.device_ref` from `SignalChainPosition` objects (graph.py lines 36–38). After the change, `signal_chain` is `list[str]` so `DeviceGraph` must iterate it directly:
```python
# graph.py _current_ (lines 36-38):
chain_positions: dict[str, int] = {
    sc.device_ref: sc.position for sc in self._rig.signal_chain
}
# graph.py _after_: position is the list index
chain_positions: dict[str, int] = {
    device_id: idx for idx, device_id in enumerate(self._rig.signal_chain)
}
```
Note: `DeviceGraph._detect_cycles` also iterates `signal_chain` using `sc.device_ref` — update to iterate strings directly.

---

### `packages/rig/src/rig/models/scene.py`

**Change:** Remove `mc6_bank: int | None` and `mc6_switch: Literal[...] | None` fields.

**Target shape** (4 fields remain):
```python
class Scene(BaseModel):
    name: str
    description: str | None = None
    tempo: int | None = None
    presets: dict[str, str]
    tags: list[str] = []
```

---

### `packages/rig/src/rig/models/signal_chain.py`

**Change:** Delete this file entirely. No replacement — `signal_chain` becomes `list[str]` on `Rig`.

---

### `packages/rig/src/rig/models/__init__.py`

**Change:** Remove all exports for deleted types. Keep only types that still exist.

**Target `__init__.py`:**
```python
from rig.models.device import Device, DeviceType, Preset
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.rig import Rig, RigConfig
from rig.models.scene import Scene

__all__ = [
    "Device",
    "DeviceType",
    "Preset",
    "Rig",
    "RigConfig",
    "AnalogPreset",
    "DigitalPreset",
    "HXStompPreset",
    "Scene",
]
```

Remove from exports: `Control`, `ControlType`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `DeviceConfig`, `SignalChainPosition`.

---

### `packages/rig/src/rig/config/loader.py`

**Change:** Remove `ChaseBlissConfig`, `ControllerConfig` imports and the scene-wiring block that does `ctrl_device.config.model_copy(update={"scenes": scenes})`. Scenes are now loaded directly onto `Rig.scenes`. Remove `SignalChainPosition` import; build `signal_chain` as `list[str]`.

**Analog:** Same file — surgical removal.

**Current scene-wiring block to remove** (loader.py lines 216–225):
```python
# Wire scenes into device's ControllerConfig so Rig.scenes resolves correctly.
if scenes:
    ctrl_device = next((d for d in devices.values() if d.type == DeviceType.CONTROLLER), None)
    if ctrl_device is not None and isinstance(ctrl_device.config, ControllerConfig):
        updated_config = ctrl_device.config.model_copy(update={"scenes": scenes})
        devices[ctrl_device.id] = ctrl_device.model_copy(update={"config": updated_config})
```

**Replacement:** Pass `scenes` directly to `Rig(...)` constructor:
```python
rig = Rig(
    name=rig_data.get("name", ""),
    description=rig_data.get("description"),
    midi_channel=rig_data.get("midi_channel"),
    signal_chain=chain,   # now list[str] of device IDs
    devices=devices,
    scenes=scenes,        # new direct field
)
```

**Signal chain loading — current pattern** (loader.py, in `load_rig`):
```python
# Current: builds list[SignalChainPosition]
chain = [SignalChainPosition(**pos) for pos in chain_data]
```
**After:** Build `list[str]` preserving order — the simplest form is:
```python
chain = [pos.get("device") or pos.get("pedal") or pos.get("pedal_ref") for pos in chain_data]
```
Or if chain YAML already uses `device:` key, just: `[pos["device"] for pos in chain_data]`.

**Imports to remove from loader.py:**
- `ChaseBlissConfig`, `ControllerConfig` from `rig.models.device`
- `SignalChainPosition` from `rig.models.signal_chain`

---

### `packages/rig/src/rig/engine/plan/compute.py`

**Change:** Remove `detect_cba_setup` function and its call site. Remove `CbaSetupAction` import. Remove `cba_setup` from the returned `Plan(...)`.

**Current call site to remove** (compute.py lines 214–218):
```python
# TODO: 1.2 this is an example of something that should be in the cb plugin
cba_setup = detect_cba_setup(rig, actual)
if cba_setup:
    any_changes = True
    logger.debug("CBA setup actions: %d", len(cba_setup))
```

**Updated Plan construction** (remove `cba_setup=cba_setup`):
```python
return Plan(
    status=plan_status,
    scenes=scenes_plan,
    missing_refs=missing_refs,
    unused_presets=unused_presets,
)
```

**Logger summary line to update** (compute.py line 221–226) — remove CBA count:
```python
logger.info(
    "Plan computed: %s (%d scene(s) with changes)",
    plan_status,
    sum(1 for s in scenes_plan.values() if s.status != "unchanged"),
)
```

---

### `packages/rig/src/rig/engine/plan/models.py`

**Change:** Remove `CbaSetupAction` class and `cba_setup: list[CbaSetupAction] = []` field from `Plan`.

**Analog:** Same file. Target `Plan`:
```python
class Plan(BaseModel):
    status: Literal["clean", "changes_detected"]
    scenes: dict[str, ScenePlan] = {}
    missing_refs: list[str] = []
    unused_presets: list[str] = []
```

---

### `packages/rig/src/rig/engine/apply.py`

**Change:** Remove the CBA-specific phase 1 reference (`cba_results` list, `cba_setup` on `ApplyResult`). Update MC6 phase 2 to use `rig.controller` from the `devices` dict lookup (not from the compat property, which is being removed). The `controller` compat property disappears from `Rig` — apply.py currently uses `rig.controller` at line 180.

**Current MC6 block** (apply.py lines 179–208):
```python
if rig and rig.controller and not scene:
    mc6_device = rig.controller
    mc6_banks = mc6_device.config.banks if hasattr(mc6_device.config, "banks") else []
    ...
```

**After `rig.controller` is removed**, replace with explicit lookup:
```python
mc6_device = next(
    (d for d in rig.devices.values() if d.type == DeviceType.CONTROLLER),
    None,
)
if rig and mc6_device and not scene:
    ...
```

**`ApplyResult` — remove `cba_setup` field** (apply.py lines 33–38):
```python
class ApplyResult(BaseModel):
    status: Literal["completed", "cancelled", "no_changes"]
    scenes: list[SceneApplyResult] = []
```

---

### `packages/rig/src/rig/cli/commands/status.py` and `validate.py`

**Change:** Replace `rig.pedals` with `rig.devices` everywhere.

**Pattern from validate.py** (lines 36–44) shows the existing idiom — `rig.pedals` appears in:
- `validate.py` line 37: `"pedals": len(rig.pedals)`
- `validate.py` line 43: `len(rig.pedals)`
- `status.py` (multiple occurrences using `rig.pedals` to iterate devices)

**Replacement:** mechanical `rig.pedals` → `rig.devices`. No structural change needed.

---

### `packages/rig-chasebliss/src/rig_chasebliss/device.py`

**Change:** Remove `from rig.models.device import ChaseBlissConfig`. Define `ChaseBlissConfig` locally in this file (it moves here from `rig.models.device`).

**Analog:** The existing `device.py` already holds the device implementation. Add the config model at the top of the same file using the same Pydantic `BaseModel` pattern already in `rig.models.device`.

**ChaseBlissConfig to define locally** (currently at device.py lines 78–80 in rig/models/device.py):
```python
from typing import Literal
from pydantic import BaseModel

class ChaseBlissConfig(BaseModel):
    """Chase Bliss Audio pedal — MIDI with power-on channel learn."""
    type: Literal["chase_bliss"] = "chase_bliss"
    midi_channel: int | None = None
    midi_device_id: int | None = None
    controls: list["Control"] = []

    def get_cc_params(self, parameters: dict[str, float | str | bool]) -> list[dict[str, int]]:
        ...  # copy existing implementation from rig.models.device
```

**Import to remove:**
```python
# Remove:
from rig.models.device import ChaseBlissConfig, DeviceType
# Replace with:
from rig.models.device import DeviceType
# And define ChaseBlissConfig locally above ChaseBlissDevice
```

---

### `packages/rig-chasebliss/src/rig_chasebliss/catalog.py`

**Change:** Remove `from rig.models.device import Control, ControlType`. Define `Control` and `ControlType` locally.

**Analog:** Same file — the full `MOOD_MKII_CONTROLS` list already uses these types; just move the definitions in-file.

**Types to define locally** (currently in rig/models/device.py lines 21–39):
```python
from enum import StrEnum
from pydantic import BaseModel

class ControlType(StrEnum):
    KNOB = "knob"
    SWITCH = "switch"
    TOGGLE = "toggle"
    DIPSWITCH = "dipswitch"

class Control(BaseModel):
    name: str
    type: ControlType
    midi_cc: int
    min: int = 0
    max: int = 127
    expression_assignable: bool = False
    positions: list[str] = []
```

**`get_controls` signature stays the same** — but `manufacturer`/`model` args are now just free strings (no longer linked to `Device.manufacturer`/`Device.model`). The function signature does not change:
```python
def get_controls(manufacturer: str, model: str) -> list[Control]:
    return _CATALOG.get(f"{manufacturer}/{model}", [])
```

---

### `packages/rig-morningstar/src/rig_morningstar/device.py`

**Change:** Replace `rig.pedals` with `rig.devices` (line 106 in current file).

**Current usage** (device.py line 106):
```python
pedal = rig.pedals.get(pedal_id)
```

**After:**
```python
pedal = rig.devices.get(pedal_id)
```

No structural change. The `rig.pedals` compat property disappears; use `rig.devices` directly.

---

### `packages/rig-morningstar/src/rig_morningstar/generator.py`

**Change:** Replace `rig.mc6` with a direct lookup into `rig.controller.config.banks`.

**Current** (generator.py lines 15–16):
```python
mc6_config = rig.mc6
banks = mc6_config.get("banks", [])
```

**After** — `rig.mc6` compat property is removed. The MC6 device config holds `banks` directly:
```python
mc6_device = next(
    (d for d in rig.devices.values() if d.type == DeviceType.CONTROLLER),
    None,
)
banks = getattr(getattr(mc6_device, "config", None), "banks", []) if mc6_device else []
```

Or if `MC6Device.config` is typed, access directly:
```python
from rig.models.device import DeviceType
mc6_device = next(
    (d for d in rig.devices.values() if d.type == DeviceType.CONTROLLER), None
)
banks = mc6_device.config.banks if mc6_device and hasattr(mc6_device.config, "banks") else []
```

---

## Shared Patterns

### `config: Any` on plugin device models
**Source:** `packages/rig-chasebliss/src/rig_chasebliss/device.py` line 89, `packages/rig-morningstar/src/rig_morningstar/device.py` line 25

Both plugin `Device` models already use `config: Any`. After Phase 9, the core `Device` model in `rig.models.device` should also hold `config: Any` (it currently uses the discriminated union). This is the established plugin pattern:
```python
class ChaseBlissDevice(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    id: str
    name: str = ""
    config: Any
    type: DeviceType = DeviceType.DIGITAL
    presets: list[Any] = Field(default_factory=list)
```

### Pydantic BaseModel with `from __future__ import annotations`
**Source:** `packages/rig/src/rig/models/rig.py` lines 1–6

All domain model files use this header. Preserve it in all modified model files:
```python
from __future__ import annotations
from pydantic import BaseModel
```

### `rig.devices` iteration pattern
**Source:** `packages/rig/src/rig/engine/plan/compute.py` lines 31, 131

After `rig.pedals` is removed, the canonical iteration is:
```python
for device_id, device in rig.devices.items(): ...
device = rig.devices.get(device_id)
```

### Controller device lookup (replaces `rig.controller` property)
**Source:** `packages/rig/src/rig/models/rig.py` lines 36–39

After `rig.controller` compat property is removed, callers must look up the controller explicitly:
```python
ctrl = next(
    (d for d in rig.devices.values() if d.type == DeviceType.CONTROLLER),
    None,
)
```
Apply this pattern in: `apply.py`, `generator.py`, `graph.py`.

### Error handling in config loader
**Source:** `packages/rig/src/rig/config/errors.py` + `loader.py` lines 7–9

All validation failures in loader.py use project-specific exception types. Do not use bare `ValueError`. Continue raising `ValidationError`, `MissingReferenceError`, or `ParseError`:
```python
from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError, ValidationError
```

---

## No Analog Found

All files have close analogs. No files require falling back to RESEARCH.md patterns.

---

## Metadata

**Analog search scope:** `packages/rig/src/rig/`, `packages/rig-chasebliss/src/`, `packages/rig-morningstar/src/`
**Files scanned:** 18
**Pattern extraction date:** 2026-06-08
