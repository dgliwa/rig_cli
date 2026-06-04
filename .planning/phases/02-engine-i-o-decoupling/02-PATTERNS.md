# Phase 2: Engine I/O Decoupling — Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 7 (2 new, 5 modified)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/rig/engine/ports.py` | protocol + adapter | request-response | `src/rig/engine/appliers/base.py` | exact (Protocol + adapter pairing) |
| `tests/fakes.py` | test utility | request-response | `tests/test_appliers.py` (`_make_ctx`) | role-match |
| `src/rig/engine/appliers/base.py` | context dataclass | request-response | itself (extension) | exact |
| `src/rig/engine/apply.py` | orchestrator | request-response | itself (extension) | exact |
| `src/rig/engine/appliers/analog.py` | applier | request-response | itself (extension) | exact |
| `src/rig/engine/appliers/midi_device.py` | applier | request-response | `analog.py` (same pattern) | exact |
| `src/rig/engine/appliers/chase_bliss.py` | applier | request-response | `analog.py` (same pattern) | exact |

---

## Pattern Assignments

### `src/rig/engine/ports.py` (protocol + adapter, NEW)

**Analog:** `src/rig/engine/appliers/base.py`

**Pattern to follow:** Define narrow `Protocol` classes for each I/O boundary, then provide a production adapter that wraps the existing implementation. Match the file's existing style exactly: `Protocol` with `...` body, `from __future__ import annotations`, no ABC inheritance.

**Protocol definition pattern** (`src/rig/engine/appliers/base.py` lines 35-36):
```python
class DeviceApplier(Protocol):
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext) -> DeviceApplyResult: ...
```

**Imports pattern** (`src/rig/engine/appliers/base.py` lines 1-13):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel
```

**What to define in `ports.py`:**

1. `ConfirmationIO` — Protocol with three methods matching the signatures of the existing interaction functions:
   - `prompt_analog(device, preset_name) -> _ConfirmResult`
   - `prompt_device(device, preset_name, preset_number, midi_channel, midi_connected) -> _ConfirmResult`
   - `prompt_cba_channel(device, midi_channel, midi_sent) -> _ConfirmResult`
   - `prompt_cba_presets(device) -> _ConfirmResult`
   - `prompt_cba_register(device, scene_refs) -> _ConfirmResult`

2. `StateWriter` — Protocol with one method: `write(root: str, state: RigState) -> None`

3. `MidiConnectionIO` — Protocol with one method matching `prompt_midi_connect`'s signature: `prompt_connect(device, midi_channel, midi, device_port) -> tuple[_ConfirmResult, str | None]`

4. Production adapters: thin classes (`RichConfirmationIO`, `FileStateWriter`, `RichMidiConnectionIO`) that delegate to the existing `interaction.*` functions and `write_state`.

**Gotcha — `_ConfirmResult` type:** It is defined independently in each `interaction/*.py` file as `Literal["confirm", "retry", "skip", "quit"]`. Define it once in `ports.py` and import from there in the interaction modules (or duplicate in ports.py to avoid reverse dependency).

---

### `tests/fakes.py` (test utility, NEW)

**Analog:** `tests/test_appliers.py` — the `_make_ctx` helper and `patch("builtins.input", ...)` pattern it replaces.

**Pattern to copy** (`tests/test_appliers.py` lines 15-22):
```python
def _make_ctx(dry_run: bool = False, connected: set[str] | None = None) -> ApplyContext:
    midi = MagicMock()
    return ApplyContext(
        dry_run=dry_run,
        midi=midi,
        connected_devices=connected or set(),
        state=RigState(),
    )
```

**What to define in `tests/fakes.py`:**

- `FakeConfirmationIO` — stores a queue of canned responses; `prompt_analog`, `prompt_device`, etc. pop from the queue. Also records calls made so tests can assert on them.
- `FakeStateWriter` — in-memory; stores `(root, state)` calls in a list for assertion.
- `FakeMidiConnectionIO` — stores a canned `(result, port_name)` return value; records calls.

**Style:** Plain classes, no `@dataclass` needed. Match project convention of short builder helpers (`_make_ctx`-style). No imports from `unittest.mock` in the fakes themselves — they are real implementations of the protocols.

**Gotcha:** `FakeConfirmationIO` needs to handle all prompt method signatures without crashing when a method is not exercised by a test. Use a `deque` of responses with a fallback default (e.g., `"skip"`) so tests only configure what they care about.

---

### `src/rig/engine/appliers/base.py` — add `confirmation_io` field

**Pattern:** `ApplyContext` is a `@dataclass`, NOT a Pydantic model. New fields follow the existing field pattern — typed, with `field(default_factory=...)` for mutable defaults or a plain default for optional scalar fields.

**Existing fields to match** (lines 26-32):
```python
@dataclass
class ApplyContext:
    dry_run: bool
    midi: MidiManager | None = None
    connected_devices: set[str] = field(default_factory=set)
    state: RigState = field(default_factory=RigState)
    config_path: str | None = None
    rig: Rig | None = None
```

**New field to add:**
```python
confirmation_io: ConfirmationIO | None = None
```

**Gotcha — import cycle:** `ConfirmationIO` will live in `src/rig/engine/ports.py`. Since `base.py` already imports from `rig.engine.state` and `rig.midi.adapter`, importing from `rig.engine.ports` is safe (no cycle). However, if `ports.py` imports from `base.py` (e.g., to reference `RigState`), that would be a cycle — `ports.py` should import `RigState` directly from `rig.engine.state`, not via `base.py`.

**Gotcha — `TYPE_CHECKING` guard:** `base.py` already uses this guard for `DeviceAction` and `Rig` (lines 11-13). If `ConfirmationIO` is only needed at type-check time in a particular file, use the same guard. But since it is a runtime field on `ApplyContext`, it needs a real import (not guarded).

---

### `src/rig/engine/apply.py` — add `state_writer` and `midi_connection_io` params

**Pattern:** `apply_plan` signature currently takes explicit keyword args with `| None = None` defaults (lines 47-54). Follow this same pattern for the two new params.

**Existing signature to extend** (`apply.py` lines 47-54):
```python
def apply_plan(
    plan: Plan,
    rig: Rig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
) -> ApplyResult:
```

**Inline call being replaced** (`apply.py` line 106):
```python
res, port_name = prompt_midi_connect(device_id, ch, midi, cached_port)
```
Replace with: `res, port_name = midi_connection_io.prompt_connect(device_id, ch, midi, cached_port)` — guard with `if midi_connection_io` and fall back to existing behavior when `None`.

**State write being replaced** (`apply.py` line 193):
```python
write_state(config_path, state)
```
Replace with: `state_writer.write(config_path, state)` — guard with `if state_writer else write_state(config_path, state)`.

**Scene-write bug fix (line 171):** `state.scenes[sp.scene_name] = {}` writes an empty dict unconditionally even for cancelled-mid-scene runs. The fix (write only on `not cancelled`) is a logic change, not a pattern question — but the state mutation pattern is the same as the existing `update_device_state` helpers.

**Gotcha:** `apply_plan` constructs `ApplyContext` at line 65. After adding `confirmation_io` to `ApplyContext`, the construction call in `apply.py` must also pass `confirmation_io=confirmation_io` (the new param).

---

### `src/rig/engine/appliers/analog.py` — call through `ctx.confirmation_io`

**Current pattern** (line 30):
```python
res = prompt_analog(action.device, action.preset_name)
```

**New pattern:**
```python
io = ctx.confirmation_io
res = io.prompt_analog(action.device, action.preset_name) if io else prompt_analog(action.device, action.preset_name)
```

Or, if the planner decides `confirmation_io` is always required (not optional), simply:
```python
res = ctx.confirmation_io.prompt_analog(action.device, action.preset_name)
```

**Import to remove:** `from rig.interaction.analog import prompt_analog` — once the call is routed through `ctx.confirmation_io`, this import is no longer needed in the applier. The production adapter in `ports.py` imports it instead.

**Existing import block to match** (`analog.py` lines 1-11):
```python
from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import ApplyContext, DeviceApplyResult, update_device_state
from rig.engine.plan import DeviceAction
from rig.interaction.analog import prompt_analog
```

Same refactor applies to `midi_device.py` (remove `from rig.interaction.midi import prompt_device`) and `chase_bliss.py` (remove `from rig.interaction.cba import prompt_cba_*`).

---

### `tests/test_appliers.py` and `tests/test_apply.py` — replace `patch("builtins.input")`

**Current pattern** (`test_appliers.py` lines 64-65):
```python
with patch("builtins.input", return_value="c"):
    result = self.applier.apply_scene(action, ctx)
```

**New pattern:**
```python
fake_io = FakeConfirmationIO(responses=["c"])
ctx = _make_ctx(confirmation_io=fake_io)
result = self.applier.apply_scene(action, ctx)
assert fake_io.calls == [("prompt_analog", "fuzz", "Noon")]
```

**`_make_ctx` update needed** (`test_appliers.py` lines 15-22): Add `confirmation_io` parameter, defaulting to a `FakeConfirmationIO` with a "skip" default so existing tests that don't care about the prompt still pass without `patch`.

---

## Shared Patterns

### Protocol definition
**Source:** `src/rig/engine/appliers/base.py` lines 35-36
**Apply to:** `src/rig/engine/ports.py` — all three Protocol classes use `...` body, no `pass`, no ABC.

### `@dataclass` for context objects (NOT Pydantic)
**Source:** `src/rig/engine/appliers/base.py` lines 25-32
**Apply to:** Any new context or result holder that is not serialized to/from JSON — use `@dataclass`. Only use `BaseModel` for things loaded from YAML or persisted to `state.json`.

### `from __future__ import annotations`
**Source:** Every file in `src/rig/` uses this.
**Apply to:** `src/rig/engine/ports.py` and `tests/fakes.py` — add as first line.

### `TYPE_CHECKING` guard for forward-reference imports
**Source:** `src/rig/engine/appliers/base.py` lines 11-13:
```python
if TYPE_CHECKING:
    from rig.engine.plan import DeviceAction
    from rig.models.rig import Rig
```
**Apply to:** `ports.py` — if `RigState` or `MidiManager` are only referenced in type signatures (not runtime), guard them. Given they are used at runtime in the adapters, they need real imports.

### `| None = None` optional params
**Source:** `src/rig/engine/apply.py` lines 48-54; `src/rig/engine/appliers/base.py` lines 28-32
**Apply to:** New params on `apply_plan` and new `confirmation_io` field on `ApplyContext`.

### `logger = logging.getLogger(__name__)`
**Source:** Every module in `src/rig/engine/` and `src/rig/interaction/`
**Apply to:** `src/rig/engine/ports.py` — add logger even if not used immediately.

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `src/rig/engine/`, `src/rig/interaction/`, `tests/`
**Files read:** 8
**Pattern extraction date:** 2026-06-04
