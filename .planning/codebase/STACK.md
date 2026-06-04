# Technology Stack

**Analysis Date:** 2026-06-03

## Languages

**Primary:**
- Python 3.12+ — all source code in `src/rig/`

## Runtime

**Environment:**
- CPython 3.12 (minimum required per `pyproject.toml` `requires-python = ">=3.12"`)

**Package Manager:**
- `uv` — used for all dev commands (`uv run pytest`, `uv run ruff`)
- Lockfile: `uv.lock` present

## Frameworks

**CLI:**
- `typer>=0.12` — CLI framework; `app = typer.Typer(name="rig")` in `src/rig/cli.py`
- `rich>=13.0` — terminal output, tables, colored text; `Console` used throughout `src/rig/cli.py`

**Data Modeling:**
- `pydantic>=2.0` — all domain models extend `BaseModel`; used in `src/rig/models/`, `src/rig/engine/appliers/base.py`, `src/rig/engine/plan.py`

**YAML Parsing:**
- `pyyaml>=6.0` — all config file loading via `yaml.safe_load()` in `src/rig/config/loader.py`

**MIDI:**
- `mido>=1.3` — MIDI message construction and port I/O; `src/rig/midi/adapter.py`
- `python-rtmidi>=1.5` — rtmidi backend for mido (hardware MIDI interface)

**Testing:**
- `pytest` (dev dependency) — test runner; config in `pyproject.toml` `[tool.pytest.ini_options]`
- `pytest-cov` (dev dependency) — coverage reporting

**Build:**
- `hatchling` — build backend (`[build-system]` in `pyproject.toml`)

## Key Dependencies

**Critical:**
- `pydantic>=2.0` — domain models (preset, pedal, scene, rig, signal_chain) are Pydantic `BaseModel`s; `model_dump_json()`, `model_copy()` used throughout
- `typer>=0.12` — defines CLI surface; all commands registered via `@app.command()` decorators
- `mido>=1.3` + `python-rtmidi>=1.5` — hardware MIDI output; mido is lazily imported with fallback (`_HAS_MIDO` flag in `src/rig/midi/adapter.py`)

**Infrastructure:**
- `pyyaml>=6.0` — parses all rig config YAML files
- `rich>=13.0` — all terminal output (tables, colored status, progress)

## Configuration

**Build:**
- `pyproject.toml` — single source of truth for dependencies, build, linting, and test config
- Entry point: `rig = "rig.cli:app"` (installs `rig` binary)

**Linting/Formatting:**
- `ruff` — both linter and formatter
- Line length: 100
- Target: `py312`
- Lint rules: `E`, `W`, `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- `E501` (line-too-long) ignored — handled by formatter

**Pre-commit:**
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

**Development:**
- Python 3.12+, uv, rtmidi system library (for MIDI hardware access)

**Production:**
- No hosted service; CLI installed locally, run against a rig config repo directory

---

*Stack analysis: 2026-06-03*
