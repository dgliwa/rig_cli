---
plan: 21-01
status: complete
completed: "2026-06-15"
commits:
  - bb15d3b feat(plugin): define Preset Protocol; update Device.presets type
  - 0df3b77 feat(plugins): add concrete config types to all plugin devices
  - ed10180 fix(registry): use model_construct for placeholder device instances
  - f1010e9 refactor(engine): remove isinstance(config, dict) guards in compute and status
  - 06d1457 test(plugins): add concrete type and validation tests for all plugin devices
---

# Plan 21-01 Summary — Concrete Types at Plugin Boundary

## What Was Done

### T1 — Preset Protocol (`packages/rig/src/rig/engine/plugin.py`)
- Added `Preset` Protocol with `id` and `name` properties
- Updated `Device.presets` return type from `list[Any]` to `list[Preset]`
- Updated docstring example to show `list[Preset]`

### T2 — AnalogConfig + AnalogDevice
- New `packages/rig-analog/src/rig_analog/config.py` with `AnalogConfig(type: Literal["manual"])`
- Updated `AnalogDevice.config: AnalogConfig`, `presets: list[AnalogPreset]`
- Top-level imports; removed lazy imports from `from_raw_yaml`

### T3 — HXStompConfig + HXStompDevice
- New `packages/rig-hx/src/rig_hx/config.py` with `HXStompConfig(type, midi_channel)`
- Updated `HXStompDevice.config: HXStompConfig`, `presets: list[HXStompPreset | MidiPreset]`
- Removed `isinstance(self.config, dict)` guard in `setup`/`get_scene_pc_command`
- Top-level imports; removed lazy imports

### T4 — ChaseBlissDevice
- Moved `DigitalPreset` import to top-level
- Changed `config: Any` → `config: ChaseBlissConfig`, `presets: list[DigitalPreset]`
- Removed `isinstance(device.config, ChaseBlissConfig)` guards in `setup` and `_detect_cba_setup_for_device`
- Tightened `_detect_cba_setup_for_device(device: ChaseBlissDevice, state: RigState, rig: Rig)`
- Fixed `PydanticBaseModel` alias — `ChaseBlissConfig` now inherits from `BaseModel` directly
- Added `TYPE_CHECKING` guard for `Rig` import

### T5 — MC6Config + MC6Device
- New `packages/rig-morningstar/src/rig_morningstar/config.py` with `MC6Config(type, scenes, banks)`
- Updated `MC6Device.config: MC6Config`
- Replaced `isinstance(self.config, dict)` guard in `apply` with `self.config.banks`

### T6 — Plugin Registry
- Replaced try/except constructor loop with `model_class.model_construct(...)` for placeholders

### T7 — Engine Guards
- `packages/rig/src/rig/engine/plan/compute.py`: removed `isinstance(pedal.config, dict)` ternary
- `packages/rig/src/rig/cli/commands/status.py`: removed both `isinstance(device.config, dict)` guards

### T8 — Tests
- `test_analog_device.py`: added AnalogConfig instance test + extra fields ignored test
- `test_device.py` (chasebliss): added ChaseBlissConfig instance test
- `test_hx_device.py` (new): modeler/digital preset types, midi_channel, validation
- `test_mc6_device.py` (new): banks parsing, config instance, invalid banks validation
- `test_plugin.py`: regression test for typed preset annotations on AnalogDevice, ChaseBlissDevice, HXStompDevice
- `test_devices.py`: updated all `config=object()` → concrete config instances; updated HXStomp PC tests to use `MidiPreset`

## Deviations from Plan

- **MC6Device.presets stays `list[Any]`** — MC6 has no real presets. `Preset` Protocol cannot be used as a Pydantic field annotation (Protocol isn't a valid `isinstance` target). The regression test excludes MC6 with a comment explaining the exception.

## Verification

```
$ grep -n "list\[Any\]" packages/rig/src/rig/engine/plugin.py
# (no output — zero hits)

$ make test
3 failed, 306 passed
# The 3 failures are pre-existing stdin-capture issues unrelated to this phase.
```

## Key Files Modified

| File | Action |
|------|--------|
| `packages/rig/src/rig/engine/plugin.py` | Add `Preset` Protocol; update `Device.presets` |
| `packages/rig-analog/src/rig_analog/config.py` | **NEW** `AnalogConfig` |
| `packages/rig-analog/src/rig_analog/device.py` | Type `config`/`presets`; top-level imports |
| `packages/rig-hx/src/rig_hx/config.py` | **NEW** `HXStompConfig` |
| `packages/rig-hx/src/rig_hx/device.py` | Type `config`/`presets`; remove guards |
| `packages/rig-chasebliss/src/rig_chasebliss/device.py` | Type `config`/`presets`; remove guards; tighten sig |
| `packages/rig-morningstar/src/rig_morningstar/config.py` | **NEW** `MC6Config` |
| `packages/rig-morningstar/src/rig_morningstar/device.py` | Type `config`; remove guard |
| `packages/rig/src/rig/engine/plugin_registry.py` | `model_construct` for placeholders |
| `packages/rig/src/rig/engine/plan/compute.py` | Remove `isinstance` guard |
| `packages/rig/src/rig/cli/commands/status.py` | Remove `isinstance` guards |
| `packages/rig-hx/tests/test_hx_device.py` | **NEW** HX Stomp device tests |
| `packages/rig-morningstar/tests/test_mc6_device.py` | **NEW** MC6 device tests |
