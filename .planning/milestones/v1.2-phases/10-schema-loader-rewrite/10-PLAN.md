---
phase: 10-schema-loader-rewrite
milestone: v1.2
goal: "Users can run `rig validate` against a single `rig.yaml` where device list order defines the signal chain, controller devices compose other devices by ID, and scenes live inside the controller"
depends_on: phase-09-core-model-cleanup
requirements:
  - SCHEMA-01
  - SCHEMA-02
  - SCHEMA-04
  - SCHEMA-05
  - LOADER-01
  - LOADER-02
success_criteria:
  - "rig validate path/to/rig.yaml succeeds when rig.yaml is a single file with a flat devices list"
  - "Device list order in rig.yaml is treated as the signal chain — no signal-chain.yaml is read"
  - "Controller with composes: [id1, id2] correctly references controlled devices"
  - "Scenes defined inside controller config are accessible via rig.scenes"
  - "Device construction dispatched via type field → entry point lookup; unknown types produce clear error"
  - "All tests pass"
---

# Phase 10: Schema & Loader Rewrite

## New Single-File Schema

The new `rig.yaml` defines everything in one file:

```yaml
name: sample-rig
description: Reference fixture for Mood + HX Stomp + MC6 setup
devices:
  - id: mood
    name: MOOD MKII
    type: chase_bliss
    config:
      type: chase_bliss
      midi_channel: 2
      controls:
        - name: time
          type: knob
          midi_cc: 14
          min: 0
          max: 127
    presets:
      - id: preset-1
        name: Shimmer Delay
        preset_number: 1
        parameters:
          time: 72
          mix: 90

  - id: hx-stomp
    name: HX Stomp XL
    type: modeler
    config:
      type: midi
      midi_channel: 1
    presets:
      - id: lead
        name: Lead Tone
        preset_number: 5
        hlx_file: hlx/lead.hlx

  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      composes: [hx-stomp, mood]
      scenes:
        lead:
          description: Lead tone with shimmer
          presets:
            hx-stomp: lead
            mood: preset-1
          tags: [lead]
      banks:
        - bank: 1
          name: Bank 1
          switches:
            A:
              scene: lead
```

### Key design decisions

1. **Device list order = signal chain** — no separate signal-chain.yaml or position fields
2. **Presets inline** — each device entry contains its presets array; no filesystem preset loading
3. **Scenes inside controller config** — controller device carries scenes with presets; loader extracts to `Rig.scenes`
4. **`composes` field** — controller optionally lists which device IDs it controls
5. **Plugin dispatch by `config.type`** — entry point key from `config.type` field (e.g., `"midi"`, `"chase_bliss"`, `"controller"`, `"manual"`)
6. **Extra fields silently ignored** — plugin device models use `extra="allow"`; `Device` in core accepts extras via `**kwargs`

---

## Wave 1: New Schema + Loader Rewrite

**Files modified:**
- `packages/rig/src/rig/config/loader.py`
- `packages/rig/tests/fixtures/sample_rig/rig.yaml`
- `packages/rig/tests/fixtures/sample_rig/` (remove multi-file structure, keep hlx/)

**Requirements covered:** SCHEMA-01, SCHEMA-02, LOADER-01, LOADER-02

### Task 1: Rewrite `load_rig()` for single-file schema

The new `load_rig()` flow:

1. Accept `root_path` (directory path or direct path to `rig.yaml`)
2. Read single `rig.yaml` file
3. Extract `name`, `description`, `midi_channel` from top level
4. Iterate `devices` list in order → this IS the signal chain
5. For each device entry, call `_parse_device()` to dispatch to plugin
6. For controller devices, extract `scenes` from config and build `Scene` objects
7. Build `Rig(name=..., signal_chain=..., devices=..., scenes=...)`
8. Run `_validate_references()` (unchanged logic)

Remove these functions entirely:
- `_load_devices_dir()` — no more devices/*.yaml loading
- `_merge_presets()` — no more filesystem preset merging
- The scene-wiring code (removed in Phase 9 already but verify)

Simplify `_parse_device()`:

```python
def _parse_device(data: dict) -> Any:
    config_data = data.get("config") or {}
    config_type = config_data.get("type") if isinstance(config_data, dict) else None
    model_class = get_registry().get_model(config_type)
    if model_class is None:
        raise ValidationError(
            f"Unknown device config type '{config_type}' — is the plugin registered?"
        )
    return model_class(**data)
```

No more temp `Device(**data)` — plugin model classes handle their own construction. Extra YAML fields are accepted via `extra="allow"` on plugin models.

### Task 2: Update sample_rig fixture

Replace multi-file layout with single `rig.yaml`:

**Before:** `tests/fixtures/sample_rig/`
```
rig.yaml                          # just name/description
signal-chain.yaml                 # device order
devices/mc6.yaml                  # controller
devices/mood.yaml                 # chase_bliss device
devices/hx-stomp.yaml             # modeler device
devices/mood/presets/preset-1.yaml
devices/hx-stomp/presets/lead.yaml
scenes/lead.yaml                  # scene
hlx/lead.hlx                      # raw .hlx file
```

**After:** `tests/fixtures/sample_rig/`
```
rig.yaml                          # everything in one file
hlx/lead.hlx                      # still needed for HX Stomp preset test
```

The `rig.yaml` contains all devices (mood, hx-stomp, mc6) with inline presets, scenes inside controller config, and device list order as signal chain.

Keep `hlx/lead.hlx` as a binary fixture referenced by `lead` preset's `hlx_file` field.

---

## Wave 2: Controller `composes` + Scene Extraction

**Files modified:**
- `packages/rig/src/rig/config/loader.py`
- `packages/rig/src/rig/models/scene.py` (possibly - see below)

**Requirements covered:** SCHEMA-04, SCHEMA-05

### Task 1: Controller scene extraction in loader

The loader extracts scenes from the controller device's config and builds `Rig.scenes`:

```python
# Inside load_rig(), after all devices are parsed:
scenes: dict[str, Scene] = {}
for device in devices.values():
    if device.type == DeviceType.CONTROLLER:
        # Scenes come from the raw YAML config data
        device_raw = next(d for d in device_list_data if d["id"] == device.id)
        config_raw = device_raw.get("config", {})
        controller_scenes = config_raw.get("scenes", {})
        for scene_name, scene_data in controller_scenes.items():
            scenes[scene_name] = Scene(
                name=scene_name,
                description=scene_data.get("description"),
                presets=scene_data.get("presets", {}),
                tags=scene_data.get("tags", []),
            )
```

The controller's `config` dict retains the full scene data (including bank/switch positions) for its own apply logic. The `Scene` model on `Rig.scenes` only includes `name`, `description`, `presets`, `tags` — no controller-specific fields. This keeps `Scene` clean and avoids re-adding `mc6_bank`/`mc6_switch` after Phase 9 removed them.

### Task 2: `composes` validation

When a controller device's config has `composes: [id1, id2]`, validate that each referenced device ID exists. Add to `_validate_references()`:

```python
# Validate controller composes references
for device in rig.devices.values():
    if device.type == DeviceType.CONTROLLER:
        composed_ids = _get_composes(device)
        for cid in composed_ids:
            if cid not in device_ids:
                raise MissingReferenceError(
                    f"Controller '{device.id}' composes unknown device '{cid}'"
                )
```

Helper function to handle both dict and model config:

```python
def _get_composes(device: Any) -> list[str]:
    if isinstance(device.config, dict):
        return device.config.get("composes", [])
    return getattr(device.config, "composes", [])
```

### Task 3: `_load_scenes` function deprecation

The `_load_scenes` function is no longer called by `load_rig()` but is kept for the direct unit test `test_load_scenes_nonexistent_dir_returns_empty`. Add a deprecation comment and update the test to reference the new scene-loading path. This function will be fully removed in Phase 11.

---

## Wave 3: Test Updates + Cleanup

**Files modified:**
- `packages/rig/tests/fixtures/sample_rig/` — single-file rewrite
- `packages/rig/tests/test_loader.py` — update fixtures and assertions
- `packages/rig/tests/test_catalog.py` — update fixture path usage
- `packages/rig/tests/test_mc6_generator.py` — update device construction if needed
- `packages/rig/src/rig/config/loader.py` — remove `_load_devices_dir`, maybe `_load_scenes`

**Requirements covered:** All SCHEMA/LOADER verification

### Task 1: Update test_loader.py

The `rig_dir` fixture currently creates multi-file layout. Rewrite to create a single `rig.yaml`:

```python
@pytest.fixture
def rig_dir(tmp_path):
    d = tmp_path / "rig"
    d.mkdir()
    _write(d, "rig.yaml", """
name: test-rig
midi_channel: 1
devices:
  - id: brothers
    type: digital
    config:
      type: midi
      midi_channel: 3
    presets:
      - id: low-gain
        name: Low Gain
        preset_number: 4
      - id: lead
        name: Lead
        preset_number: 7

  - id: tumnus
    type: analog
    config:
      type: manual
    presets:
      - id: edge
        name: Edge of Breakup
        values:
          Gain: 3.5

  - id: mc6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        billy-clean:
          presets:
            brothers: low-gain
      banks: []
""")
    return d
```

Then update all test methods:
- `test_loads_full_config` — same assertions, new fixture
- `test_loads_signal_chain` — remove signal-chain.yaml writes; signal chain is device list order
- `test_loads_presets` — same assertions (presets now inline)
- `test_loads_scenes` — same assertions (scenes now from controller config)
- `test_missing_rig_yaml` — unchanged
- `test_missing_signal_chain` — remove this test (no signal-chain.yaml needed)
- `test_invalid_yaml` — unchanged
- `test_broken_preset_reference` — write into single rig.yaml instead
- `test_broken_pedal_reference` — write into single rig.yaml instead
- `test_broken_signal_chain_ref` — remove this test (signal chain from device list order)
- `test_scenes_dir_missing` — remove this test (scenes no longer loaded from directory)
- `test_non_cba_pedal_without_midi_channel_accepted` — update device YAML in single file
- `test_hx_preset_loaded_as_hx_type` — update device YAML in single file
- `test_loads_controller_as_device` — same assertions
- `test_scenes_accessible_via_controller` — same assertions

For `TestRegistryDispatch` tests:
- All device entries now in single rig.yaml — same assertions should work
- `test_unknown_config_type_raises_validation_error` — set config.type to unknown in single file
- `test_all_devices_have_apply_method` — same assertions

For `test_load_scenes_nonexistent_dir_returns_empty` — update to not call `_load_scenes` directly since it's deprecated. Either:
- Remove the test (scenes no longer loaded from directories)
- Or keep with a TODO: Phase 11 removal marker

### Task 2: Update test_catalog.py

The `FIXTURE_PATH = "tests/fixtures/sample_rig"` needs to still work since `load_rig` accepts directory paths. The sample_rig fixture now has a single `rig.yaml` inside it. The tests that load the fixture (lines 123-151) should work unchanged.

### Task 3: Update test_mc6_generator.py

The `_make_rig()` helper builds `Device` objects directly (not through the loader). It currently uses `manufacturer` and `model` kwargs on `Device` which are silently ignored by Pydantic. No changes needed for the loader rewrite, but the helper should be updated to remove `manufacturer`/`model` kwargs for cleanliness (they're ignored anyway).

### Task 4: Verify all downstream tests pass

Run `uv run pytest packages/ -q --tb=short` and ensure all tests pass. Key test files:
- `test_loader.py` — updated fixture + assertions
- `test_catalog.py` — fixture loading
- `test_mc6_generator.py` — programmatic rig construction
- `test_models.py` — model construction (no loader)
- `test_plan.py` — plan computation (uses load_rig via test helpers)
- `test_diff.py` — diff computation
- `test_apply.py` — apply execution
- `test_appliers.py` — device appliers
- `test_graph.py` — dependency graph
- `test_devices.py` — plugin device tests
- `test_cli_plan.py` — CLI plan command
- Plugin tests in `packages/rig-*/tests/`

Expected test count: ~270 (some test_loader tests removed due to multi-file removal).

---

## Threat Model

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-10-01 | Tampering | Device YAML → plugin model | accept | Plugin models validate their own data; extra fields in YAML silently ignored by `extra="allow"` |
| T-10-02 | Tampering | Controller scenes extraction | accept | Scene presets validated by `_validate_references` (same as current flow) |
| T-10-03 | Information Disclosure | Signal chain as device order | accept | Device IDs are not secrets; no new exposure |
