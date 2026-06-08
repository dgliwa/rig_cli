---
phase: 10-schema-loader-rewrite
status: complete
milestone: v1.2
requirements:
  - SCHEMA-01
  - SCHEMA-02
  - SCHEMA-04
  - SCHEMA-05
  - LOADER-01
  - LOADER-02
started: 2026-06-08T04:00:00Z
completed: 2026-06-08T05:00:00Z
---

## Summary

Phase 10 rewrote the config loader to support a single-file `rig.yaml` schema, replacing
the multi-file directory layout. This is the largest structural change in v1.2.

### What changed

| File | Change |
|------|--------|
| `packages/rig/src/rig/config/loader.py` | Rewritten for single-file `rig.yaml`. Removes `_load_devices_dir()`, `_merge_presets()`. Keeps `_load_scenes()` as deprecated stub for backward compat. Adds `_parse_presets()`, `_extract_controller_scenes()`, `_get_composes()`. |
| `packages/rig/tests/fixtures/sample_rig/` | Replaced multi-file layout (9 files) with single `rig.yaml` + `hlx/lead.hlx`. Removed `devices/`, `scenes/`, `signal-chain.yaml`. |
| `packages/rig/tests/test_loader.py` | Rewritten for single-file fixtures. Added tests for empty devices, direct file path, controller composes validation. |
| `packages/rig/tests/test_cli.py` | Updated `_write_minimal_rig` helper to single-file schema. |
| `packages/rig/tests/test_cli_plan.py` | Updated all 4 config helpers to single-file schema. |
| `packages/rig/tests/test_catalog.py` | Fixed `FIXTURE_PATH` to use `Path(__file__).parent` for test-environment independence. |

### New schema

Single `rig.yaml` replaces the multi-file approach:

```yaml
name: sample-rig
description: Reference fixture
devices:
  - id: mood
    type: digital                   # DeviceType enum (not entry point key)
    config:
      type: chase_bliss             # Entry point key → plugin dispatch
      midi_channel: 2
      controls: [...]
    presets:
      - id: preset-1
        name: Shimmer Delay
        preset_number: 1
        parameters: {time: 72, mix: 90}
  - id: mc6
    type: controller
    config:
      type: controller
      midi_channel: 1
      composes: [hx-stomp, mood]    # Optional: references controlled devices
      scenes:
        lead:
          description: Lead tone
          presets: {hx-stomp: lead, mood: preset-1}
          tags: [lead]
      banks:
        - bank: 1
          name: Bank 1
          switches:
            A: {scene: lead}
```

### Key design decisions

1. **Device list order = signal chain** — no separate `signal-chain.yaml` or positional fields
2. **Presets inline** — each device entry contains its own presets; parsed to correct model type (`AnalogPreset` for analog, `HXStompPreset` for modelers, `DigitalPreset` for digital)
3. **Plugin dispatch by `config.type`** — entry point key from `config.type` field (e.g., `"midi"`, `"chase_bliss"`, `"controller"`, `"manual"`)
4. **Scenes extracted from controller** — controller carries `scenes` in config; loader builds `Scene` objects for `Rig.scenes`; controller-specific fields (bank, switch) remain in device config
5. **`composes` validation** — optional `composes: [id1, id2]` on controllers is validated against existing device IDs

### Removed infrastructure

- `_load_devices_dir()` — no more directory-based device loading
- `_merge_presets()` — no more filesystem-preset merging
- `signal-chain.yaml` — signal chain comes from device list order
- Fixture: `devices/`, `scenes/`, `signal-chain.yaml` files removed

### Test results

- 274 tests pass (up from 272 pre-Phase-10)
- 11 plugin tests pass

### New tests added

- `test_empty_devices_list` — empty devices array produces empty rig
- `test_direct_path_to_rig_yaml` — load_rig accepts direct file path
- `test_controller_composes_validation` — valid composes works
- `test_controller_composes_unknown_device` — missing composes ref raises error
- `test_no_signal_chain_file_needed` — signal-chain.yaml not required
