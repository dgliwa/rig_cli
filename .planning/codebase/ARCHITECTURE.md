<!-- refreshed: 2026-06-03 -->
# Architecture

**Analysis Date:** 2026-06-03

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     CLI Entry Point                          │
│              `src/rig/cli.py` (Typer app)                    │
│  validate │ plan │ apply │ status │ diff │ generate mc6      │
└────┬───────┴──────┴───────┴────────┴──────┴─────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Config / Loader Layer                      │
│              `src/rig/config/loader.py`                      │
│  Reads YAML repo → cross-reference validates → returns Rig   │
└──────────────────────────┬──────────────────────────────────┘
                           │ Rig (Pydantic model)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Models                           │
│                   `src/rig/models/`                          │
│  Rig · Device · Preset variants · Scene · Controller        │
│  SignalChainPosition                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
     ┌───────────┴─────────────────────────┐
     ▼                                     ▼
┌──────────────────────┐      ┌────────────────────────────┐
│   Engine Layer       │      │    Generators Layer         │
│ `src/rig/engine/`    │      │  `src/rig/generators/`      │
│ plan · apply · diff  │      │  mc6_presets.py             │
│ state · appliers/    │      └────────────────────────────┘
└──────────┬───────────┘
           │ Plan · ApplyContext
           ▼
┌─────────────────────────────────────────────────────────────┐
│              Applier Registry (plugin dispatch)              │
│         `src/rig/engine/appliers/registry.py`               │
│  manual→AnalogApplier  midi→MidiApplier                     │
│  chase_bliss→ChaseBlissApplier  mc6→MC6Applier              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   MIDI Adapter                               │
│              `src/rig/midi/adapter.py`                       │
│  MidiManager: port sharing, PC/CC/SysEx send                │
└─────────────────────────────────────────────────────────────┘
           │                             │
           ▼                             ▼
  Physical Devices                `.rig/state.json`
  (MIDI hardware)            (rig config repo, persisted state)
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI | Command parsing, output formatting, orchestration | `src/rig/cli.py` |
| Loader | Read YAML repo, validate cross-refs, build Rig | `src/rig/config/loader.py` |
| Domain Models | Typed representations of rig entities | `src/rig/models/` |
| Plan Engine | Diff desired state vs `.rig/state.json` | `src/rig/engine/plan.py` |
| Apply Engine | Execute plan, orchestrate appliers, write state | `src/rig/engine/apply.py` |
| Diff Engine | Compare config to last-known state | `src/rig/engine/diff.py` |
| State | Read/write `.rig/state.json` | `src/rig/engine/state.py` |
| Applier Registry | Route device config type → correct applier | `src/rig/engine/appliers/registry.py` |
| AnalogApplier | Manual (human) prompt for knob/switch devices | `src/rig/engine/appliers/analog.py` |
| MidiApplier | Send PC message via MIDI | `src/rig/engine/appliers/midi_device.py` |
| ChaseBlissApplier | CBA 3-phase setup: channel, presets, registration | `src/rig/engine/appliers/chase_bliss.py` |
| MC6Applier | Send bank/switch configs to MC6 via SysEx | `src/rig/engine/appliers/mc6.py` |
| MidiManager | Open/share MIDI output ports, send messages | `src/rig/midi/adapter.py` |
| MC6 Generator | Generate MC6 bank JSON files from rig config | `src/rig/generators/mc6_presets.py` |
| CBA Catalog | Per-model CC control maps for Chase Bliss pedals | `src/rig/catalog/chase_bliss.py` |

## Pattern Overview

**Overall:** Layered pipeline with plugin-based device dispatch.

**Key Characteristics:**
- CLI loads config → engine computes plan → appliers execute actions per device type
- All domain objects are Pydantic BaseModel; state is serialized to/from JSON
- Device behavior is dispatched via `DeviceApplier` Protocol keyed on `config.type`
- State is external (`.rig/state.json` in the rig config repo, not in this codebase)
- Protocols used for structural subtyping (`DeviceApplier` in `appliers/base.py`)

## Layers

**CLI Layer:**
- Purpose: User-facing commands; formats and prints results
- Location: `src/rig/cli.py`
- Contains: Typer commands (`validate`, `plan`, `apply`, `status`, `diff`, `generate mc6`)
- Depends on: config/loader, engine, generators, midi
- Used by: End user via `rig` entrypoint

**Config Layer:**
- Purpose: Parse and validate YAML rig config repo into domain models
- Location: `src/rig/config/`
- Contains: `loader.py` (YAML reads, merging, cross-ref validation), `errors.py` (exception types)
- Depends on: models
- Used by: CLI (all commands call `load_rig`)

**Models Layer:**
- Purpose: Authoritative domain types; no business logic
- Location: `src/rig/models/`
- Contains: `device.py`, `preset.py`, `scene.py`, `rig.py`, `controller.py`, `signal_chain.py`
- Depends on: nothing internal
- Used by: all layers

**Engine Layer:**
- Purpose: Plan computation, apply execution, state management
- Location: `src/rig/engine/`
- Contains: `plan.py`, `apply.py`, `diff.py`, `state.py`, `appliers/`
- Depends on: models, midi, config.errors
- Used by: CLI

**Generators Layer:**
- Purpose: Produce output artifacts from rig config (not apply to devices)
- Location: `src/rig/generators/`
- Contains: `mc6_presets.py` — writes MC6 bank JSON files
- Depends on: models
- Used by: CLI `generate mc6` command

**MIDI Layer:**
- Purpose: Hardware abstraction for MIDI output
- Location: `src/rig/midi/`
- Contains: `adapter.py` (MidiManager), `mc6.py` (MC6 SysEx helpers)
- Depends on: mido (optional import), rtmidi
- Used by: engine/appliers

## Data Flow

### Primary: validate / plan / status / diff

1. CLI command invoked (`src/rig/cli.py`)
2. `load_rig(config_path)` called (`src/rig/config/loader.py`)
   - Reads `rig.yaml`, `signal-chain.yaml`, `devices/*.yaml`, `scenes/*.yaml`, `controller.yaml`
   - Merges filesystem presets onto device objects
   - Validates cross-references (signal chain refs, scene→device→preset refs, CBA CC params)
   - Returns `Rig` model
3. Engine function called with `Rig`:
   - `compute_plan(rig)` reads `.rig/state.json` via `read_state`, diffs desired vs actual
   - `compute_diff(rig)` compares config fields to saved state
4. Result printed to terminal (Rich table, colored text, or JSON)

### Apply Flow

1. `load_rig` returns `Rig` (same as above)
2. `compute_plan(rig)` produces `Plan` (list of `ScenePlan` + `CbaSetupAction`)
3. `apply_plan(plan, rig, config_path, midi=MidiManager())`:
   - Phase -1: Prompt user to connect MIDI ports per device; caches port names in state
   - Phase 0: CBA setup — `ChaseBlissApplier.apply_setup()` runs 3-phase channel/preset/registration flow
   - Phase 1: Scene apply — for each scene action, `get_scene_applier(config_type)` dispatches to correct applier
   - Phase 2: MC6 programming — `MC6Applier.apply_banks()` sends SysEx to MC6
4. On completion: `write_state(config_path, state)` persists updated state to `.rig/state.json`

### Generate MC6

1. `load_rig` → `Rig`
2. `generate_mc6(rig)` iterates `rig.controller.config.banks`, resolves scenes → PC commands via `device.get_scene_pc_command(preset_id)`
3. `write_mc6_config(data, output_path)` writes JSON bank files to `generated/mc6/` in rig config repo

## Key Abstractions

**DeviceApplier Protocol** (`src/rig/engine/appliers/base.py`):
- Structural protocol: any class with `apply_scene(action, ctx) -> DeviceApplyResult`
- Implementations: `AnalogApplier`, `MidiApplier`, `ChaseBlissApplier`, `MC6Applier`
- Registry dispatches by `device.config.type` string: `"manual"`, `"midi"`, `"chase_bliss"`

**ApplyContext** (`src/rig/engine/appliers/base.py`):
- Dataclass passed to all appliers: `dry_run`, `midi`, `connected_devices`, `state`, `config_path`, `rig`

**DeviceConfig discriminated union** (`src/rig/models/device.py`):
- `ManualConfig | MidiConfig | ChaseBlissConfig` discriminated on `type` field
- `get_cc_params(parameters)` method on config — only `MidiConfig`/`ChaseBlissConfig` return CC data

**Preset union** (`src/rig/models/device.py`):
- `Preset = AnalogPreset | DigitalPreset | HXStompPreset`
- Type is implicit: `Device.type` (DeviceType enum) determines which preset subtype is valid

## State Management

State is stored in `.rig/state.json` inside the **user's rig config repo** (not this codebase).

**RigState** (`src/rig/engine/state.py`):
- `devices: dict[str, DeviceState]` — per-device last-known state
- `scenes: dict[str, dict]` — scenes applied (value is currently empty dict)

**DeviceState** (`src/rig/engine/state.py`):
- `last_preset`: last preset ID applied
- `midi_port`: cached MIDI port name for reconnection
- `channel_established`, `presets_saved`, `registration_done`: CBA setup phase flags
- `midi_channel`: channel used for this device

**Read:** `read_state(root)` — loads `.rig/state.json`; returns empty `RigState` if absent
**Write:** `write_state(root, state)` — serializes `RigState` to `.rig/state.json` after apply

## Domain Model Relationships

```
Rig
├── name, description, midi_channel
├── signal_chain: list[SignalChainPosition]
│     └── device_ref → Device.id
├── devices: dict[id, Device]
│     ├── id, manufacturer, model, type (DeviceType)
│     ├── config: ManualConfig | MidiConfig | ChaseBlissConfig
│     │     └── controls: list[Control]  (CC map for CBA/MIDI devices)
│     └── presets: list[AnalogPreset | DigitalPreset | HXStompPreset]
├── controller: Controller | None
│     └── config: MC6Config
│           └── banks: list[dict]  (bank/switch → scene mappings)
└── scenes: dict[name, Scene]
      ├── name, description, tempo, tags
      ├── presets: dict[device_id → preset_id]  (cross-refs into devices)
      └── mc6_bank, mc6_switch  (optional MC6 position annotation)
```

## Architectural Constraints

- **Global state:** `MidiManager` is instantiated per CLI invocation and passed through `ApplyContext`; no module-level singletons except the applier instances in `appliers/registry.py` (`_cba_applier`, `_mc6_applier`)
- **Optional MIDI:** mido/rtmidi are soft dependencies; `MidiManager` degrades gracefully when absent
- **CBA catalog lazy load:** `rig.catalog.chase_bliss.get_controls()` is imported inside `Device._populate_cba_controls` model validator to avoid circular imports
- **Legacy compatibility:** `pedals/` directory name accepted alongside `devices/`; `pedal.py` re-exports from `device.py` for backward compat; `pedals` property on `Rig` aliases `devices`

## Anti-Patterns

### CBA setup mixed into Plan

**What happens:** `_detect_cba_setup` runs inside `compute_plan` and CBA setup is on `Plan.cba_setup` rather than per-device plan entries.
**Why it's wrong:** Plan and apply diverge — CBA setup is not scoped to scenes like other device actions. TODO markers reference this (#13 and inline).
**Do this instead:** Model CBA setup as device-level phases inside each `ScenePlan.device_actions`, consistent with how other device types work.

### `apply_plan` is monolithic

**What happens:** `src/rig/engine/apply.py::apply_plan` handles MIDI connection prompting, CBA setup, scene application, and MC6 programming in one 150-line function.
**Why it's wrong:** Difficult to test phases independently; TODO comment acknowledges this.
**Do this instead:** Extract each phase into its own function or class.

### Preset type inferred from device type

**What happens:** `_merge_presets` in `loader.py` uses `device.type` (analog/modeler/digital) to decide which Preset subclass to instantiate from directory YAML.
**Why it's wrong:** Fragile branching; the YAML itself doesn't declare its preset type.
**Do this instead:** Inline presets in device YAML (already preferred per TODOs in loader) with explicit discriminator.

---

*Architecture analysis: 2026-06-03*
