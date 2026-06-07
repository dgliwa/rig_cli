# Plan 1: Core Protocol & Engine Cleanup — Summary

**Status:** Complete
**Committed:** d5617ba (included in aggregate commit with Plan 2/3)

## What was built

### Formalized Device Protocol in `rig.engine.plugin`
- Added `get_scene_pc_command(preset_id) -> dict[str, Any] | None` method
- Added `presets` property
- Added comprehensive docstring with plugin authoring contract and example
- Removed `midi_connection_io` from `SetupContext` (no longer needed)
- Added `DeviceApplyResult` to type-checking imports

### Removed Phase -1 MIDI connection loop from `apply.py`
- Deleted the entire Phase -1 section (midi connection per unique device)
- Removed `midi_connection_io` parameter from `apply_plan()`
- Removed `midi_connection_io` import and `SetupContext.midi_connection_io` wiring
- Device `setup()` is now the sole MIDI connection mechanism

### Deleted `rig.engine.devices.py`
- All 4 Device classes moved to their respective plugin packages
- AnalogDevice → rig_analog.device (already existed)
- MidiDevice → rig_hx.device:HXStompDevice (created)
- ChaseBlissDevice → rig_chasebliss.device (created)
- MC6Device → rig_morningstar.device (already existed, entry point fixed)

### Removed MIDI connection I/O from CLI
- `midi_connection_io` removed from `rig apply` command
- `InteractiveMidiConnectionIO` import removed
