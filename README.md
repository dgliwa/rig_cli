# rig-cli

Infrastructure-as-Code CLI for guitar rigs. Declare your pedals, presets, and scenes in YAML — version-control everything.

## Quick Start

```bash
# Install globally via uv
make tool-install
rig validate --config ~/dev/rig

# Or run directly without installing
uv run rig validate --config ~/dev/rig
```

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package & project manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Commands

| Command | Description |
|---------|-------------|
| `rig validate` | Validate rig config YAML (cross-references, types) |
| `rig status` | Show loaded rig state (pedals, scenes) |
| `rig ingest hx <file>` | Import HX Stomp .hlx presets to YAML |
| `rig ingest mc6 <file>` | Import MC6 JSON config to scene YAML |
| `rig ingest scene create/add/set` | Create/add/set device presets in scenes |
| `rig generate mc6` | Generate MC6 bank configs from scenes |

### Common Flags

| Flag | Description |
|------|-------------|
| `--config <path>` | Path to rig config repo (default: `.`) |
| `-v` / `-vv` | Increase verbosity (INFO / DEBUG) |
| `--format json` | Machine-readable JSON output for automation |

## Tech Stack

- Python 3.12, Pydantic v2, Typer, Rich
- MIDI via Mido + python-rtmidi

## Config Loading

`rig validate` reads all YAML configs from the rig repo and validates cross-references:

| File | Purpose |
|------|---------|
| `rig.yaml` | Top-level name, MIDI channel |
| `signal-chain.yaml` | Ordered pedal signal chain |
| `pedals/*.yaml` | Pedal definitions |
| `pedals/<id>/presets/*.yaml` | Presets per pedal |
| `scenes/*.yaml` | Scene definitions |

The loader checks:
- Every pedal referenced in the signal chain exists
- Every scene's preset references resolve to existing presets
- Pedal types match preset types (analog presets for analog pedals, etc.)

## Architecture

### Models

```
PedalDefinition       — A pedal in the rig (digital, analog, modeler, controller)
  ├── Control         — A knob, switch, or toggle on the pedal
  │
AnalogPreset          — Knob/switch positions for analog pedals
DigitalPreset          — Preset number + parameters for digital pedals
HXStompPreset          — HX Stomp preset with block-level detail
  ├── HXBlock         — A block in the HX signal chain (amp, cab, delay, etc.)
  │     └── settings  — Flexible KV pairs for any block parameter
  ├── MIDICommand     — PC/CC/SysEx sent on preset load (Command Center)
  └── FootswitchAssignment — Per-preset footswitch mapping

Scene                  — A complete rig state (one button press)
SignalChainPosition    — A pedal's position in the signal chain
RigConfig              — Top-level config (imports all above)
```

## Development

```bash
# Clone + install
cd rig-cli
uv sync

# See all available targets
make help

# Run tests
make test

# Lint / format
make lint
make format

# Build distributable wheel
make build

# Install as global CLI tool (one-time)
make tool-install
```

### Available targets

| Target | Description |
|--------|-------------|
| `make help` | Show available targets (default) |
| `make install` | Install deps + package (editable) via `uv sync` |
| `make test` | Run test suite |
| `make lint` | Ruff check |
| `make format` | Ruff format |
| `make build` | Build wheel + sdist |
| `make tool-install` | Install as global CLI via `uv tool install .` |
| `make lock` | Re-lock dependencies |
| `make clean` | Remove build artifacts |

## Troubleshooting

### MIDI events not passing through the MC6

If CC/PC messages sent to the MC6 are not reaching downstream devices, check **Controller Settings → Cross MIDI Thru** in the Morningstar MC6 editor. This setting must be enabled for the MC6 to forward incoming MIDI messages out to connected devices. Plain "MIDI Thru" is not sufficient — Cross MIDI Thru handles USB→DIN and DIN→DIN routing.
