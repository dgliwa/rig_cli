# Plan 2: Plugin Device Wiring — Summary

**Status:** Complete
**Committed:** d5617ba (included in aggregate commit with Plan 1/3)

## What was built

### Updated all 4 plugin entry points
- `rig-analog`: `manual → rig_analog.device:AnalogDevice`
- `rig-chasebliss`: `chase_bliss → rig_chasebliss.device:ChaseBlissDevice`
- `rig-hx`: `midi → rig_hx.device:HXStompDevice`
- `rig-morningstar`: `controller → rig_morningstar.device:MC6Device`

### Created HXStompDevice in `rig-hx`
- Full Pydantic BaseModel implementing Device Protocol
- `setup()` handles MIDI port connection via `prompt_midi_connect()`
- `apply()` sends PC messages with retry/skip/quit prompt loop
- `get_scene_pc_command()` returns PC dict for DigitalPreset/HXStompPreset
- Graceful handling of `midi=None` (no MIDI available)

### Created full ChaseBlissDevice in `rig-chasebliss`
- Merged old core ChaseBlissDevice + cba_setup helper + applier logic
- `setup()` handles MIDI port connection and 3-phase CBA init
- 3-phase init: establish_channel → build_preset → register_scenes (via ChaseBlissApplier)
- `setup()` gracefully handles `midi=None` and `dry_run=True`
- `apply()` sends PC messages (CBA scene switching is just PC)
