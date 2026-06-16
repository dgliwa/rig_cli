# Phase 22: Retire the Legacy Device Model — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/rig/src/rig/engine/plugin.py` | model/protocol | transform | `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` | role-match (StrEnum addition) |
| `packages/rig/src/rig/models/rig.py` | model | CRUD | `packages/rig/src/rig/models/graph.py` | exact (Device Protocol consumer) |
| `packages/rig/src/rig/models/graph.py` | utility | transform | self (update import source) | exact |
| `packages/rig/src/rig/models/__init__.py` | config | transform | self (re-export update) | exact |
| `packages/rig/src/rig/engine/apply.py` | service | request-response | `packages/rig-analog/src/rig_analog/device.py` | partial (guard removal) |
| `packages/rig-analog/src/rig_analog/device.py` | model | request-response | self (update import source) | exact |
| `packages/rig/tests/conftest.py` | utility | transform | `packages/rig/tests/fakes.py` | role-match (Protocol-satisfying test double) |
| `packages/rig/tests/test_models.py` | test | CRUD | `packages/rig/tests/test_graph.py` | exact (same Device usage) |
| `packages/rig/tests/test_plan.py` | test | CRUD | self (migrate Device→FakeDevice) | exact |
| `packages/rig/tests/test_diff.py`, `test_appliers.py`, `test_graph.py`, `test_catalog.py` | test | CRUD | `packages/rig/tests/test_graph.py` | exact |

---

## Pattern Assignments

### `packages/rig/src/rig/engine/plugin.py` — Add `DeviceType` StrEnum

**Analog:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py`

The project defines StrEnums in the module where they are semantically owned. `ControlType` lives in `catalog.py` (the CBA catalog module) — not in models. `DeviceType` should similarly live in `plugin.py` (the engine plugin contract module) because it is used at engine runtime, not just in models.

**StrEnum pattern** (`rig_chasebliss/catalog.py` lines 1–9):
```python
from enum import StrEnum

class ControlType(StrEnum):
    KNOB = "knob"
    SWITCH = "switch"
    TOGGLE = "toggle"
    DIPSWITCH = "dipswitch"
```

**Apply to `plugin.py`** — add `DeviceType` immediately after the module docstring and before the `from __future__` block's existing imports. Copy the comment block from `models/device.py` lines 11–14 explaining the Literal/StrEnum coexistence rationale:

```python
from enum import StrEnum

# DeviceType StrEnum is for runtime comparisons (engine, CLI, plan output).
# Config submodels use Literal type fields (e.g. Literal["chase_bliss"]) — Pydantic
# requires Literal for discriminated union dispatch. The two are orthogonal: StrEnum
# describes device kind; Literal identifies config schema. Both must coexist.
class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"
    CONTROLLER = "controller"
```

**Existing import block** (`plugin.py` lines 30–42) — `DeviceType` requires only `from enum import StrEnum` added to the standard-library block above `from __future__ import annotations`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, Self
```

---

### `packages/rig/src/rig/models/rig.py` — Change `devices: dict[str, Any]` to `dict[str, Device]`

**Analog:** `packages/rig/src/rig/models/graph.py`

`graph.py` already imports `Device` from `rig.engine.plugin` (after this phase; currently from `rig.models.device`). `rig.py` should do the same.

**Import pattern** (`graph.py` lines 1–7 — post-migration target):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from rig.engine.plugin import Device, DeviceType   # after DeviceType moves here

if TYPE_CHECKING:
    from rig.models.rig import Rig
```

**`Rig.devices` field change** (`rig.py` lines 18–19):

Before:
```python
from rig.models.device import Device, DeviceType
...
devices: dict[str, Any] = {}
```

After:
```python
from rig.engine.plugin import Device, DeviceType
...
devices: dict[str, Device] = {}
```

**Remove** `from typing import Any` if `Any` is no longer used (verify — `scenes` property uses `Any` for `raw_scenes`; keep if needed).

**`Rig.model_config` comment** (`rig.py` line 13-14) — the `arbitrary_types_allowed=True` comment references "legacy Device model during P3 migration". Update the comment to reflect that it is now needed for concrete plugin types only:
```python
# arbitrary_types_allowed so concrete Device plugin types (AnalogDevice, etc.)
# satisfy the Device Protocol stored in devices dict.
model_config = ConfigDict(arbitrary_types_allowed=True)
```

---

### `packages/rig/src/rig/models/graph.py` — Update import source for `Device` and `DeviceType`

**Analog:** self

Only one import line changes. The rest of the file is untouched.

**Before** (`graph.py` line 7):
```python
from rig.models.device import Device, DeviceType
```

**After**:
```python
from rig.engine.plugin import Device, DeviceType
```

The `TYPE_CHECKING` guard pattern already in place (lines 9–10) is the correct pattern — no changes needed there:
```python
if TYPE_CHECKING:
    from rig.models.rig import Rig
```

---

### `packages/rig/src/rig/models/__init__.py` — Re-export `DeviceType` from new location

**Analog:** self (current `__init__.py`)

Current exports (`__init__.py` lines 1–12):
```python
from rig.models.device import Device, DeviceType, Preset
from rig.models.rig import Rig, RigConfig
from rig.models.scene import Scene

__all__ = [
    "Device",
    "DeviceType",
    "Rig",
    "Preset",
    "Scene",
    "RigConfig",
]
```

After `models/device.py` is deleted, re-export `Device` and `DeviceType` from `rig.engine.plugin`, and `Preset` (Protocol) from `rig.engine.plugin` as well:

```python
from rig.engine.plugin import Device, DeviceType, Preset
from rig.models.rig import Rig, RigConfig
from rig.models.scene import Scene

__all__ = [
    "Device",
    "DeviceType",
    "Rig",
    "Preset",
    "Scene",
    "RigConfig",
]
```

This preserves backward-compat for any consumer doing `from rig.models import DeviceType`.

---

### `packages/rig/src/rig/engine/apply.py` — Remove `hasattr` guards

**Analog:** `packages/rig-analog/src/rig_analog/device.py`

`AnalogDevice` shows every concrete device unconditionally implements `setup()` and `apply()`. The `Device` Protocol in `plugin.py` enforces both. Once `Rig.devices` is typed as `dict[str, Device]`, all values satisfy the Protocol — `hasattr` checks are redundant.

**Guards to remove** (`apply.py` lines 95 and 127):

Line 95 — remove the guard, call unconditionally:
```python
# BEFORE
if hasattr(device, "setup"):
    result = device.setup(setup_ctx)

# AFTER
result = device.setup(setup_ctx)
```

Line 127 — remove the guard, call unconditionally:
```python
# BEFORE
if device is None or not hasattr(device, "apply"):
    ...

# AFTER — keep only the `device is None` check if it exists for other reasons;
# remove the hasattr(device, "apply") portion entirely
```

Verify the full context around line 127 to understand what falls in the `else` branch before removing.

---

### `packages/rig-analog/src/rig_analog/device.py` — Update `DeviceType` import source

**Analog:** self

Only one import line changes:

```python
# BEFORE (line 11)
from rig.models.device import DeviceType

# AFTER
from rig.engine.plugin import DeviceType
```

All other code in `AnalogDevice` is unchanged.

---

### `packages/rig/tests/conftest.py` — Add `FakeDevice` Protocol-satisfying class

**Analog:** `packages/rig/tests/fakes.py` (InMemoryPromptAdapter / InMemoryStateAdapter pattern)

The project's existing test-double convention (`fakes.py`) uses plain Python classes (no Pydantic) that implement the target Protocol with deterministic behavior. `FakeDevice` follows the same pattern — a minimal class satisfying `engine.plugin.Device` Protocol for tests that previously used `Device(BaseModel)`.

**Test-double class pattern** (`fakes.py` lines 17–52):
```python
class InMemoryPromptAdapter:
    """Fake ConfirmationIO that returns configured responses."""

    def __init__(self, default: str = "confirm", side_effect: list[str] | None = None) -> None:
        ...

    def prompt_device(self, ...) -> str:
        return self._next()
```

**Apply to `FakeDevice`** — place in `packages/rig/tests/conftest.py` (the only conftest.py in the packages tree, currently only a sys.path shim). Add `FakeDevice` as a module-level class so all tests import it from `tests.conftest` or via pytest fixture:

```python
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from rig.engine.plugin import (
    DeviceApplyContext,
    DeviceApplyResult,
    DeviceType,
    SetupContext,
    SetupResult,
)

_worktree_src = os.path.join(os.path.dirname(__file__), "src")
if _worktree_src not in sys.path:
    sys.path.insert(0, _worktree_src)
elif sys.path.index(_worktree_src) != 0:
    sys.path.remove(_worktree_src)
    sys.path.insert(0, _worktree_src)


@dataclass
class FakePreset:
    """Minimal preset satisfying rig.engine.plugin.Preset Protocol."""
    id: str
    name: str = ""
    preset_number: int | None = None


@dataclass
class FakeDevice:
    """Protocol-satisfying test double for rig.engine.plugin.Device.

    Replaces Device(BaseModel) in tests. Use this wherever tests previously
    constructed Device(id=..., type=..., config=..., presets=[...]).
    """
    id: str
    type: DeviceType
    config: Any = None
    name: str = ""
    presets: list[FakePreset] = field(default_factory=list)

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> FakeDevice:
        return cls(id=data["id"], type=DeviceType(data.get("type", "analog")), config=data.get("config"))

    def setup(self, ctx: SetupContext) -> SetupResult:
        return SetupResult()

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        return None

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        return DeviceApplyResult(device=self.id, status="skipped", preset="")
```

**Important:** `FakeDevice` uses `@dataclass` not `BaseModel`. This matches the project convention — `@dataclass` for runtime context objects / test doubles that are not serialized (`ApplyContext` in `appliers/base.py` is also a `@dataclass`).

**Controller scenes** — tests that build controller `FakeDevice` instances with `config={"scenes": {...}}` still work because `Rig.scenes` accesses `cfg.get("scenes", {})` when `isinstance(cfg, dict)` (`rig.py` lines 33–34). No change needed to `FakeDevice.config`.

---

### Test files — Migrate `Device(BaseModel)` to `FakeDevice`

**Analog:** `packages/rig/tests/test_graph.py` (current `_make_device` helper pattern)

Every test file follows the same migration pattern. The analog is `test_graph.py`'s `_make_device` factory:

```python
def _make_device(id: str, type: DeviceType, config=None) -> Device:
    if config is None:
        if type in (DeviceType.ANALOG,):
            config = {"type": "manual"}
        elif type == DeviceType.CONTROLLER:
            config = {"type": "controller", "banks": []}
        else:
            config = {"type": "midi", "midi_channel": 1}
    return Device(id=id, type=type, config=config)
```

**Migration rule for all 8 test files:**

1. Replace `from rig.models.device import Device, DeviceType` with:
   ```python
   from rig.engine.plugin import DeviceType
   from tests.conftest import FakeDevice
   ```

2. Replace every `Device(id=..., type=..., config=..., presets=[...])` call with `FakeDevice(id=..., type=..., config=..., presets=[...])`.

3. Helper function return type annotations: change `-> Device` to `-> FakeDevice`.

**Per-file scope:**

| Test File | Usage of `Device(BaseModel)` | Notes |
|---|---|---|
| `test_models.py` | `_make_controller_device`, `_make_analog_device` helpers + `TestRigConfig`, `TestApplyOrder` | Also tests `Rig.controller` return type — update annotation |
| `test_plan.py` | `_make_rig` helper builds 4 `Device` instances | `hx`, `bro`, `tum`, `ctrl` all become `FakeDevice` |
| `test_apply.py` | `_make_config` and `_make_concrete_config` — `ctrl` is `Device`; `hx` and `bro` are already concrete plugin types | Only the `ctrl = Device(id="mc6", ...)` calls → `FakeDevice` |
| `test_diff.py` | `_make_rig` builds `hx`, `bro`, `ctrl` as `Device` | Same pattern as `test_plan.py` |
| `test_graph.py` | `_make_device` factory | Update factory return type only |
| `test_catalog.py` | Import only — `Device` used only in `from rig.models.device import Device` | Remove import; check if `Device` is used in body |
| `test_appliers.py` | Lines 189–211 inside `test_detect_cba_setup_fresh_device_produces_all_phases` | Inline `Device(...)` calls → `FakeDevice(...)` |
| `test_loader.py` | Line 168 inline reference | Check context and replace |

---

## Shared Patterns

### `TYPE_CHECKING` guard for circular import avoidance

**Source:** `packages/rig/src/rig/engine/plugin.py` lines 37–42 and `packages/rig/src/rig/models/graph.py` lines 9–10

**Apply to:** `rig.py` and `graph.py` after import source changes

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rig.models.rig import Rig
```

`rig.engine.plugin` already imports `rig.models.rig.Rig` inside `TYPE_CHECKING`. After `DeviceType` moves into `plugin.py`, `rig.py` imports from `rig.engine.plugin` — this is safe (no cycle) because `plugin.py` only imports `Rig` under `TYPE_CHECKING`.

### `@dataclass` for test doubles (not `BaseModel`)

**Source:** `packages/rig/src/rig/engine/appliers/base.py` (`ApplyContext` dataclass) and `packages/rig/tests/fakes.py` (plain class pattern)

**Apply to:** `FakeDevice` and `FakePreset` in `conftest.py`

```python
from dataclasses import dataclass, field

@dataclass
class FakeDevice:
    id: str
    type: DeviceType
    config: Any = None
    name: str = ""
    presets: list[FakePreset] = field(default_factory=list)
```

### Protocol structural subtyping — no inheritance

**Source:** `packages/rig/src/rig/engine/plugin.py` docstring and `AnalogDevice` implementation

`FakeDevice` must NOT inherit from `Device` Protocol or `BaseModel`. It satisfies the Protocol structurally. `AnalogDevice` (a `BaseModel`) satisfies `Device` Protocol the same way — by having matching fields and methods, not by inheriting:

```python
class AnalogDevice(BaseModel):  # no "(Device)" inheritance
    id: str
    name: str = ""
    ...
    def setup(self, ctx: SetupContext) -> SetupResult: ...
    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult: ...
    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None: ...
```

### Import order convention

**Source:** All source files in `packages/rig/src/rig/`

```python
from __future__ import annotations      # 1. future
                                         # 2. stdlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, Self
                                         # 3. third-party (pydantic, rich, mido)
from pydantic import BaseModel
                                         # 4. internal rig.* imports
from rig.engine.state import RigState

if TYPE_CHECKING:                        # 5. TYPE_CHECKING-only imports last
    from rig.models.rig import Rig
```

---

## No Analog Found

All files have clear analogs. No file in this phase introduces a pattern with no existing codebase example.

---

## Metadata

**Analog search scope:** `packages/rig/src/`, `packages/rig/tests/`, `packages/rig-analog/src/`, `packages/rig-chasebliss/src/`
**Files scanned:** 18
**Pattern extraction date:** 2026-06-15
