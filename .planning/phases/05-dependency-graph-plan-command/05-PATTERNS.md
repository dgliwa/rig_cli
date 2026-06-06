# Phase 5: Dependency Graph & Plan Command - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 7 (2 new, 5 modified)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/rig/models/graph.py` | model | transform | `src/rig/models/rig.py` | exact |
| `src/rig/engine/plan/models.py` | model | transform | `src/rig/engine/plan/models.py` (self) | exact |
| `src/rig/engine/plan/compute.py` | service | batch | `src/rig/engine/plan/compute.py` (self) | exact |
| `src/rig/cli/commands/plan.py` | controller | request-response | `src/rig/cli/commands/plan.py` (self) | exact |
| `src/rig/engine/apply.py` | service | event-driven | `src/rig/engine/apply.py` (self) | exact |
| `tests/test_graph.py` | test | — | `tests/test_plan.py` | role-match |
| `tests/test_plan.py` | test | — | `tests/test_plan.py` (self) | exact |

---

## Pattern Assignments

### `src/rig/models/graph.py` (model, transform)

**Analog:** `src/rig/models/rig.py`

**Imports pattern** (rig.py lines 1-11):
```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from rig.models.device import Device, DeviceType
from rig.models.signal_chain import SignalChainPosition
```

**Core model pattern** — wrap `Rig`, expose computed properties (rig.py lines 13-103):
```python
class DeviceGraph(BaseModel):
    """Wraps Rig to provide topological ordering with cycle detection."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rig: Rig

    def ordered_devices(self) -> list[Device]:
        """Return devices in apply order with cycle detection."""
        ...
```

Key points copied from `Rig.apply_order()` (lines 79-103):
- Build `chain_positions` dict from `signal_chain`
- Separate `in_chain` vs `off_chain`
- `in_chain.sort(key=lambda d: chain_positions[d.id])`
- Controller device appended last
- Return `in_chain + off_chain + [ctrl]`

**Cycle detection pattern** — raise `ConfigError` subclass (see `src/rig/config/errors.py`):
```python
from rig.config.errors import ConfigError

class CycleError(ConfigError):
    """Signal chain contains a cycle."""
```

No existing cycle detection in the codebase — implement with a visited-set DFS on the `signal_chain` positions. Raise `CycleError` with the offending device IDs in the message.

---

### `src/rig/engine/plan/models.py` (model, transform) — MODIFY

**Analog:** existing `src/rig/engine/plan/models.py` (lines 1-39)

**Current imports** (lines 1-6):
```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
```

**Existing `DeviceAction`** (lines 8-16) — add `before` / `after` fields following the same optional-field pattern:
```python
class DeviceAction(BaseModel):
    device: str
    device_type: str
    status: Literal["configure", "verify", "analog"]
    preset_name: str = ""
    preset_number: int | None = None
    midi_channel: int | None = None
    instructions: list[str] = []
    # NEW:
    before: list[str] = []   # device IDs that must apply before this
    after: list[str] = []    # device IDs that must apply after this
```

**Existing `Plan`** (lines 35-39) — add diagnostic list fields:
```python
class Plan(BaseModel):
    status: Literal["clean", "changes_detected"]
    scenes: dict[str, ScenePlan] = {}
    cba_setup: list[CbaSetupAction] = []
    # NEW:
    missing_refs: list[str] = []    # device IDs referenced in scenes but absent from rig.devices
    unused_presets: list[str] = []  # preset IDs defined but never referenced in any scene
```

Use `list[str] = []` default (not `Field(default_factory=list)`) — matches existing field style in this file.

---

### `src/rig/engine/plan/compute.py` (service, batch) — MODIFY

**Analog:** existing `src/rig/engine/plan/compute.py`

**Imports + logger pattern** (lines 1-11):
```python
from __future__ import annotations

import logging
from typing import Literal

from rig.engine.plan.models import CbaSetupAction, DeviceAction, Plan, ScenePlan
from rig.engine.state import DeviceState, RigState, read_state
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import Rig

logger = logging.getLogger(__name__)
```

**Missing-ref detection pattern** — mirrors existing `pedal is None` guard (lines 102-106):
```python
# In compute_plan, collect missing_refs alongside the existing warning:
if pedal is None:
    logger.warning("Pedal '%s' referenced in scene '%s' not found", pedal_id, scene_name)
    missing_refs.add(pedal_id)   # NEW — accumulate instead of just warning
    continue
```

**Unused-preset detection pattern** — new set-diff after scene loop:
```python
all_preset_ids: set[str] = {p.id for dev in rig.devices.values() for p in dev.presets}
referenced: set[str] = {pid for scene in rig.scenes.values() for pid in scene.presets.values()}
unused_presets = sorted(all_preset_ids - referenced)
```

**DeviceGraph integration** — replace `rig.apply_order()` call with `DeviceGraph(rig=rig).ordered_devices()`:
```python
from rig.models.graph import DeviceGraph

graph = DeviceGraph(rig=rig)
ordered = graph.ordered_devices()  # raises CycleError if cycle detected
```

**Plan construction** (lines 188-192) — extend to pass new fields:
```python
return Plan(
    status=plan_status,
    scenes=scenes_plan,
    cba_setup=cba_setup,
    missing_refs=sorted(missing_refs),
    unused_presets=unused_presets,
)
```

---

### `src/rig/cli/commands/plan.py` (controller, request-response) — MODIFY

**Analog:** existing `src/rig/cli/commands/plan.py`

**Imports + shared wiring** (lines 1-22):
```python
from __future__ import annotations

import logging
from pathlib import Path

import typer

from rig.cli._shared import (
    _CONFIG_OPTION,
    _FORMAT_OPTION,
    _SCENE_OPTION,
    _VERBOSE_OPTION,
    _emit_json,
    app,
    console,
)
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.plan import compute_plan
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)
```

**Command signature pattern** (lines 25-31) — add `--show-unchanged` flag following `typer.Option` style:
```python
@app.command()
def plan(
    config: str = _CONFIG_OPTION,
    scene: str | None = _SCENE_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
    show_unchanged: bool = typer.Option(False, "--show-unchanged", help="Show unchanged scenes"),
):
```

**ConfigError guard pattern** (lines 35-39):
```python
try:
    rig = load_rig(config)
except ConfigError as e:
    console.print(f"[red]✗[/red] {e}")
    raise typer.Exit(1)
```

**Exit code pattern** — `typer.Exit(1)` for errors, `typer.Exit(0)` (implicit) for clean. For `changes_detected`, add explicit `raise typer.Exit(2)` at end so callers can detect pending changes in CI:
```python
if result.status == "changes_detected":
    raise typer.Exit(2)
```

**Status icon pattern** (lines 55-58) — reuse existing dict lookup style:
```python
status_icon = {"new": "[cyan]+[/cyan]", "changed": "[yellow]~[/yellow]", "unchanged": "[green] [/green]"}[sp.status]
```

**Two-section output pattern** — write changes section first (existing loop), then a second loop or block for warnings:
```python
# Section 1: scenes (existing loop, filtered by show_unchanged)
for name in scene_names:
    sp = result.scenes.get(name)
    if sp is None or (sp.status == "unchanged" and not show_unchanged):
        continue
    ...

# Section 2: warnings (missing refs, unused presets)
if result.missing_refs:
    console.print("\n[bold red]Missing device references:[/bold red]")
    for ref in result.missing_refs:
        console.print(f"  [red]✗[/red] {ref}")

if result.unused_presets:
    console.print("\n[bold yellow]Unused presets:[/bold yellow]")
    for pid in result.unused_presets:
        console.print(f"  [yellow]-[/yellow] {pid}")
```

**Cold-start warning pattern** — detect no `state.json` (mirrors existing `config_exists` check lines 93-95):
```python
state_path = Path(config).resolve() / ".rig" / "state.json"
if not state_path.exists():
    console.print("\n[yellow]⚠ No state file found — this is a cold start.[/yellow]")
```

---

### `src/rig/engine/apply.py` (service, event-driven) — MODIFY

**Analog:** existing `src/rig/engine/apply.py`

**Function signature pattern** (lines 51-61) — make `plan` optional with `None` default and internal fallback:
```python
def apply_plan(
    plan: Plan | None = None,       # NEW: None → compute internally
    state_writer: StateWriter = ...,
    ...
    rig: Rig | None = None,
    config_path: str | None = None,
    ...
) -> ApplyResult:
    if plan is None:
        if rig is None:
            raise ValueError("Either plan or rig must be provided")
        from rig.engine.plan import compute_plan
        plan = compute_plan(rig, root_path=config_path)
```

Keep all existing logic unchanged after that guard — no other modifications needed to `apply_plan`.

---

### `tests/test_graph.py` (test) — NEW

**Analog:** `tests/test_plan.py`

**Imports pattern** (test_plan.py lines 1-16):
```python
import json

from rig.engine.plan import compute_plan
from rig.models.device import (
    ChaseBlissConfig,
    ControllerConfig,
    Device,
    DeviceType,
    ManualConfig,
    MidiConfig,
)
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
```

For `test_graph.py`, replace the plan imports with:
```python
from rig.config.errors import ConfigError
from rig.models.graph import DeviceGraph
from rig.models.rig import Rig
from rig.models.signal_chain import SignalChainPosition
```

**Builder helper pattern** (test_plan.py `_make_rig` pattern) — create a `_make_rig()` function that returns a minimal `Rig` with two devices and a signal chain; reuse the same device/preset construction shortcuts (`hx`, `bro`, `tum` naming for brevity).

**Test class pattern** — group by behavior:
```python
class TestDeviceGraph:
    def test_ordered_devices_signal_chain_order(self): ...
    def test_controller_last(self): ...
    def test_off_chain_devices_after_chain(self): ...

class TestCycleDetection:
    def test_no_cycle_passes(self): ...
    def test_cycle_raises_config_error(self): ...
```

**Assertion style** — direct `assert` statements, no `pytest.raises` unless testing exceptions; for exceptions:
```python
import pytest

with pytest.raises(ConfigError):
    DeviceGraph(rig=cycle_rig).ordered_devices()
```

---

### `tests/test_plan.py` (test) — MODIFY

**Analog:** existing `tests/test_plan.py`

**New test classes to add** — follow existing class grouping pattern:
```python
class TestMissingRefs:
    def test_missing_device_collected_in_plan(self): ...
    def test_valid_refs_produce_empty_list(self): ...

class TestUnusedPresets:
    def test_unused_preset_detected(self): ...
    def test_all_referenced_produces_empty_list(self): ...

class TestBeforeAfterFields:
    def test_device_action_has_before_after(self): ...
```

**Fixture construction pattern** — reuse `_make_rig()` from the existing file and extend with additional devices/presets to exercise new detection logic.

---

## Shared Patterns

### ConfigError (and subclasses) for structural errors
**Source:** `src/rig/config/errors.py` (all 18 lines)
**Apply to:** `src/rig/models/graph.py` (CycleError)
```python
class CycleError(ConfigError):
    """Signal chain contains a cycle."""
```
Raise as: `raise CycleError(f"Cycle detected involving device '{device_id}'")`

### Module-level logger
**Source:** `src/rig/engine/plan/compute.py` line 11
**Apply to:** `src/rig/models/graph.py`, `src/rig/engine/plan/compute.py`
```python
logger = logging.getLogger(__name__)
```

### `from __future__ import annotations`
**Source:** every module in `src/rig/`
**Apply to:** all new and modified files

### Pydantic BaseModel field defaults
**Source:** `src/rig/engine/plan/models.py` lines 8-16
- Use `list[str] = []` (not `Field(default_factory=list)`) for simple list fields
- Use `dict[str, X] = {}` (not `Field(default_factory=dict)`) for simple dict fields
- Use `X | None = None` for optional scalar fields

### Rich console output markup
**Source:** `src/rig/cli/commands/plan.py` lines 55-88
- Status icons: `[cyan]+[/cyan]`, `[yellow]~[/yellow]`, `[green]✓[/green]`, `[red]✗[/red]`
- Section headers: `console.print("\n[bold]Section Title[/bold]")`
- Inline dim text: `[dim]...[/dim]`

### typer.Exit codes
**Source:** `src/rig/cli/commands/plan.py` line 39
- `raise typer.Exit(1)` — error (ConfigError, missing rig)
- `raise typer.Exit(2)` — changes detected (new, for CI integration)
- implicit `Exit(0)` — plan is clean

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Cycle detection logic | utility | transform | No graph/topological algorithms exist in the codebase — implement standard DFS with visited set |

---

## Metadata

**Analog search scope:** `src/rig/models/`, `src/rig/engine/plan/`, `src/rig/cli/commands/`, `src/rig/config/`, `tests/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-06
