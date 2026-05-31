# rig-cli

Infrastructure-as-Code CLI for guitar rigs. Declare your pedals, presets, and scenes in YAML — version-control everything.

## Quick Start

```bash
pip install -e .
rig validate
rig plan
rig apply
```

## Commands

| Command | Description |
|---------|-------------|
| `rig validate` | Validate the rig configuration |
| `rig plan` | Preview changes needed to reach desired state |
| `rig apply` | Apply changes to reach desired state |
| `rig status` | Show current rig state |
| `rig diff` | Show differences between config versions |

## Tech Stack

- Python 3.12, Pydantic v2, Typer, Rich
- MIDI via Mido + python-rtmidi

## Development

```bash
pip install -e ".[dev]"
pytest
```
