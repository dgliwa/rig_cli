# Phase 26: Isolated Preset Apply - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 3 (apply.py engine function, apply.py CLI command, test_apply.py)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/rig/src/rig/engine/apply.py` (new fn) | service | request-response | `apply_plan()` in same file | exact |
| `packages/rig/src/rig/cli/commands/apply.py` (new options) | controller | request-response | `--scene` / `--dry-run` options in same file | exact |
| `packages/rig/tests/test_apply.py` (new tests) | test | CRUD | existing test classes in same file | exact |

---

## Pattern Assignments

### `apply_device_preset()` in `packages/rig/src/rig/engine/apply.py`

**Analog:** `apply_plan()` in the same file (lines 35–189)

**Imports pattern** — reuse all existing imports; no new ones needed (lines 1–17):
```python
from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel
from rich.console import Console

from rig.engine.plan import Plan
from rig.engine.plugin import DeviceApplyContext, DeviceApplyResult, SetupContext
from rig.engine.ports import ConfirmationIO, RichConfirmationIO, StateWriter
from rig.engine.state import RigState
from rig.midi.adapter import MidiManager
from rig.models.rig import Rig

logger = logging.getLogger(__name__)
console = Console()
```

**Keyword-only signature pattern** — copy this style exactly; all parameters after `*` are keyword-only (lines 35–45):
```python
def apply_plan(
    plan: Plan | None = None,
    *,
    state_writer: StateWriter,
    confirmation_io: ConfirmationIO | None = None,
    rig: Rig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
) -> ApplyResult:
```

**New function signature** — same style, narrower scope (device + preset instead of scene):
```python
def apply_device_preset(
    *,
    rig: Rig,
    device_id: str,
    preset_id: str,
    state_writer: StateWriter,
    confirmation_io: ConfirmationIO | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    midi: MidiManager | None = None,
) -> ApplyResult:
```

**Guard/validation pattern before doing any work** (lines 46–55):
```python
if plan is None:
    if rig is None:
        raise ValueError("apply_plan requires either a pre-computed plan or a rig instance")
    ...
if plan.status == "clean":
    logger.info("No changes needed — state matches config")
    console.print("[green]✓[/green] No changes needed. State matches config.")
    return ApplyResult(status="no_changes")
```
For `apply_device_preset()`, validate that `device_id` exists in `rig.devices` and that `preset_id` exists on that device — raise `ValueError` (not a domain error) for programmer mistakes, consistent with `apply_plan`'s own guard.

**State read pattern** (lines 57–63):
```python
state = RigState()
if config_path:
    state = state_writer.read(config_path)

connected_devices: set[str] = set()
_io = confirmation_io or RichConfirmationIO()
```

**Device setup phase pattern** (lines 71–87):
```python
setup_ctx = SetupContext(
    state=state,
    rig=rig,
    dry_run=dry_run,
    confirmation_io=_io,
    midi=midi,
    config_path=config_path,
    connected_devices=connected_devices,
)
for _device_id, device in rig.devices.items():
    result = device.setup(setup_ctx)
    if result.cancelled:
        console.print("[red]Apply cancelled by user[/red]")
        return ApplyResult(status="cancelled", scenes=scene_results)
```
`apply_device_preset()` only needs to call `device.setup()` for the one target device (or can skip setup entirely since there is no scene context — planner decides).

**DeviceApplyContext construction pattern** (lines 119–129):
```python
device_ctx = DeviceApplyContext(
    action=action,
    state=state,
    rig=rig,
    dry_run=dry_run,
    confirmation_io=_io,
    midi=midi,
    connected_devices=connected_devices,
    config_path=config_path,
)
action_result = device.apply(device_ctx)
```

**State save pattern** (lines 184–188):
```python
if config_path and not dry_run and state_modified:
    logger.info("Saving state to .rig/state.json")
    state_writer.write(config_path, state)
    console.print("[green]✓[/green] State saved to .rig/state.json")
```

**What differs from `apply_plan`:** No `Plan` object is built. No scene loop. No controller programming phase. The function builds a single `DeviceAction` directly from `device_id` + `preset_id`, calls `device.setup()` then `device.apply()` once, and returns an `ApplyResult`. The `scenes` list in `ApplyResult` will contain a single synthetic `SceneApplyResult` (or the return type can be just `DeviceApplyResult` — planner decides, but `ApplyResult` reuse avoids a new type).

---

### `--device` and `--preset` options in `packages/rig/src/rig/cli/commands/apply.py`

**Analog:** `--scene` and `--dry-run` options in the same file (lines 20–26)

**Existing Option pattern to copy** (lines 20–26):
```python
@app.command()
def apply(
    config: str = _CONFIG_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    scene: str | None = _SCENE_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
```

**New options follow the same inline `typer.Option()` style:**
```python
device: str | None = typer.Option(None, "--device", "-d", help="Apply a single device preset by device ID"),
preset: str | None = typer.Option(None, "--preset", "-p", help="Preset ID to apply (requires --device)"),
```

**ConfigError guard pattern — copy exactly** (lines 31–34):
```python
try:
    rig = load_rig(config)
except ConfigError as e:
    console.print(f"[red]✗[/red] {e}")
    raise typer.Exit(1)
```

**Mutual-dependency validation pattern** — add after `load_rig` succeeds, before engine calls, following the same guard style:
```python
if (device is None) != (preset is None):
    console.print("[red]✗[/red] --device and --preset must be used together")
    raise typer.Exit(1)
```

**Call routing pattern** — existing call to `apply_plan` stays; add branch:
```python
if device and preset:
    from rig.engine.apply import apply_device_preset
    apply_device_preset(
        rig=rig,
        device_id=device,
        preset_id=preset,
        state_writer=state_writer,
        config_path=config_path,
        dry_run=dry_run,
        midi=midi,
    )
else:
    result = compute_plan(rig, root_path=config_path)
    apply_plan(result, ...)
```

**`finally: midi.disconnect_all()` pattern — preserve** (lines 50–51):
```python
finally:
    midi.disconnect_all()
```

**What differs from existing options:** `--scene` is defined as a shared constant in `_shared.py` (`_SCENE_OPTION`). `--device` and `--preset` are new and not shared across commands, so define them inline with `typer.Option()` directly in the function signature.

---

### New test class/functions in `packages/rig/tests/test_apply.py`

**Analog:** Existing test classes in the same file (uses `FakeDevice`, `InMemoryStateAdapter`, `InMemoryPromptAdapter`)

**Import pattern** — all needed imports already present in the file (lines 1–26):
```python
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rig.engine.apply import ApplyResult, apply_plan
from rig.engine.plan import compute_plan
from rig.engine.plugin import DeviceType
from rig.models.rig import Rig
from tests.conftest import FakeDevice
from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter
```
Add `apply_device_preset` to the `from rig.engine.apply import ...` line.

**`FakeDevice` construction pattern** (`conftest.py` lines 15–40):
```python
ctrl = FakeDevice(
    id="mc6",
    type=DeviceType.CONTROLLER,
)
```
`FakeDevice` is a `@dataclass` with `id`, `type`, optional `config`, `presets`, `name`. Its `apply()` always returns `DeviceApplyResult(device=self.id, status="skipped", preset="")`. For isolated preset apply tests, a custom fake that returns `"confirmed"` may be needed — subclass or replace `apply` via `MagicMock`.

**`InMemoryStateAdapter` usage pattern** (from `fakes.py` lines 60–75):
```python
state_adapter = InMemoryStateAdapter()
# ... call apply_device_preset(..., state_writer=state_adapter)
state = state_adapter.state
assert state.devices["hx-stomp"].last_preset == "clean-edge"
```

**`InMemoryPromptAdapter` usage pattern** (from `fakes.py` lines 17–57):
```python
prompt_io = InMemoryPromptAdapter(default="confirm")
# or with side_effect for multi-step:
prompt_io = InMemoryPromptAdapter(default="confirm", side_effect=["skip"])
```
Valid values: `"confirm"`, `"retry"`, `"skip"`, `"quit"` — enforced by assertion in `__init__`.

**Minimal Rig construction pattern** (from test file around line 29–55):
```python
hx = HXStompDevice(
    id="hx-stomp",
    type=DeviceType.MODELER,
    config={"type": "midi", "midi_channel": 1},
    presets=[HXStompPreset(id="clean-edge", ...)],
)
rig = Rig(
    name="test",
    signal_chain=["hx-stomp"],
    devices={"hx-stomp": hx},
)
```

**What differs in new tests:** Tests call `apply_device_preset()` not `apply_plan()`. No scene loop to exercise. Key cases to cover:
- `device_id` not in `rig.devices` → `ValueError`
- `preset_id` not on device → `ValueError`
- happy path: `DeviceApplyResult.status == "confirmed"` → state written
- `dry_run=True` → state not written
- confirmation `"skip"` → state not written

---

## Shared Patterns

### Error guard before engine work
**Source:** `packages/rig/src/rig/cli/commands/apply.py` lines 31–34
**Apply to:** CLI `apply` command additions
```python
try:
    rig = load_rig(config)
except ConfigError as e:
    console.print(f"[red]✗[/red] {e}")
    raise typer.Exit(1)
```

### Keyword-only function signature
**Source:** `packages/rig/src/rig/engine/apply.py` lines 35–45
**Apply to:** `apply_device_preset()` signature
All parameters after the bare `*` are keyword-only. Required parameters (`state_writer`, `rig`, `device_id`, `preset_id`) have no defaults. Optional parameters (`confirmation_io`, `config_path`, `dry_run`, `midi`) default to `None` or `False`.

### State read → modify → write lifecycle
**Source:** `packages/rig/src/rig/engine/apply.py` lines 57–60 and 184–188
**Apply to:** `apply_device_preset()` body
```python
state = RigState()
if config_path:
    state = state_writer.read(config_path)
# ... mutations ...
if config_path and not dry_run and state_modified:
    state_writer.write(config_path, state)
```

### `from __future__ import annotations` + `logging.getLogger(__name__)`
**Source:** Every source file in `src/rig/`
**Apply to:** All new/modified source files
```python
from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
```

### `finally: midi.disconnect_all()`
**Source:** `packages/rig/src/rig/cli/commands/apply.py` lines 50–51
**Apply to:** CLI apply command — any new branch that uses `MidiManager` must be inside the existing `finally` block

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `packages/rig/src/rig/engine/`, `packages/rig/src/rig/cli/`, `packages/rig/tests/`
**Files scanned:** 5 (`apply.py` engine, `apply.py` CLI, `_shared.py`, `test_apply.py`, `fakes.py`, `conftest.py`)
**Pattern extraction date:** 2026-06-17
