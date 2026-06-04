# Technology Stack

**Project:** rig-cli — I/O decoupling & plan command milestone
**Researched:** 2026-06-04
**Confidence:** HIGH (patterns verified against Python official docs and existing codebase)

---

## Context: What This Milestone Changes

The existing stack (Python 3.13, uv, Typer, Pydantic, Mido + rtmidi, ruff) does not change.
This milestone introduces two structural patterns on top of that stack:

1. **Protocol-based ports** — decouple `apply.py` from direct `input()`, `console.print()`, and `write_state()` calls
2. **Typed plan output** — a `plan` command that diffs desired vs persisted state and emits a structured action list

---

## Pattern 1: Protocol-Based I/O Ports

### The Problem in the Current Codebase

`apply.py::apply_plan` is untestable without hardware because it:
- Calls `prompt_midi_connect` (which calls `input()` directly)
- Calls `write_state()` (filesystem write)
- Constructs `Console()` at module level and prints inline
- Passes `MidiManager` concretely (requires rtmidi hardware)

The appliers (`AnalogApplier`, `MidiApplier`, `ChaseBlissApplier`) import from `rig.interaction`
(which calls `input()`) and use `Console()` at module scope.

### The Fix: Three Output Ports

Define three Protocol interfaces that capture exactly the three I/O concerns:

```python
# src/rig/engine/ports.py

from typing import Protocol, Literal
from rig.engine.plan import DeviceAction, CbaSetupAction

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


class PromptPort(Protocol):
    """Driven port: interactive confirmation of device steps."""

    def prompt_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool = False,
    ) -> _ConfirmResult: ...

    def prompt_analog(self, device: str, preset_name: str) -> _ConfirmResult: ...

    def prompt_midi_connect(
        self, device: str, midi_channel: int, available_ports: list[str], cached_port: str | None
    ) -> tuple[_ConfirmResult, str | None]: ...

    def prompt_cba_channel(
        self, device: str, midi_channel: int, midi_sent: bool = False
    ) -> _ConfirmResult: ...

    def prompt_cba_build_preset(
        self, device: str, preset_name: str, preset_number: int | None, midi_channel: int
    ) -> _ConfirmResult: ...

    def prompt_cba_register(self, device: str, scene_refs: list[str]) -> _ConfirmResult: ...


class StatePort(Protocol):
    """Driven port: read and write persisted rig state."""

    def read(self) -> RigState: ...
    def write(self, state: RigState) -> None: ...


class MidiPort(Protocol):
    """Driven port: hardware MIDI output."""

    def send_pc(self, channel: int, program: int, port_alias: str) -> None: ...
    def send_cc(self, channel: int, control: int, value: int, port_alias: str) -> None: ...
    def connect(self, port_name: str, alias: str) -> None: ...
    def is_connected(self, alias: str) -> bool: ...
    def list_output_ports(self) -> list[str]: ...
```

**Confidence: HIGH** — This directly matches the structural subtyping pattern confirmed in
Python 3.13 official docs (`typing.Protocol`, PEP 544). No ABC inheritance needed; any class
with the matching method signatures satisfies the Protocol.

### Concrete Adapters (Production)

The existing `interaction.py` functions become methods on a `RichPromptAdapter`:

```python
# src/rig/engine/adapters/rich_prompt.py

class RichPromptAdapter:
    """Production adapter: wraps existing interaction.py functions."""

    def prompt_analog(self, device: str, preset_name: str) -> _ConfirmResult:
        return prompt_analog(device, preset_name)  # existing interaction.py call

    # ... delegates to all existing prompt_* functions
```

The existing `MidiManager` already satisfies `MidiPort` structurally — verify the method
signatures match, add any missing pass-throughs, no inheritance needed.

The existing `read_state` / `write_state` functions become a `FileStateAdapter`:

```python
# src/rig/engine/adapters/file_state.py

class FileStateAdapter:
    def __init__(self, config_path: str) -> None:
        self._path = config_path

    def read(self) -> RigState:
        return read_state(self._path)

    def write(self, state: RigState) -> None:
        write_state(self._path, state)
```

### Test Doubles (In-Memory Adapters)

```python
# tests/fakes.py

class InMemoryPromptAdapter:
    """Scripted responses for testing — no input() calls."""

    def __init__(self, responses: dict[str, _ConfirmResult] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple] = []

    def prompt_analog(self, device: str, preset_name: str) -> _ConfirmResult:
        self.calls.append(("analog", device, preset_name))
        return self.responses.get(device, "confirm")


class InMemoryStateAdapter:
    """In-memory state store — no filesystem."""

    def __init__(self, initial: RigState | None = None) -> None:
        self.state = initial or RigState()

    def read(self) -> RigState:
        return self.state

    def write(self, state: RigState) -> None:
        self.state = state
```

**Confidence: HIGH** — This pattern is well-established; the test double satisfies `StatePort`
structurally without declaring it. Type checkers (mypy / pyright) verify this at static analysis
time.

### Updated ApplyContext

`ApplyContext` gains the three ports. Keep it as a `@dataclass` (it already is one, and it
holds mutable state like `connected_devices` — Pydantic is overkill here):

```python
@dataclass
class ApplyContext:
    dry_run: bool
    prompt: PromptPort
    state_port: StatePort
    midi: MidiPort | None = None
    connected_devices: set[str] = field(default_factory=set)
    config_path: str | None = None
    rig: Rig | None = None
```

Remove the `state: RigState` field from `ApplyContext` — state is now accessed via `state_port`.
The engine reads state at the start of `apply_plan`, writes at the end. Appliers that
currently call `update_device_state(ctx.state, ...)` should receive the in-flight mutable
`RigState` object directly (pattern: read at start, mutate in place, write at end is fine).

---

## Pattern 2: Plan Command & Output Format

### Recommendation: Keep Plan Types as Pydantic Models

The existing `DeviceAction`, `ScenePlan`, `CbaSetupAction`, and `Plan` in `plan.py` are
already Pydantic `BaseModel`. Keep them as Pydantic for these reasons:

1. **JSON serialization is already used** — `model_dump_json()` is the natural path to the
   `--json` flag on the `plan` command.
2. **These cross the serialization boundary** — `Plan` is persisted/compared, not a pure
   internal value object. Pydantic's schema export and validation are relevant.
3. **Performance is not a concern** — `compute_plan` runs once per CLI invocation, not in
   a tight loop.

Use `@dataclass` only for truly internal, ephemeral computation objects that never leave
the engine (e.g., intermediate diff state). `ApplyContext` remains a dataclass for this reason.

**Confidence: HIGH** — Confirmed against the existing codebase pattern; Pydantic models are
already used consistently for all plan/result types.

### Plan Output Format

Model the plan output after Terraform's `resource_changes` structure:
- Each action has a typed `action` field (not a status string)
- Include `before` and `after` to make the diff human-readable
- Top-level `summary` counts by action type
- Dual output: human-readable text by default, `--json` for machine consumption

**Recommended `plan` JSON schema** (extends existing `Plan` model):

```json
{
  "format_version": "1.0",
  "status": "changes_detected",
  "summary": {
    "configure": 3,
    "verify": 1,
    "analog": 2,
    "no_change": 4,
    "total": 10
  },
  "scenes": {
    "bedroom-practice": {
      "scene_name": "bedroom-practice",
      "status": "changed",
      "device_actions": [
        {
          "device": "hx-stomp",
          "device_type": "modeler",
          "action": "configure",
          "preset_name": "clean-verb",
          "preset_number": 3,
          "midi_channel": 1,
          "before": { "preset": "drive-heavy" },
          "after": { "preset": "clean-verb" }
        },
        {
          "device": "mood-mkii",
          "device_type": "analog",
          "action": "analog",
          "preset_name": "shimmer",
          "before": { "preset": "chorus-light" },
          "after": { "preset": "shimmer" }
        }
      ]
    }
  }
}
```

**Action types** (matches existing `DeviceAction.status` Literal):
- `configure` — MIDI PC/CC must be sent; device state will change
- `verify` — device already at correct preset; confirming only
- `analog` — human must adjust knobs; no MIDI
- `no_change` — device already correct; omitted from output by default

The `before`/`after` fields require reading `state.json` during plan computation (already done
in `compute_plan`). The `before.preset` is `actual.devices[device_id].last_preset`, the
`after.preset` is the desired `preset_id`. Add these to `DeviceAction`.

**Text output** (default, no `--json`):

```
Plan: 2 changes detected

  Scene: bedroom-practice (changed)
    configure  hx-stomp      PC#3  ch1   drive-heavy → clean-verb
    analog     mood-mkii           --    chorus-light → shimmer

Summary: 1 configure, 1 analog, 0 verify
No changes: 4 device/scene pairs
```

**Confidence: MEDIUM** — Terraform's JSON format is well-documented and a proven IaC
pattern. The specific field names (`before`/`after` on `DeviceAction`) are a direct
recommendation, not yet validated against the codebase's downstream consumers.

---

## Alternatives Considered

| Decision | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Port definition style | `Protocol` (structural) | `ABC` with `@abstractmethod` | ABC requires inheritance; Protocol allows existing classes to satisfy ports without modification — e.g., `MidiManager` satisfies `MidiPort` without changing it |
| Plan action types | Pydantic `BaseModel` | `@dataclass` | Plan crosses serialization boundary; `model_dump_json()` is the path to `--json` |
| `ApplyContext` | `@dataclass` | Pydantic | Holds mutable `connected_devices: set`; Pydantic would need validators; dataclass is simpler and correct |
| Plan output | `before`/`after` per action | Simple status string | Makes diff human-readable without needing to look up state.json separately; consistent with IaC tools |
| `StatePort` location | `engine/ports.py` | Inline in `apply.py` | Ports must be importable by appliers and test doubles; centralizing avoids circular imports |

---

## No New Dependencies Required

All patterns are implemented with the existing stack:
- `typing.Protocol` — stdlib, Python 3.8+, confirmed in Python 3.13 docs
- `@dataclass` — stdlib
- `pydantic.BaseModel` — already a dependency
- No new packages needed

---

## Sources

- Python 3.13 `typing.Protocol` official docs: https://docs.python.org/3/library/typing.html
- Terraform JSON plan format (resource_changes schema): https://developer.hashicorp.com/terraform/internals/json-format
- Hexagonal architecture / ports and adapters overview: https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/
- Pydantic vs dataclass guidance: https://hrekov.com/blog/dataclasses-or-pydantic-basemodels
