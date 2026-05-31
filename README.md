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
pip install -e ".[dev]"
pytest
```
