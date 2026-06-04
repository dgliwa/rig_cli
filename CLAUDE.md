# rig-cli — Claude Context

## What this is

Infrastructure-as-Code CLI for a guitar rig. The user maintains a separate **rig config repo** (YAML files) that describes their pedals, presets, and scenes. This tool validates, plans, applies, and generates configs from that repo.

## Domain glossary

- **Pedal** — any device in the rig (analog, digital, modeler, or controller)
- **Preset** — a named configuration for one pedal
  - `AnalogPreset` — knob/switch positions; no MIDI, human must set manually
  - `DigitalPreset` — preset number + optional parameters; sent via PC message
  - `HXStompPreset` — preset number + path to the `.hlx` file that should be loaded on the device
- **HX Stomp** — Line6 HX Stomp multi-effects modeler (pedal type: `modeler`)
- **`.hlx` file** — Line6 proprietary preset format exported from HX Edit; stored in the rig config repo and referenced by `hlx_file` on `HXStompPreset`
- **Scene** — a complete rig state (one button press activates it); maps pedal IDs → preset IDs
- **MC6** — Morningstar MC6 MIDI controller; scenes are mapped to MC6 bank/switch slots
- **Signal chain** — ordered list of pedals from guitar to amp
- **Plan** — diff between current device state and desired state; drives `apply`

## HXStompPreset is intentionally simple

`HXStompPreset` has `id`, `name`, `preset_number`, and `hlx_file` only. There is **no block-level detail**. The scene trigger sends a PC message using `preset_number`; the actual patch content lives in the `.hlx` file referenced by `hlx_file`. Block parsing and management is a future concern tracked in GitHub — do not re-add blocks or try to manage HX patch internals here.

## Rig config repo layout (the user's data, not this codebase)

```
rig.yaml                          # name, midi_channel
signal-chain.yaml                 # ordered pedal chain
pedals/<id>.yaml                  # PedalDefinition
pedals/<id>/presets/<preset>.yaml # AnalogPreset | DigitalPreset | HXStompPreset
scenes/<name>.yaml                # Scene
hlx/<name>.hlx                    # raw Line6 preset files
mc6.yaml                          # MC6 bank/switch → scene mappings
```

## Running things

```bash
make test          # uv run pytest tests/ -v
make lint          # uv run ruff check src/
make format        # uv run ruff format src/
```

Tests live in `tests/`. Run them with `uv run pytest tests/ -q` for quiet output.

## Commit convention

`type(scope): description` — scope is required. Examples:

- `feat(hx): ...`
- `fix(loader): ...`
- `refactor(engine): ...`
- `test(plan): ...`

## Engineering standards

- **Prefer protocols for abstractions.** Define behavior through `Protocol` classes (structural subtyping) rather than abstract base classes. This keeps implementations decoupled and testable without inheritance.
- **Model the domain first.** Before implementing a new feature, nail down the domain model — what are the entities, what are their relationships, what invariants must hold. Clear models make the implementation obvious and keep the codebase extensible.

## Architecture

```
src/rig/
  models/       — Pydantic models (preset, pedal, scene, rig, signal_chain)
  config/       — YAML loader + cross-reference validation
  ingest/       — Import from external formats (HX .hlx, MC6 JSON, manual)
  engine/       — Plan (diff desired vs actual state), apply, diff, state
  generators/   — Output generators (MC6 bank JSON)
  midi/         — MIDI adapter (Mido + rtmidi)
  cli.py        — Typer CLI entry point
```

The engine reads state from `.rig/state.json` in the rig config repo to track what has already been applied to physical devices.

<!-- GSD:project-start source:PROJECT.md -->

## Project

**rig-cli**

Infrastructure-as-Code CLI for a guitar rig. Reads a YAML config repo describing pedals, presets, and scenes, then validates, plans, diffs, and applies those configurations to physical MIDI devices. Designed for one user (the rig owner) who wants repeatable, git-tracked rig state.

**Core Value:** A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

### Constraints

- **Tech stack**: Python 3.13, uv, Typer, Pydantic, Mido + rtmidi — no changes to core dependencies
- **MIDI**: No MIDI interaction in the `plan` command — plan is read-only against state.json
- **Protocol-first**: New abstractions use `Protocol` classes, not ABC inheritance
- **Side project velocity**: Ship working features; avoid over-engineering for hypothetical future frontends

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12+ — all source code in `src/rig/`

## Runtime

- CPython 3.12 (minimum required per `pyproject.toml` `requires-python = ">=3.12"`)
- `uv` — used for all dev commands (`uv run pytest`, `uv run ruff`)
- Lockfile: `uv.lock` present

## Frameworks

- `typer>=0.12` — CLI framework; `app = typer.Typer(name="rig")` in `src/rig/cli.py`
- `rich>=13.0` — terminal output, tables, colored text; `Console` used throughout `src/rig/cli.py`
- `pydantic>=2.0` — all domain models extend `BaseModel`; used in `src/rig/models/`, `src/rig/engine/appliers/base.py`, `src/rig/engine/plan.py`
- `pyyaml>=6.0` — all config file loading via `yaml.safe_load()` in `src/rig/config/loader.py`
- `mido>=1.3` — MIDI message construction and port I/O; `src/rig/midi/adapter.py`
- `python-rtmidi>=1.5` — rtmidi backend for mido (hardware MIDI interface)
- `pytest` (dev dependency) — test runner; config in `pyproject.toml` `[tool.pytest.ini_options]`
- `pytest-cov` (dev dependency) — coverage reporting
- `hatchling` — build backend (`[build-system]` in `pyproject.toml`)

## Key Dependencies

- `pydantic>=2.0` — domain models (preset, pedal, scene, rig, signal_chain) are Pydantic `BaseModel`s; `model_dump_json()`, `model_copy()` used throughout
- `typer>=0.12` — defines CLI surface; all commands registered via `@app.command()` decorators
- `mido>=1.3` + `python-rtmidi>=1.5` — hardware MIDI output; mido is lazily imported with fallback (`_HAS_MIDO` flag in `src/rig/midi/adapter.py`)
- `pyyaml>=6.0` — parses all rig config YAML files
- `rich>=13.0` — all terminal output (tables, colored status, progress)

## Configuration

- `pyproject.toml` — single source of truth for dependencies, build, linting, and test config
- Entry point: `rig = "rig.cli:app"` (installs `rig` binary)
- `ruff` — both linter and formatter
- Line length: 100
- Target: `py312`
- Lint rules: `E`, `W`, `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- `E501` (line-too-long) ignored — handled by formatter
- `pre-commit>=4.6.0` (dev dependency group)

## Notable Language Features Used

- `from __future__ import annotations` — postponed annotation evaluation in most modules
- `Protocol` classes for structural subtyping — `DeviceApplier` in `src/rig/engine/appliers/base.py`
- `dataclass` — `ApplyContext` in `src/rig/engine/appliers/base.py`
- `Literal` types — `DeviceApplyResult.status: Literal["confirmed", "skipped", "error"]`
- `TYPE_CHECKING` guard — avoids circular imports in appliers and engine
- Union types with `|` syntax (`str | None`) throughout — Python 3.10+ style
- `Path` (pathlib) — all file I/O uses `pathlib.Path`

## Platform Requirements

- Python 3.12+, uv, rtmidi system library (for MIDI hardware access)
- No hosted service; CLI installed locally, run against a rig config repo directory

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- `snake_case.py` for all source files: `signal_chain.py`, `chase_bliss.py`, `mc6_presets.py`
- Test files prefixed with `test_`: `test_models.py`, `test_appliers.py`
- Module directories match domain area: `models/`, `engine/`, `config/`, `generators/`, `midi/`
- `PascalCase` throughout: `AnalogPreset`, `DeviceApplier`, `ChaseBlissApplier`, `ApplyContext`
- Pydantic models named as domain nouns: `Device`, `Scene`, `Rig`, `SignalChainPosition`
- Protocol classes use the `Protocol` suffix or role noun: `DeviceApplier`, `DeviceConfig`
- Enums use `PascalCase` class names, `UPPER_CASE` members: `DeviceType.DIGITAL`, `ControlType.KNOB`
- `snake_case` for all functions and methods
- Private helpers prefixed with underscore: `_make_rig()`, `_read_yaml()`, `_resolve()`
- Test builder helpers named `_make_*` or `_*_action()`: `_make_ctx()`, `_analog_action()`, `_midi_action()`
- `snake_case` throughout
- Short, descriptive names for local scope: `ch`, `bro`, `tum` (test builder abbreviations)
- Enum string values are lowercase with underscores: `"chase_bliss"`, `"fx_loop"`
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

- `src/rig/models/preset.py`: `AnalogPreset`, `DigitalPreset`, `HXStompPreset`
- `src/rig/models/device.py`: `Device`, `Control`, `DeviceConfig`, `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`
- `src/rig/models/scene.py`: `Scene`
- `src/rig/models/rig.py`: `Rig`
- `src/rig/models/signal_chain.py`: `SignalChainPosition`

## Protocol Pattern

## Enums

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

## Dataclasses vs Pydantic

- `@dataclass` used for runtime context objects that are not serialized: `ApplyContext` in `src/rig/engine/appliers/base.py`
- Pydantic `BaseModel` used for domain data that is loaded from YAML or needs validation

## Comments

- Comments used sparingly; only for non-obvious decisions
- `TODO:` markers left for unresolved design questions (e.g., `TODO: If we pass pydantic model`, `TODO: I feel like "controls" should live in the configs?`)
- Docstrings on classes that need disambiguation: `"""Base for device configuration strategies. Discriminated by type."""`
- Test methods are self-documenting via descriptive names; no docstrings

## Line Length

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI | Command parsing, output formatting, orchestration | `src/rig/cli.py` |
| Loader | Read YAML repo, validate cross-refs, build Rig | `src/rig/config/loader.py` |
| Domain Models | Typed representations of rig entities | `src/rig/models/` |
| Plan Engine | Diff desired state vs `.rig/state.json` | `src/rig/engine/plan.py` |
| Apply Engine | Execute plan, orchestrate appliers, write state | `src/rig/engine/apply.py` |
| Diff Engine | Compare config to last-known state | `src/rig/engine/diff.py` |
| State | Read/write `.rig/state.json` | `src/rig/engine/state.py` |
| Applier Registry | Route device config type → correct applier | `src/rig/engine/appliers/registry.py` |
| AnalogApplier | Manual (human) prompt for knob/switch devices | `src/rig/engine/appliers/analog.py` |
| MidiApplier | Send PC message via MIDI | `src/rig/engine/appliers/midi_device.py` |
| ChaseBlissApplier | CBA 3-phase setup: channel, presets, registration | `src/rig/engine/appliers/chase_bliss.py` |
| MC6Applier | Send bank/switch configs to MC6 via SysEx | `src/rig/engine/appliers/mc6.py` |
| MidiManager | Open/share MIDI output ports, send messages | `src/rig/midi/adapter.py` |
| MC6 Generator | Generate MC6 bank JSON files from rig config | `src/rig/generators/mc6_presets.py` |
| CBA Catalog | Per-model CC control maps for Chase Bliss pedals | `src/rig/catalog/chase_bliss.py` |

## Pattern Overview

- CLI loads config → engine computes plan → appliers execute actions per device type
- All domain objects are Pydantic BaseModel; state is serialized to/from JSON
- Device behavior is dispatched via `DeviceApplier` Protocol keyed on `config.type`
- State is external (`.rig/state.json` in the rig config repo, not in this codebase)
- Protocols used for structural subtyping (`DeviceApplier` in `appliers/base.py`)

## Layers

- Purpose: User-facing commands; formats and prints results
- Location: `src/rig/cli.py`
- Contains: Typer commands (`validate`, `plan`, `apply`, `status`, `diff`, `generate mc6`)
- Depends on: config/loader, engine, generators, midi
- Used by: End user via `rig` entrypoint
- Purpose: Parse and validate YAML rig config repo into domain models
- Location: `src/rig/config/`
- Contains: `loader.py` (YAML reads, merging, cross-ref validation), `errors.py` (exception types)
- Depends on: models
- Used by: CLI (all commands call `load_rig`)
- Purpose: Authoritative domain types; no business logic
- Location: `src/rig/models/`
- Contains: `device.py`, `preset.py`, `scene.py`, `rig.py`, `controller.py`, `signal_chain.py`
- Depends on: nothing internal
- Used by: all layers
- Purpose: Plan computation, apply execution, state management
- Location: `src/rig/engine/`
- Contains: `plan.py`, `apply.py`, `diff.py`, `state.py`, `appliers/`
- Depends on: models, midi, config.errors
- Used by: CLI
- Purpose: Produce output artifacts from rig config (not apply to devices)
- Location: `src/rig/generators/`
- Contains: `mc6_presets.py` — writes MC6 bank JSON files
- Depends on: models
- Used by: CLI `generate mc6` command
- Purpose: Hardware abstraction for MIDI output
- Location: `src/rig/midi/`
- Contains: `adapter.py` (MidiManager), `mc6.py` (MC6 SysEx helpers)
- Depends on: mido (optional import), rtmidi
- Used by: engine/appliers

## Data Flow

### Primary: validate / plan / status / diff

### Apply Flow

### Generate MC6

## Key Abstractions

- Structural protocol: any class with `apply_scene(action, ctx) -> DeviceApplyResult`
- Implementations: `AnalogApplier`, `MidiApplier`, `ChaseBlissApplier`, `MC6Applier`
- Registry dispatches by `device.config.type` string: `"manual"`, `"midi"`, `"chase_bliss"`
- Dataclass passed to all appliers: `dry_run`, `midi`, `connected_devices`, `state`, `config_path`, `rig`
- `ManualConfig | MidiConfig | ChaseBlissConfig` discriminated on `type` field
- `get_cc_params(parameters)` method on config — only `MidiConfig`/`ChaseBlissConfig` return CC data
- `Preset = AnalogPreset | DigitalPreset | HXStompPreset`
- Type is implicit: `Device.type` (DeviceType enum) determines which preset subtype is valid

## State Management

- `devices: dict[str, DeviceState]` — per-device last-known state
- `scenes: dict[str, dict]` — scenes applied (value is currently empty dict)
- `last_preset`: last preset ID applied
- `midi_port`: cached MIDI port name for reconnection
- `channel_established`, `presets_saved`, `registration_done`: CBA setup phase flags
- `midi_channel`: channel used for this device

## Domain Model Relationships

```

```

## Architectural Constraints

- **Global state:** `MidiManager` is instantiated per CLI invocation and passed through `ApplyContext`; no module-level singletons except the applier instances in `appliers/registry.py` (`_cba_applier`, `_mc6_applier`)
- **Optional MIDI:** mido/rtmidi are soft dependencies; `MidiManager` degrades gracefully when absent
- **CBA catalog lazy load:** `rig.catalog.chase_bliss.get_controls()` is imported inside `Device._populate_cba_controls` model validator to avoid circular imports
- **Legacy compatibility:** `pedals/` directory name accepted alongside `devices/`; `pedal.py` re-exports from `device.py` for backward compat; `pedals` property on `Rig` aliases `devices`

## Anti-Patterns

### CBA setup mixed into Plan

### `apply_plan` is monolithic

### Preset type inferred from device type

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
