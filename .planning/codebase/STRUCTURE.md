<!-- refreshed: 2026-06-03 -->
# Codebase Structure

**Analysis Date:** 2026-06-03

## Directory Layout

```
rig-cli/
├── src/
│   └── rig/                    # Main package
│       ├── cli.py              # Typer CLI entry point
│       ├── interaction.py      # MIDI connection prompts (user I/O)
│       ├── log_setup.py        # Logging configuration
│       ├── models/             # Pydantic domain models
│       │   ├── rig.py          # Rig aggregate root
│       │   ├── device.py       # Device + DeviceConfig + Control
│       │   ├── pedal.py        # Re-export shim (backward compat)
│       │   ├── preset.py       # AnalogPreset, DigitalPreset, HXStompPreset
│       │   ├── scene.py        # Scene
│       │   ├── controller.py   # Controller, MC6Config
│       │   └── signal_chain.py # SignalChainPosition
│       ├── config/             # YAML loading and validation
│       │   ├── loader.py       # load_rig() — main entry for config parsing
│       │   └── errors.py       # ConfigError hierarchy
│       ├── engine/             # Plan, apply, diff, state
│       │   ├── plan.py         # compute_plan() → Plan model
│       │   ├── apply.py        # apply_plan() — orchestrates appliers
│       │   ├── diff.py         # compute_diff(), format_diff()
│       │   ├── state.py        # RigState, DeviceState, read/write_state
│       │   └── appliers/       # Per-device-type apply logic
│       │       ├── base.py     # DeviceApplier Protocol, ApplyContext
│       │       ├── registry.py # Dispatch table config_type → applier
│       │       ├── analog.py   # AnalogApplier (manual/human prompt)
│       │       ├── midi_device.py # MidiApplier (PC message)
│       │       ├── chase_bliss.py # ChaseBlissApplier (3-phase CBA setup)
│       │       └── mc6.py      # MC6Applier (SysEx bank programming)
│       ├── generators/         # Output artifact generation
│       │   └── mc6_presets.py  # generate_mc6(), write_mc6_config()
│       ├── midi/               # MIDI hardware abstraction
│       │   ├── adapter.py      # MidiManager (port sharing, PC/CC/SysEx)
│       │   └── mc6.py          # MC6-specific SysEx message builders
│       └── catalog/            # Device-specific CC control maps
│           └── chase_bliss.py  # get_controls(manufacturer, model) → list[Control]
├── tests/
│   ├── fixtures/
│   │   └── sample_rig/         # Minimal rig config repo for tests
│   │       ├── rig.yaml
│   │       ├── signal-chain.yaml
│   │       ├── controller.yaml
│   │       ├── devices/
│   │       │   ├── hx-stomp.yaml
│   │       │   ├── hx-stomp/presets/lead.yaml
│   │       │   ├── mood.yaml
│   │       │   └── mood/presets/preset-1.yaml
│   │       ├── scenes/lead.yaml
│   │       └── hlx/lead.hlx
│   ├── test_appliers.py
│   ├── test_apply.py
│   ├── test_catalog.py
│   ├── test_cli.py
│   ├── test_diff.py
│   ├── test_loader.py
│   ├── test_logging.py
│   ├── test_mc6_generator.py
│   ├── test_mc6_sysex.py
│   ├── test_midi_adapter.py
│   ├── test_models.py
│   └── test_plan.py
├── pyproject.toml              # Project metadata, dependencies, entrypoint
├── Makefile                    # make test / make lint / make format shortcuts
└── CLAUDE.md                   # Project-level Claude context
```

## Directory Purposes

**`src/rig/models/`:**
- Purpose: Pydantic domain models only — no business logic
- Contains: All entity types (Device, Preset variants, Scene, Rig, Controller, SignalChainPosition)
- Key files: `device.py` (most complex — DeviceType, DeviceConfig variants, Control, Device)

**`src/rig/config/`:**
- Purpose: Load and validate YAML rig config repo into domain models
- Contains: `loader.py` (YAML parsing, preset merging, cross-ref validation), `errors.py`
- Key files: `loader.py::load_rig(root_path)` — the single function called by every CLI command

**`src/rig/engine/`:**
- Purpose: Core business logic — plan, apply, diff, state persistence
- Contains: Top-level engine functions + `appliers/` subdirectory for per-device dispatch
- Key files: `plan.py` (compute_plan), `apply.py` (apply_plan), `state.py` (read/write state)

**`src/rig/engine/appliers/`:**
- Purpose: Plugin-style per-device-type apply implementations
- Contains: One applier per device config type + Protocol base + registry
- Key files: `base.py` (DeviceApplier Protocol), `registry.py` (dispatch table)

**`src/rig/generators/`:**
- Purpose: Produce output files from rig config (not real-time device interaction)
- Contains: `mc6_presets.py` — generates MC6 bank JSON artifacts

**`src/rig/midi/`:**
- Purpose: MIDI hardware abstraction; isolates mido/rtmidi dependency
- Contains: `adapter.py` (MidiManager), `mc6.py` (MC6 SysEx helpers)

**`src/rig/catalog/`:**
- Purpose: Static device knowledge (CC maps) for vendor-specific devices
- Contains: `chase_bliss.py` — returns Control lists for Chase Bliss Audio pedal models

**`tests/fixtures/sample_rig/`:**
- Purpose: Minimal but complete rig config repo used as test fixture
- Generated: No — hand-authored YAML
- Committed: Yes

## Key File Locations

**Entry Points:**
- `src/rig/cli.py`: Typer application; all CLI commands defined here
- `pyproject.toml`: `[project.scripts]` defines `rig = "rig.cli:app"` entrypoint

**Configuration Loading:**
- `src/rig/config/loader.py::load_rig(root_path: str) -> Rig`: called by every command

**Engine:**
- `src/rig/engine/plan.py::compute_plan(rig, root_path) -> Plan`
- `src/rig/engine/apply.py::apply_plan(plan, rig, config_path, dry_run, scene, midi) -> ApplyResult`
- `src/rig/engine/state.py::read_state(root)` / `write_state(root, state)`

**Plugin dispatch:**
- `src/rig/engine/appliers/registry.py::get_scene_applier(config_type)` — returns applier by device config type string

**MIDI:**
- `src/rig/midi/adapter.py::MidiManager` — instantiated once per `apply` run

**Domain models:**
- `src/rig/models/rig.py::Rig` — aggregate root passed through all engine functions
- `src/rig/models/device.py::Device` — core device type with discriminated config union

## Naming Conventions

**Files:**
- Modules named after their primary type or concern: `plan.py`, `state.py`, `adapter.py`
- Applier files named after device type: `analog.py`, `midi_device.py`, `chase_bliss.py`, `mc6.py`

**Classes:**
- Models: PascalCase noun (`Device`, `Scene`, `RigState`, `DeviceAction`)
- Protocols: PascalCase noun + role suffix (`DeviceApplier`)
- Appliers: PascalCase noun + `Applier` suffix (`MidiApplier`, `ChaseBlissApplier`)
- Config variants: PascalCase noun + `Config` suffix (`MidiConfig`, `MC6Config`)

**Functions:**
- Engine functions: `verb_noun` pattern (`compute_plan`, `apply_plan`, `read_state`, `write_state`, `generate_mc6`)
- Private helpers: underscore prefix (`_read_yaml`, `_detect_cba_setup`, `_is_cba`)

**Enums:**
- Use `StrEnum` so values serialize naturally to/from YAML strings (`DeviceType`, `ControlType`, `ControllerType`)

## Where to Add New Code

**New device type (e.g., a new MIDI controller):**
1. Add config model to `src/rig/models/device.py` (extend `DeviceConfig`, add `Literal` type)
2. Add applier at `src/rig/engine/appliers/<device_type>.py` implementing `DeviceApplier` Protocol
3. Register in `src/rig/engine/appliers/registry.py::_SCENE_APPLIERS`
4. Add tests at `tests/test_appliers.py`

**New CLI command:**
- Add `@app.command()` decorated function to `src/rig/cli.py`
- If it's a sub-group command (like `generate`), add to `gen_app` typer or create a new sub-typer

**New preset type:**
- Add to `src/rig/models/preset.py` as a new Pydantic BaseModel
- Add to `Preset` union in `src/rig/models/device.py`
- Update loader in `src/rig/config/loader.py::_merge_presets` if directory-loading needed
- Update plan engine in `src/rig/engine/plan.py` to handle the new type

**New generator (output artifact):**
- Add new file to `src/rig/generators/<name>.py`
- Add `@gen_app.command()` to `src/rig/cli.py`

**New vendor catalog:**
- Add file to `src/rig/catalog/<vendor>.py`
- Expose a `get_controls(manufacturer, model)` function returning `list[Control]`
- Wire into `Device._populate_cba_controls` or a new model validator

**Tests:**
- Co-located with concern area: `tests/test_<module>.py`
- Shared fixture data: `tests/fixtures/sample_rig/`

## Special Directories

**`.rig/` (in rig config repo, not this codebase):**
- Purpose: Persisted apply state (`state.json`)
- Generated: Yes — by `apply` command
- Committed: Up to the user (tracks physical device state)

**`generated/mc6/` (in rig config repo):**
- Purpose: Output of `rig generate mc6` — MC6 bank JSON files
- Generated: Yes
- Committed: Up to the user

**`src/rig_cli.egg-info/`:**
- Purpose: Python package metadata generated by pip install
- Generated: Yes — do not edit
- Committed: No

---

*Structure analysis: 2026-06-03*
