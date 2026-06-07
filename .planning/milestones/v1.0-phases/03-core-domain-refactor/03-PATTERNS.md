# Phase 3: Core Domain Refactor - Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/rig/engine/plugin.py` | protocol + context | request-response | `src/rig/engine/appliers/base.py` | exact |
| `src/rig/engine/plugin_registry.py` | registry/dispatch | request-response | `src/rig/engine/appliers/registry.py` | exact |
| `src/rig/models/device.py` | model | CRUD | `src/rig/models/device.py` (self) | exact |
| `src/rig/models/controller.py` | model | CRUD | `src/rig/models/device.py` | role-match |
| `src/rig/models/rig.py` | model + graph | transform | `src/rig/models/rig.py` (self) | exact |
| `src/rig/config/loader.py` | loader/service | CRUD + transform | `src/rig/config/loader.py` (self) | exact |
| `tests/test_models.py` | test | CRUD | `tests/test_models.py` (self) | exact |
| `tests/test_loader.py` | test | CRUD | `tests/test_loader.py` (self) | exact |

---

## Pattern Assignments

### `src/rig/engine/plugin.py` (new file — protocol + context)

**Analog:** `src/rig/engine/appliers/base.py`

This is the primary pattern to copy. `DevicePlugin` follows `DeviceApplier` exactly. `PluginContext` is a subset of `ApplyContext` — same `@dataclass` style, fewer fields.

**Imports pattern** (`src/rig/engine/appliers/base.py` lines 1–15):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel

from rig.engine.state import DeviceState, RigState

if TYPE_CHECKING:
    from rig.engine.plan import DeviceAction
    from rig.models.rig import Rig
```

For `plugin.py`, the TYPE_CHECKING imports will be `from rig.models.rig import Rig` and `from rig.models.device import Device`. Import `RigState` directly (not under TYPE_CHECKING) because it's used in the dataclass field type.

**Protocol pattern** (`src/rig/engine/appliers/base.py` lines 37–38):
```python
class DeviceApplier(Protocol):
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext) -> DeviceApplyResult: ...
```

`DevicePlugin` follows this exactly with three methods instead of one:
```python
class DevicePlugin(Protocol):
    def plan(self, device: Device, ctx: PluginContext) -> ...: ...
    def diff(self, device: Device, ctx: PluginContext) -> ...: ...
    def apply(self, device: Device, ctx: PluginContext) -> ...: ...
```

**Context dataclass pattern** (`src/rig/engine/appliers/base.py` lines 26–34):
```python
@dataclass
class ApplyContext:
    dry_run: bool
    confirmation_io: ConfirmationIO
    midi: MidiManager | None = None
    connected_devices: set[str] = field(default_factory=set)
    state: RigState = field(default_factory=RigState)
    config_path: str | None = None
    rig: Rig | None = None
```

`PluginContext` is a trimmed version — only three fields, all required (no defaults except `RigState`):
```python
@dataclass
class PluginContext:
    state: RigState
    rig: Rig
    dry_run: bool
```

Note: `rig` is NOT `Optional` here — the plugin always has access to the full rig. This is a deliberate narrowing from `ApplyContext` where `rig: Rig | None`.

**Secondary analog:** `src/rig/engine/ports.py` lines 26–53 — shows the Protocol-only-methods pattern (no data fields on Protocol, just method stubs with `...`).

---

### `src/rig/engine/plugin_registry.py` (new file — registry/dispatch)

**Analog:** `src/rig/engine/appliers/registry.py`

This is the dict-dispatch pattern formalized into a class. The existing registry is module-level functions over a dict; `PluginRegistry` wraps that pattern in a class.

**Full analog** (`src/rig/engine/appliers/registry.py` lines 1–31):
```python
from __future__ import annotations

from rig.engine.appliers.analog import AnalogApplier
from rig.engine.appliers.base import DeviceApplier
from rig.engine.appliers.chase_bliss import ChaseBlissApplier
from rig.engine.appliers.mc6 import MC6Applier
from rig.engine.appliers.midi_device import MidiApplier

_cba_applier = ChaseBlissApplier()
_mc6_applier = MC6Applier()

_SCENE_APPLIERS: dict[str, DeviceApplier] = {
    "manual": AnalogApplier(),
    "midi": MidiApplier(),
    "chase_bliss": _cba_applier,
}


def get_scene_applier(config_type: str) -> DeviceApplier:
    """Return the DeviceApplier for the given pedal config_type."""
    return _SCENE_APPLIERS.get(config_type, MidiApplier())
```

`PluginRegistry` formalizes this as a class with `register(config_type, plugin)` and `get(config_type)` methods. The internal dict mirrors `_SCENE_APPLIERS`. Phase 3 leaves the registry empty (no registrations) — Phase 4 registers existing appliers.

**Pattern to copy:**
```python
from __future__ import annotations

from rig.engine.plugin import DevicePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DevicePlugin] = {}

    def register(self, config_type: str, plugin: DevicePlugin) -> None:
        self._plugins[config_type] = plugin

    def get(self, config_type: str) -> DevicePlugin | None:
        return self._plugins.get(config_type)
```

No module-level singleton in Phase 3 (CONTEXT.md D-10: exists and is wirable, but appliers not registered yet).

---

### `src/rig/models/device.py` (modified — DeviceType enum + discriminated union)

**Analog:** Self (existing file). Two concrete patterns to follow:

**DeviceType StrEnum** (`src/rig/models/device.py` lines 14–18):
```python
class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"
```

Add `CONTROLLER = "controller"` following the same `UPPER_CASE = "lowercase"` convention.

**Discriminated union** (`src/rig/models/device.py` lines 86):
```python
config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]
```

The new `ControllerConfig` joins this union. It follows the `Literal["type"]` pattern from existing configs:

**Existing Literal discriminator pattern** (`src/rig/models/device.py` lines 48–51, 55–58, 72–75):
```python
class ManualConfig(DeviceConfig):
    type: Literal["manual"] = "manual"

class MidiConfig(DeviceConfig):
    type: Literal["midi"] = "midi"

class ChaseBlissConfig(MidiConfig):
    type: Literal["chase_bliss"] = "chase_bliss"
```

New `ControllerConfig` follows this exactly:
```python
class ControllerConfig(DeviceConfig):
    type: Literal["controller"] = "controller"
    midi_channel: int = 1
    banks: list[dict[str, Any]] = []
    scenes: dict[str, Scene] = {}
```

The updated discriminated union becomes:
```python
config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig | ControllerConfig, Field(discriminator="type")]
```

---

### `src/rig/models/controller.py` (modified — Controller becomes Device subtype)

**Analog:** `src/rig/models/device.py` `Device` class (lines 81–121) and the existing `src/rig/models/controller.py`.

The existing `Controller(BaseModel)` is a peer of `Device`. Phase 3 restructures it so `Controller` IS a `Device` with `DeviceType.CONTROLLER`. The existing `MC6Config` banks pattern moves into `ControllerConfig`.

**Current pattern in `src/rig/models/controller.py`** (lines 9–28):
```python
class ControllerType(StrEnum):
    MC6 = "mc6"

class MC6Config(BaseModel):
    type: Literal["mc6"] = "mc6"
    midi_channel: int = 1
    banks: list[dict[str, Any]] = []

class Controller(BaseModel):
    id: str
    manufacturer: str
    model: str
    type: ControllerType
    config: MC6Config
```

After refactor, `Controller` is either removed entirely (replaced by `Device` with `DeviceType.CONTROLLER`) or becomes a thin typed alias. `ControllerConfig` in `device.py` absorbs `MC6Config`'s fields plus `scenes`.

**`Rig.mc6` property backward-compat pattern** (`src/rig/models/rig.py` lines 51–54):
```python
@property
def mc6(self) -> dict[str, Any]:
    if self.controller:
        return {"banks": self.controller.config.banks}
    return {}
```

This pattern shows how to add backward-compat properties on `Rig` when moving data between models.

---

### `src/rig/models/rig.py` (modified — add `apply_order()`, scenes move to Controller)

**Analog:** Self (existing file). The existing `@property` pattern on `Rig` for derived/computed values.

**Existing computed property pattern** (`src/rig/models/rig.py` lines 25–48):
```python
@property
def pedals(self) -> dict[str, Device]:
    return self.devices

@property
def digital_presets(self) -> dict[str, list[DigitalPreset]]:
    return {
        k: [p for p in v.presets if isinstance(p, DigitalPreset)]
        for k, v in self.devices.items()
    }
```

`apply_order()` is a method (not property — it computes a traversal, not a projection). It should be a plain method:
```python
def apply_order(self) -> list[Device]:
    """DFS from Controller root; children in signal chain order."""
```

**Backward-compat pattern for scenes access** — when `scenes` moves off `Rig`, preserve the existing read path:
```python
@property
def scenes(self) -> dict[str, Scene]:
    if self.controller and isinstance(self.controller.config, ControllerConfig):
        return self.controller.config.scenes
    return {}
```

Follow the same backward-compat approach as `pedals` → `devices` (lines 25–27).

**Signal chain order for DFS** — `signal_chain: list[SignalChainPosition]` is already sorted by `position` (integer). The `apply_order()` DFS visits children in `SignalChainPosition.position` order:
```python
sorted(self.signal_chain, key=lambda p: p.position)
```

---

### `src/rig/config/loader.py` (modified — load Controller as a device)

**Analog:** Self. The existing `_load_devices_dir` and `_parse_controller_legacy` patterns.

**YAML file loading pattern** (`src/rig/config/loader.py` lines 24–36):
```python
def _read_yaml(path: Path):
    if not path.exists():
        logger.error("Missing file: %s", path)
        raise FileNotFoundError_(f"Missing file: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data
    except yaml.YAMLError as e:
        logger.error("Invalid YAML in %s: %s", path, e)
        raise ParseError(f"Invalid YAML in {path}: {e}")
```

**Device parsing pattern** (`src/rig/config/loader.py` lines 39–41):
```python
def _parse_device(data: dict) -> Device:
    return Device(**data)
```

A new `_parse_controller_device` function follows this — pass raw YAML dict to `Device(**data)` now that Controller config is a proper `DeviceConfig` with discriminator.

**`load_rig` assembly pattern** (`src/rig/config/loader.py` lines 228–246):
```python
rig = Rig(
    name=rig_data.get("name", ""),
    description=rig_data.get("description"),
    midi_channel=rig_data.get("midi_channel"),
    signal_chain=chain,
    devices=devices,
    controller=controller,
    scenes=scenes,
)
```

After Phase 3, `scenes=` is removed from this call because scenes live on the Controller device's config. The `controller=` parameter may change type from `Controller` to `Device`.

**logger.info completion log** (`src/rig/config/loader.py` lines 240–244):
```python
logger.info(
    "Rig '%s' loaded successfully (%d devices, %d scenes)",
    rig.name,
    len(rig.devices),
    len(rig.scenes),
)
```

Update the log count to read `len(rig.scenes)` via the backward-compat property.

---

### `tests/test_models.py` (modified — test new Controller-as-Device shape)

**Analog:** Self. Existing test class structure.

**Test class + inline construction pattern** (`tests/test_models.py` lines 22–39):
```python
class TestPedalModels:
    def test_pedal_definition_round_trips(self):
        device = Device(
            id="tumnus",
            manufacturer="Wampler",
            model="Tumnus",
            type=DeviceType.ANALOG,
            config=ManualConfig(
                controls=[Control(name="Gain", type=ControlType.KNOB, min=0, max=10)]
            ),
        )
        assert device.id == "tumnus"
        assert device.config.controls[0].name == "Gain"
```

New tests for Controller follow the same inline-construction pattern with `DeviceType.CONTROLLER` and `ControllerConfig`.

**Enum value test pattern** (`tests/test_models.py` lines 36–39):
```python
def test_device_type_enum_values(self):
    assert DeviceType.DIGITAL.value == "digital"
    assert DeviceType.ANALOG.value == "analog"
    assert DeviceType.MODELER.value == "modeler"
```

Add `assert DeviceType.CONTROLLER.value == "controller"` to this test.

**`apply_order()` test** — new test method on a new or existing class:
```python
def test_apply_order_visits_devices_in_signal_chain_order(self):
    # Build a Rig with controller + 2 devices in signal chain
    # Assert apply_order() returns devices in position order
```

---

### `tests/test_loader.py` (modified — update fixtures to Controller-as-device YAML layout)

**Analog:** Self. The `rig_dir` pytest fixture pattern with `_write` helper.

**Fixture builder pattern** (`tests/test_loader.py` lines 9–47):
```python
def _write(base: Path, path: str, content: str):
    full = base / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)

@pytest.fixture
def rig_dir(tmp_path):
    d = tmp_path / "rig"
    d.mkdir()
    _write(d, "rig.yaml", "name: test-rig\nmidi_channel: 1\n")
    _write(d, "signal-chain.yaml", "chain: []\n")
    _write(d, "pedals/brothers.yaml", "id: brothers\n...")
    _write(d, "scenes/billy-clean.yaml", "name: billy-clean\n...")
    return d
```

After Phase 3, the `rig_dir` fixture must write a Controller device YAML (e.g. `devices/mc6.yaml` with `type: controller` config) and scenes nested under that Controller config, OR scenes as separate YAML files that the loader attaches to the Controller. Follow the same `_write` helper — just add new calls for the new layout.

**Scenes-via-controller assertion pattern** — existing assertion at line 80:
```python
def test_loads_scenes(self, rig_dir):
    config = load_rig(str(rig_dir))
    assert "billy-clean" in config.scenes  # backward-compat property still works
```

Keep this test passing via the backward-compat `Rig.scenes` property.

---

## Shared Patterns

### Protocol Definition (no ABC inheritance)
**Source:** `src/rig/engine/appliers/base.py` lines 37–38 and `src/rig/engine/ports.py` lines 26–53
**Apply to:** `src/rig/engine/plugin.py`
```python
class DevicePlugin(Protocol):
    def plan(self, device: Device, ctx: PluginContext) -> ...: ...
    def diff(self, device: Device, ctx: PluginContext) -> ...: ...
    def apply(self, device: Device, ctx: PluginContext) -> ...: ...
```
No `ABC`, no `@abstractmethod`. Structural subtyping only. Method bodies are `...`.

### Context as `@dataclass` (not Pydantic BaseModel)
**Source:** `src/rig/engine/appliers/base.py` lines 26–34
**Apply to:** `src/rig/engine/plugin.py` `PluginContext`

Runtime context objects that are not serialized use `@dataclass`. Domain data that is loaded from YAML uses `BaseModel`. `PluginContext` is runtime context → `@dataclass`.

### `Literal` type discriminator on configs
**Source:** `src/rig/models/device.py` lines 48–75
**Apply to:** New `ControllerConfig` in `src/rig/models/device.py`
```python
class ControllerConfig(DeviceConfig):
    type: Literal["controller"] = "controller"
```
Every config subtype has `type: Literal["<value>"] = "<value>"`. The value must be lowercase with underscores. This is what enables Pydantic's discriminated union.

### `from __future__ import annotations` + `TYPE_CHECKING` guard
**Source:** `src/rig/engine/appliers/base.py` lines 1–14, `src/rig/models/device.py` lines 1–11
**Apply to:** `src/rig/engine/plugin.py`, `src/rig/engine/plugin_registry.py`

Use `from __future__ import annotations` at the top of every new file. Use `TYPE_CHECKING` guard for imports that would create circular dependencies (e.g. `Rig` importing from engine, engine importing from models).

### `logger = logging.getLogger(__name__)`
**Source:** `src/rig/config/loader.py` line ~15, `src/rig/engine/appliers/analog.py`
**Apply to:** `src/rig/engine/plugin_registry.py` (if it logs registration), `src/rig/config/loader.py` (already present)

One `logger` per module, named by `__name__`.

### Backward-compat property aliases on `Rig`
**Source:** `src/rig/models/rig.py` lines 25–27, 51–54
**Apply to:** `src/rig/models/rig.py` when `scenes` moves off `Rig`

Keep `Rig.scenes` as a `@property` that reads from the Controller device's config. Same pattern as `Rig.pedals` aliasing `Rig.devices`.

---

## No Analog Found

All files in Phase 3 have close analogs. No files require relying solely on RESEARCH.md.

| File | Note |
|------|------|
| `src/rig/engine/plugin.py` | `apply_order()` DFS logic has no existing graph traversal analog — implement against `signal_chain` sort using `sorted(..., key=lambda p: p.position)` |

---

## Metadata

**Analog search scope:** `src/rig/engine/`, `src/rig/models/`, `src/rig/config/`, `tests/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-04
