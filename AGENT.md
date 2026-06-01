# rig-cli

Project: https://github.com/dgliwa/rig_cli

## Project Info

- Python 3.12 project. Pydantic v2 for models. Typer for CLI. Rich for output.
- Entry point: `rig` command.
- Source in `src/rig/`, tests in `tests/`.
- Package manager: `uv`. Build system: hatchling.

## Agent Rules

- **Keep README.md in sync.** When adding/changing CLI commands, workflow,
  prerequisites, or any user-facing behavior, update README.md to reflect
  the current state. The README is the single source of truth for users.
- All tests must pass before committing. Run: `make test`
- Lint with ruff before committing: `make lint`
- Conventional commits (feat:, fix:, docs:, test:, refactor:, build:)
- PR per feature branch.

## Local Development

```bash
uv sync
make test
```
