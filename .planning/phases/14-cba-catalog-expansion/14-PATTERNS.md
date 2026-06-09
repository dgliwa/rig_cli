# Phase 14: CBA Catalog Expansion - Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 3 (catalog.py modification + 2 new catalog lists + tests)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` | model/config | transform | itself (MOOD_MKII_CONTROLS) | exact |
| `packages/rig-chasebliss/tests/test_catalog.py` | test | transform | `tests/test_catalog.py` (root) | role-match |

---

## Pattern Assignments

### `catalog.py` — `Control` model (lines 13-21)

**Analog:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` lines 13-21

**Existing `Control` model:**
```python
class Control(BaseModel):
    name: str = Field(..., min_length=1)
    type: ControlType
    midi_cc: int | None = None
    min: float | str | bool | None = None
    max: float | str | bool | None = None
    positions: list[str] = []
    expression_assignable: bool = False
```

**Pattern for adding `default` field** — follow `midi_cc` / `min` / `max` style (optional scalar, `= None`):
```python
class Control(BaseModel):
    name: str = Field(..., min_length=1)
    type: ControlType
    midi_cc: int | None = None
    min: float | str | bool | None = None
    max: float | str | bool | None = None
    default: float | None = None          # <-- add here, same pattern as min/max
    positions: list[str] = []
    expression_assignable: bool = False
```

No `Field(...)` wrapper needed — bare `= None` is the project convention for optional scalars (see `models.py` lines 12-15, `device.py` line 24).

---

### `catalog.py` — `MOOD_MKII_CONTROLS` list (lines 24-112)

**Source:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` lines 24-112

**Knob construction pattern** (single-line):
```python
Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127),
```

**Toggle construction pattern** (multi-line, with `positions`):
```python
Control(
    name="wet_channel",
    type=ControlType.TOGGLE,
    midi_cc=21,
    min=0,
    max=127,
    positions=["reverb", "delay", "slip"],
),
```

**Dipswitch construction pattern** (always `min=0, max=127`, on/off switches):
```python
Control(name="dip_l_bounce", type=ControlType.DIPSWITCH, midi_cc=66, min=0, max=127),
```

**Switch construction pattern** (momentary/latch):
```python
Control(name="true_bypass", type=ControlType.SWITCH, midi_cc=55, min=0, max=127),
```

**Missing controls to fix in MOOD_MKII_CONTROLS** — the TODO on line 23 references adding `default` values. After adding the field, update each KNOB `Control` to include `default=<midpoint_or_known_value>` where appropriate.

---

### `catalog.py` — `_CATALOG` dict and `get_controls()` (lines 114-120)

**Source:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` lines 114-120

```python
_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
}


def get_controls(manufacturer: str, model: str) -> list[Control]:
    return _CATALOG.get(f"{manufacturer}/{model}", [])
```

**Pattern for adding new pedals** — define a `list[Control]` constant named `<PEDAL>_CONTROLS`, then add an entry to `_CATALOG`:
```python
WOMBTONE_MKII_CONTROLS: list[Control] = [
    Control(name="...", type=ControlType.KNOB, midi_cc=..., min=0, max=127),
    ...
]

BROTHERS_AM_CONTROLS: list[Control] = [
    Control(name="...", type=ControlType.KNOB, midi_cc=..., min=0, max=127),
    ...
]

_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
    "Chase Bliss Audio/Wombtone MkII": WOMBTONE_MKII_CONTROLS,
    "Chase Bliss Audio/Brothers AM": BROTHERS_AM_CONTROLS,
}
```

Key format: `"<manufacturer>/<model>"` — must match `device.manufacturer` and `device.model` fields exactly as they appear in YAML (e.g., `"Chase Bliss Audio/Mood MkII"`).

---

### `catalog.py` — how `get_controls()` is called by callers

**Source:** `packages/rig-chasebliss/src/rig_chasebliss/device.py`

```python
from rig_chasebliss.catalog import Control
```

The `ChaseBlissConfig` model holds `controls: list[Control] = []` and `get_cc_params` iterates over it:
```python
def get_cc_params(self, parameters: dict[str, ...]) -> list[dict[str, int]]:
    result = []
    for ctrl in self.controls:
        if ctrl.midi_cc is not None and ctrl.name in parameters:
            result.append({"cc": ctrl.midi_cc, "value": int(parameters[ctrl.name])})
    return result
```

The `default` field does not affect `get_cc_params` — it is used upstream when building a "reset to defaults" CC list before applying preset-specific values.

---

### `packages/rig-chasebliss/tests/test_catalog.py` — test pattern

**Analog:** `tests/test_catalog.py` (root package) — `TestMoodMkiiCatalog` class

```python
from rig_chasebliss.catalog import MOOD_MKII_CONTROLS, ControlType

class TestMoodMkiiCatalog:
    def test_knob_count(self):
        knobs = [c for c in MOOD_MKII_CONTROLS if c.type == ControlType.KNOB]
        assert len(knobs) == 7

    def test_all_knobs_have_midi_cc(self):
        knobs = [c for c in MOOD_MKII_CONTROLS if c.type == ControlType.KNOB]
        assert all(c.midi_cc is not None for c in knobs)
```

**Pattern for new pedal tests:**
```python
from rig_chasebliss.catalog import WOMBTONE_MKII_CONTROLS, BROTHERS_AM_CONTROLS, ControlType

class TestWombtoneControls:
    def test_all_controls_have_midi_cc(self):
        assert all(c.midi_cc is not None for c in WOMBTONE_MKII_CONTROLS)

    def test_knob_defaults_present(self):
        knobs = [c for c in WOMBTONE_MKII_CONTROLS if c.type == ControlType.KNOB]
        assert all(c.default is not None for c in knobs)
```

Test file lives at: `packages/rig-chasebliss/tests/test_catalog.py` (currently only `__init__.py` exists there — this is a greenfield test file).

---

## Shared Patterns

### Optional scalar field with `= None`
**Source:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` lines 15-17, `packages/rig-chasebliss/src/rig_chasebliss/models.py` lines 12-15
```python
preset_id: str | None = None
midi_cc: int | None = None
min: float | str | bool | None = None
```
No `Field(default=None)` — bare `= None` is the convention throughout.

### Pydantic `BaseModel` imports
**Source:** `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` lines 1-3
```python
from enum import StrEnum
from pydantic import BaseModel, Field
```
`Field` is already imported in `catalog.py` — only needed for `Field(..., min_length=1)` on `name`. New fields with `= None` don't require `Field`.

### Test imports for rig-chasebliss package
```python
import pytest
from rig_chasebliss.catalog import <CONTROLS_LIST>, ControlType, get_controls
```

## No Analog Found

None — all files have close analogs within the same `catalog.py` module or the root `tests/test_catalog.py`.

## Metadata

**Analog search scope:** `packages/rig-chasebliss/`, `tests/`, `packages/rig/src/rig/models/`
**Files scanned:** 8
**Pattern extraction date:** 2026-06-08
