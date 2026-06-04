# Coding Conventions

**Analysis Date:** 2026-06-03

## Naming Patterns

**Files:**
- `snake_case.py` for all source files: `signal_chain.py`, `chase_bliss.py`, `mc6_presets.py`
- Test files prefixed with `test_`: `test_models.py`, `test_appliers.py`
- Module directories match domain area: `models/`, `engine/`, `config/`, `generators/`, `midi/`

**Classes:**
- `PascalCase` throughout: `AnalogPreset`, `DeviceApplier`, `ChaseBlissApplier`, `ApplyContext`
- Pydantic models named as domain nouns: `Device`, `Scene`, `Rig`, `SignalChainPosition`
- Protocol classes use the `Protocol` suffix or role noun: `DeviceApplier`, `DeviceConfig`
- Enums use `PascalCase` class names, `UPPER_CASE` members: `DeviceType.DIGITAL`, `ControlType.KNOB`

**Functions:**
- `snake_case` for all functions and methods
- Private helpers prefixed with underscore: `_make_rig()`, `_read_yaml()`, `_resolve()`
- Test builder helpers named `_make_*` or `_*_action()`: `_make_ctx()`, `_analog_action()`, `_midi_action()`

**Variables:**
- `snake_case` throughout
- Short, descriptive names for local scope: `ch`, `bro`, `tum` (test builder abbreviations)
- Enum string values are lowercase with underscores: `"chase_bliss"`, `"fx_loop"`

**Constants:**
- `UPPER_CASE` for module-level constants: `MOOD_MKII_CONTROLS`, `FIXTURE_PATH`

## Type Annotations

- All function signatures are annotated with return types
- `from __future__ import annotations` used in files with forward references (`base.py`, `device.py`)
- `TYPE_CHECKING` guard for import-time circular dependency avoidance (`base.py`, `device.py`)
- Union types written with `|` syntax (Python 3.10+ style): `str | None`, `float | str | bool`
- `Literal` used for discriminator fields on Pydantic configs: `type: Literal["midi"] = "midi"`
- `Annotated` + `Field(discriminator=...)` for Pydantic discriminated unions: `config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]`
- `list[str]`, `dict[str, float]` (lowercase generics, not `List`/`Dict`)

## Pydantic Model Patterns

**BaseModel inheritance** for all domain entities:
- `src/rig/models/preset.py`: `AnalogPreset`, `DigitalPreset`, `HXStompPreset`
- `src/rig/models/device.py`: `Device`, `Control`, `DeviceConfig`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`
- `src/rig/models/scene.py`: `Scene`
- `src/rig/models/rig.py`: `Rig`
- `src/rig/models/signal_chain.py`: `SignalChainPosition`

**Discriminated unions for config polymorphism:**
```python
class DeviceConfig(BaseModel):
    type: str

class ManualConfig(DeviceConfig):
    type: Literal["manual"] = "manual"

class MidiConfig(DeviceConfig):
    type: Literal["midi"] = "midi"
```
The `Device.config` field uses `Field(discriminator="type")` to select the right subclass from YAML.

**`model_validator(mode="after")`** for cross-field post-construction logic (e.g., auto-populating CBA controls in `Device._populate_cba_controls`).

**`model_copy(update=...)`** for immutable state updates in `src/rig/engine/appliers/base.py`.

**Optional fields default to `None` or empty collections:**
```python
tags: list[str] = []
parameters: dict[str, float | str | bool] = {}
notes: str | None = None
```

## Protocol Pattern

`Protocol` used (not ABC) for applier contracts in `src/rig/engine/appliers/base.py`:
```python
class DeviceApplier(Protocol):
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext) -> DeviceApplyResult: ...
```
Concrete implementations (`AnalogApplier`, `MidiApplier`, `ChaseBlissApplier`) do not inherit from `DeviceApplier`; they satisfy it structurally.

## Enums

`StrEnum` (Python 3.11+) is used so enum values compare equal to their string representations:
```python
class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"
```

## Error Handling

- Domain-specific exceptions defined in `src/rig/config/errors.py`: `FileNotFoundError_`, `MissingReferenceError`, `ParseError`, `ValidationError`
- `FileNotFoundError_` has a trailing underscore to avoid shadowing the built-in
- Errors raised with descriptive messages including the offending path or ref
- `yaml.YAMLError` caught and re-raised as `ParseError` in `_read_yaml()`
- Pydantic `ValidationError` propagates naturally for model construction failures

## Logging

- `logging.getLogger(__name__)` used in each module: `src/rig/engine/appliers/analog.py`, `src/rig/config/loader.py`
- `logger.debug(...)` for trace-level information (file reads, path resolution)
- `logger.error(...)` for failures before raising
- `rich.console.Console` used for user-facing output (not logging): `console.print(...)` with Rich markup

## Import Organization

Order (enforced by ruff with `isort`):
1. `from __future__ import annotations` (if needed)
2. Standard library
3. Third-party (`pydantic`, `yaml`, `rich`, `typer`)
4. Internal (`rig.*`)

`TYPE_CHECKING` imports placed after regular imports, inside `if TYPE_CHECKING:` block.

## Dataclasses vs Pydantic

- `@dataclass` used for runtime context objects that are not serialized: `ApplyContext` in `src/rig/engine/appliers/base.py`
- Pydantic `BaseModel` used for domain data that is loaded from YAML or needs validation

## Comments

- Comments used sparingly; only for non-obvious decisions
- `TODO:` markers left for unresolved design questions (e.g., `TODO: If we pass pydantic model`, `TODO: I feel like "controls" should live in the configs?`)
- Docstrings on classes that need disambiguation: `"""Base for device configuration strategies. Discriminated by type."""`
- Test methods are self-documenting via descriptive names; no docstrings

## Line Length

100 characters (configured in `pyproject.toml` under `[tool.ruff]`).

---

*Convention analysis: 2026-06-03*
