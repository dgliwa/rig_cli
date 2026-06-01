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
