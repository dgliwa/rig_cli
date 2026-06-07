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
| `rig plan` | Preview changes needed to reach desired state |
| `rig apply` | Apply changes to reach desired state |
| `rig status` | Show current rig state |
| `rig diff` | Show differences between config versions |
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

## Plugin Packages

`rig` discovers device support at runtime via entry points — install only what you need:

```bash
# Analog pedals with knob/switch presets (manual prompts)
uv pip install rig-analog

# Chase Bliss MIDI pedals (auto channel, preset build, scene registration)
uv pip install rig-chasebliss

# Line6 HX Stomp (PC message device control)
uv pip install rig-hx

# Morningstar MC6 MIDI controller (bank/switch SysEx config)
uv pip install rig-morningstar
```

No device plugins = empty registry. `rig validate` still works with no plugins installed.

## Tech Stack

- Python 3.12+, Pydantic v2, Typer, Rich
- MIDI via Mido + python-rtmidi
- Plugin discovery via `importlib.metadata.entry_points('rig.devices')`
- 5 packages: `rig` (core), `rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar`

## Config Loading

`rig validate` reads all YAML configs from the rig repo and validates cross-references:

| File | Purpose |
|------|---------|
| `rig.yaml` | Top-level name, MIDI channel |
| `signal-chain.yaml` | Ordered pedal signal chain |
| `pedals/*.yaml` or `devices/*.yaml` | Device definitions |
| `pedals/<id>/presets/*.yaml` or `devices/<id>/presets/*.yaml` | Presets per device |
| `scenes/*.yaml` | Scene definitions |

The loader checks:
- Every device referenced in the signal chain exists
- Every scene's preset references resolve to existing presets
- Device types match preset types (analog presets for analog devices, etc.)

## Domain Model

```
Device                — A pedal in the rig (analog, digital, modeler, controller)
  ├── ManualConfig    — No MIDI control; user sets knobs manually
  ├── MidiConfig      — Program Change messages sent via MIDI
  └── ChaseBlissConfig — CBA 3-phase setup (channel, preset, scene registration)

Preset                — A named configuration for one device
  ├── AnalogPreset    — Knob/switch positions; human must set manually
  ├── DigitalPreset   — Preset number + optional parameters; PC message
  └── HXStompPreset   — Preset number + path to .hlx file

Scene                 — A complete rig state (one button press)
  └── Maps device IDs → preset IDs
```

Device behavior is dispatched by config type. Each device plugin provides a Pydantic model matching its config type's entry point, implementing `setup()` (MIDI connection, initialization) and `apply()` (preset application, PC send).

## Architecture

```
rig-core (rig)                  — CLI, loader, plan/apply engine, MIDI adapter
  └── rig.devices entry point   — discovers device plugins at runtime

rig-analog                      — Manual device support
  └── AnalogDevice              — setup() is no-op, apply() prompts user

rig-chasebliss                  — Chase Bliss Audio support
  └── ChaseBlissDevice          — setup() manages MIDI + 3-phase init,
                                  apply() sends PC messages

rig-hx                          — Line6 HX Stomp support
  └── HXStompDevice             — setup() manages MIDI,
                                  apply() sends PC messages

rig-morningstar                 — Morningstar MC6 controller support
  └── MC6Device                 — setup() manages MIDI,
                                  apply() sends bank/switch SysEx
```

### Apply Flow

1. **Phase 1: Device Setup** — Each device's `setup()` is called once: opens MIDI port, runs device-specific init (CBA channel discovery, MC6 bank config)
2. **Phase 2: Scene Apply** — For each active scene, apply preset per device in signal-chain order (MC6 last, after all scenes reference it)
3. **Phase 3: State Write** — Save `.rig/state.json` in the config repo

`rig plan` is read-only (no MIDI) — it diffs desired state vs last-known state from `.rig/state.json`.

## Config Repo Layout

```
rig.yaml                        # name, midi_channel
signal-chain.yaml               # ordered device chain
pedals/<id>.yaml                # Device definition
pedals/<id>/presets/<preset>.yaml  # Preset
scenes/<name>.yaml              # Scene
hlx/<name>.hlx                  # raw Line6 preset files (for HXStompPreset)
mc6.yaml                        # MC6 bank/switch → scene mappings
.rig/state.json                 # Last-known applied state (auto-managed)
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

# Install all packages in editable mode
uv pip install -e packages/rig -e packages/rig-analog -e packages/rig-chasebliss -e packages/rig-hx -e packages/rig-morningstar

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
