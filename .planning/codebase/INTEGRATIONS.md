# External Integrations

**Analysis Date:** 2026-06-03

## Hardware Devices

**Morningstar MC6 MkII (MIDI Controller):**
- Communication: MIDI SysEx over USB MIDI
- Protocol: Morningstar SysEx spec (https://helpdesk.morningstar.io/support/solutions/articles/43000681034)
- Device ID: `0x03` (MC6 MkII) — `src/rig/midi/mc6.py`
- Operations: set preset name (01h), write Program Change to message slot (04h), clear preset messages, bank navigation
- Checksum: XOR of all bytes masked to 7-bit — `_checksum()` in `src/rig/midi/mc6.py`

**Line6 HX Stomp (Multi-effects Modeler):**
- Communication: MIDI Program Change over USB MIDI
- Preset activation: PC message with `preset_number` and `midi_channel`
- Patch files: `.hlx` format (Line6 proprietary JSON-based), stored in rig config repo under `hlx/`
- `HXStompPreset` model: `src/rig/models/preset.py` — holds `preset_number` and `hlx_file` path only

**Chase Bliss Audio Pedals:**
- Communication: MIDI CC (Control Change) messages
- Config: `ChaseBlissConfig` in `src/rig/models/device.py`; controls catalog in `src/rig/catalog/chase_bliss.py`
- Applier: `src/rig/engine/appliers/chase_bliss.py`
- Setup operations: establish MIDI channel, build preset, register scenes

**Generic Digital Pedals:**
- Communication: MIDI Program Change
- Applier: `src/rig/engine/appliers/midi_device.py`

**Analog Pedals:**
- No MIDI; apply generates human-readable instructions for manual knob/switch setting
- Applier: `src/rig/engine/appliers/analog.py`

## MIDI Layer

**Library:** `mido` + `python-rtmidi` backend
**Manager:** `MidiManager` in `src/rig/midi/adapter.py`
- Port discovery: `mido.get_output_names()`
- Port sharing: multiple device IDs can share a physical port; opened once per port name
- Message types sent: `program_change`, `control_change`, `sysex`
- Lazy import: mido is imported at runtime with `_HAS_MIDO` guard; gracefully degrades when MIDI hardware absent

## File Formats

**Read (inputs from rig config repo):**
- `rig.yaml` — rig name, global MIDI channel
- `signal-chain.yaml` — ordered device chain
- `devices/*.yaml` (or legacy `pedals/*.yaml`) — device definitions; parsed into `Device` or `Controller` models
- `devices/<id>/presets/*.yaml` — preset definitions (`AnalogPreset`, `DigitalPreset`, `HXStompPreset`)
- `scenes/*.yaml` — scene definitions (device → preset mappings)
- `controller.yaml` (or legacy `mc6.yaml`) — MC6 bank/switch → scene mappings
- `.hlx` files — Line6 HX Stomp patch files; referenced by path but not parsed (content is opaque)

**Written (outputs):**
- `generated/mc6/bank{N}.json` — MC6 bank config JSON files; written by `write_mc6_config()` in `src/rig/generators/mc6_presets.py`
- `.rig/state.json` — rig state tracking file in the config repo; read/written by `src/rig/engine/state.py`

**CLI output formats:**
- `text` (default) — Rich-formatted terminal output
- `json` — machine-readable JSON to stdout (via `sys.stdout.write` bypassing Rich)

## CLI Interface

**Binary:** `rig` (entry point: `rig.cli:app`)

**Commands:**

| Command | Description | Key Options |
|---------|-------------|-------------|
| `rig validate` | Validate rig config | `--config/-c`, `--format/-f`, `--verbose/-v` |
| `rig plan` | Preview changes | `--config/-c`, `--scene/-s`, `--format/-f`, `--verbose/-v` |
| `rig apply` | Apply changes via MIDI | `--config/-c`, `--scene/-s`, `--dry-run`, `--verbose/-v` |
| `rig status` | Show current rig state | `--config/-c`, `--format/-f`, `--verbose/-v` |
| `rig diff` | Show config vs state diff | `--config/-c`, `--format/-f`, `--verbose/-v` |
| `rig generate mc6` | Generate MC6 bank JSON | `--config/-c`, `--verbose/-v` |

**Global options:**
- `--config/-c` — path to rig config directory (default: `.`)
- `--format/-f` — output format: `text` or `json` (default: `text`)
- `--verbose/-v` — repeatable flag; `-v` = INFO, `-vv` = DEBUG

**Exit codes:**
- `0` — success
- `1` — config error or validation failure (`typer.Exit(1)`)

## Data Storage

**Rig Config Repo:**
- External directory of YAML files maintained by the user
- Path passed via `--config` flag at runtime
- No database; file-system only

**State File:**
- `<config_root>/.rig/state.json` — tracks last-applied device state
- Read at plan time; written after successful apply

## Authentication & Identity

- None — local CLI tool, no remote services or auth

## Monitoring & Observability

**Logging:**
- Python `logging` module; configured in `src/rig/log_setup.py`
- Verbosity controlled by `--verbose` flag count
- Default level: WARNING; `-v` = INFO; `-vv` = DEBUG

**Error Tracking:**
- None — errors surface as CLI exit code 1 with Rich-formatted messages

## CI/CD & Deployment

**Hosting:** None — local development tool
**Distribution:** installable Python package via `uv` or pip
**CI Pipeline:** Not detected (no `.github/workflows/` found)

---

*Integration audit: 2026-06-03*
