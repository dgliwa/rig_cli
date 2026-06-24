# rig-cli

## What This Is

Infrastructure-as-Code CLI for a guitar rig. Reads a YAML config repo describing pedals, presets, and scenes, then validates, plans, diffs, and applies those configurations to physical MIDI devices. Designed for one user (the rig owner) who wants repeatable, git-tracked rig state.

## Core Value

A single command should bring the physical rig to the exact state described in the config repo — no guessing, no manual knob-hunting.

## Requirements

### Validated

- ✓ YAML config loading and cross-reference validation (`validate` command) — existing
- ✓ Domain models: Pedal, Preset (Analog/Digital/HXStomp), Scene, Rig, SignalChain — existing
- ✓ HX Stomp preset management (PC messages + `.hlx` file references) — existing
- ✓ MC6 bank/switch JSON generation (`generate mc6` command) — existing
- ✓ Apply engine: sends MIDI PC/CC, prompts for analog-only presets, updates state — existing
- ✓ MIDI adapter (Mido + rtmidi, port sharing, PC/CC/SysEx send) — existing
- ✓ CLI commands: `validate`, `apply`, `status`, `diff`, `generate mc6` — existing
- ✓ CBA (Chase Bliss Audio) multi-phase apply flow (channel → preset → scene) — existing
- ✓ **`mark_preset_saved` helper extracted** — all `presets_saved` dict mutations now flow through `update_device_state` via this named helper; no raw dict assignments remain (#11) — v1.0
- ✓ **`detect_cba_setup` promoted to public API** — renamed from `_detect_cba_setup`, `_is_cba` inlined and removed; no cross-module private symbol imports in engine package (#12) — v1.0
- ✓ **Decouple apply engine from I/O** — `ConfirmationIO`, `StateWriter`, `MidiConnectionIO` Protocols in `ports.py`; all appliers route through `ApplyContext.confirmation_io`; zero `builtins.input` patches in tests — v1.0
- ✓ **Controller as first-class Device** — `DeviceType.CONTROLLER` + `ControllerConfig` in discriminated union; `Rig.apply_order()` DFS; loader drops legacy controller path; `DevicePlugin` Protocol + `PluginRegistry` scaffold — v1.0
- ✓ **Plugin architecture** — all appliers (Analog, MIDI, ChaseBliss, MC6) migrated to `Device` Protocol + `PluginRegistry`; engine routes exclusively through registry; adding a new device type requires only plugin registration — v1.0
- ✓ **`rig plan` command** — graph-ordered diff against `state.json`, typed action list (configure / verify / analog / no_change), text + JSON output, exit codes, cold-start warning, `--scene` filter, `--show-unchanged` flag — v1.0
- ✓ **CBA single-apply convergence** — `detect_cba_setup` is forward-looking; a single `rig apply` converges a fresh CBA device through all 3 phases without re-detection — v1.0
- ✓ **Plugin package extraction** — `rig.devices` entry point group; `rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar` as independent pip packages; `rig` core has zero hard plugin dependencies — v1.1
- ✓ **Device-level MIDI lifecycle** — `Device.setup()` is sole MIDI connection mechanism; Phase -1 engine loop removed; engine has no plugin-specific MIDI logic — v1.1
- ✓ **Dead code elimination** — 7 core files deleted (mc6.py, chase_bliss.py, appliers/chase_bliss.py, catalog, controller model, interaction modules); plugins own their full implementations — v1.1

- ✓ **Single-file `rig.yaml` schema** — device list order defines signal chain; `SignalChainPosition` removed; presets inline; plugin dispatch by `config.type` entry point key — v1.2
- ✓ **Core model fully decoupled from plugins** — `Device.config: Any`; `ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig`, `Control`, `ControlType` evicted from core — v1.2
- ✓ **Loader rewritten for single-file layout** — `load_rig()` parses one `rig.yaml`; multi-file paths removed; scenes extracted from controller device config — v1.2
- ✓ **Dead code sweep** — `rig generate mc6` command removed; `composes` validation removed; all `TODO: 1.2` markers cleared; multi-file compat paths deleted — v1.2
- ✓ **`Rig.scenes` as computed property** — scenes aggregated from controller devices, not stored as a flat field; `compute.py` `is_hx` branch removed; all preset lookups unified through `_get_preset_number` — v1.2
- ✓ **CBA-04: Control model default field** — `Control.default: float | None = None` added; footswitches/utilities get `None`, knobs get numeric defaults — v1.3
- ✓ **CBA-01: Wombtone MkII catalog** — 12 controls (CC14-21) with ranges and defaults — v1.3
- ✓ **CBA-02: Brothers AM catalog** — 28 controls (8 knobs, 3 toggles, 15 dipswitches, 2 footswitches) with ranges and defaults — v1.3
- ✓ **CBA-03: Mood MkII catalog backfill** — 47 controls; CC24-29, CC31-33, CC52 added; CC102=wet_bypass, CC103=loop_bypass — v1.3
- ✓ **CBA-05: Preset parameter validation** — unknown names and out-of-range values raise `ValidationError` before pedal interaction — v1.3
- ✓ **CBA-06: Reset-to-defaults** — per-preset CC reset of all resettable controls before preset CC sends — v1.3

- ✓ **Single `Device` Protocol end-to-end** — `Device(BaseModel)` legacy model retired; `Rig.devices: dict[str, Device]` typed against Protocol; zero `hasattr` or `cast(Any)` guards in engine — v1.4
- ✓ **Concrete plugin config types** — `AnalogConfig`, `HXStompConfig`, `ChaseBlissConfig`, `MC6Config` in respective plugins; `config: Any` gone; YAML construction validates against concrete type — v1.4
- ✓ **`Preset` Protocol in core** — `presets: list[Preset]` in all 4 plugins; `MC6Device` uses `SkipValidation[list[Preset]]` to satisfy Pydantic constraint — v1.4
- ✓ **Dead stubs removed** — `plan()` and `diff()` stubs deleted from Protocol and all 4 plugin device files — v1.4
- ✓ **Single `ApplyContext` type** — `appliers/base.py` deleted; `DeviceApplyContext` from `engine.plugin` is the sole apply context throughout `apply.py` — v1.4
- ✓ **Test infrastructure clean** — Root `tests/` directory deleted; 309 passed, 0 failures; 3 stdin-capture tests pass without `-s` flag — v1.4
- ✓ **`DeviceType` + `ActionStatus` enums throughout** — zero raw string device-type comparisons; `DeviceAction` fully enum-typed — v1.4
- ✓ **ConfirmationIO I/O Parity (Analog)** — `AnalogDevice.apply()` threaded through `ConfirmationIO` Protocol with retry loop; `prompt_analog()` deleted; 3 analog tests use `InMemoryPromptAdapter` without `builtins.input` patching — v1.5
- ✓ **Isolated Preset Apply** — `apply_device_preset()` engine function + `--device`/`--preset` CLI flags on `rig apply` for single-device preset apply without scene plan; `state.scenes` never modified — v1.5
- ✓ **Editor Protocol + CLI + YAML Writer** — `EditorProtocol` + `EditContext` in `plugin.py`; `rig edit <device-id> <preset-id>` command; ruamel.yaml round-trip write-back with comment preservation; save/discard lifecycle — v1.5
- ✓ **CBA Live Editor** — `ChaseBlissDevice.edit()` sends live CC on each valid `<control> <value>` entry; unknown control/out-of-range re-prompts without advancing — v1.5
- ✓ **Analog Key-Value Editor** — `AnalogDevice.edit()` implements `EditorProtocol` with no-MIDI key-entry loop; validates against existing keys only — v1.5
- ✓ **`EditContext.midi` field** — `MidiManager | None = None` for CC-based plugins; `edit.py` passes `midi=None` explicitly — v1.5
- ✓ **CAT-01: Catalog as single source of truth** — Mood MkII CC swap fixed (`wet_bypass=102`, `loop_bypass=103`); named constants `MOOD_MKII_WET_BYPASS_CC/LOOP_BYPASS_CC` exported; all test assertions reference catalog, not literals — v1.6
- ✓ **STATE-01: Per-device state tracking** — `last_preset` written to `state.json` per device after every apply; `rig plan` reports VERIFY (not CHANGED) for already-applied presets; VERIFY-status actions skip device.apply() entirely — v1.6
- ✓ **MC6-01: Clear SysEx flash persistence** — `clear_preset_messages()` defaults to `save=True` (0x7F byte), matching MC6 web UI byte-for-byte; power-cycle regression eliminated — v1.6
- ✓ **PLAN-01/02: Per-parameter plan diffs** — `ParamDiff(name, before, after)` model on `DeviceAction.param_diff`; `rig plan` shows `gain: 5.0 → 8.0` per control; cold-start shows `?: 8.0`; JSON output includes full diff structure; unchanged params suppressed — v1.6
- ✓ **APPLY-01: Skip analog prompt for matched state** — VERIFY-status analog actions print `✓ device: already set to 'preset'` and return without calling device.apply() or showing a prompt — v1.6
- ✓ **APPLY-02: Cross-scene device-only apply** — `apply_plan(device_filter=...)` skips non-matching devices; `rig apply --device <id>` applies that device across all scenes; controller phase gated when device_filter set — v1.6

### Active

- [ ] **SCENE-01**: Scenes are defined at the top level of `rig.yaml`, not embedded in controller device config; a rig without a controller can define and apply scenes
- [ ] **STATE-02**: `state.json` carries a `schema_version` field; `read_state()` migrates older files forward on load; missing version treated as v0
- [ ] **PKG-07**: Plugin authoring guide (`PLUGIN-AUTHORING.md`) covering Device Protocol, entry points, `from_raw_yaml`, setup/apply/edit lifecycle, with a minimal working example plugin skeleton
- [ ] **PKG-08**: All 5 packages published to PyPI; GitHub Actions CI publishes on `v*` tags; `pip install rig rig-chasebliss` works from scratch
- [ ] **PKG-09**: Reference third-party plugin (`rig-neuraldsp`) in its own repo demonstrating the full plugin authoring contract for Neural DSP Quad Cortex
- [ ] **DOC-01**: Formal `rig.yaml` schema reference documenting every field, type, required/optional status, and validation rules per device type

### Out of Scope

| Feature | Reason |
|---------|--------|
| HX Stomp interactive editing | Requires MIDI SysEx parsing; Phase 28 stub prints 'future milestone' message |
| Full HX SysEx read/write via MIDI (#3) | Requires MIDI SysEx parsing complexity — future milestone |
| `rig edit` for controllers (MC6) | MC6 editing is a different domain (bank/switch config, not CC values) — defer |
| HX MIDI channel configurability (#4) | Current hardcoded channel works — defer |
| Complex MC6 workflows (next page, MIDI clock, etc.) (#6) | Low-priority — defer |
| Module-level READMEs (#9) | Nice to have, not blocking |
| MC6 clear message emulation (#17) | ✓ Shipped in v1.6 (Phase 31) |
| Default preset values (#19) | Low-priority tech task |
| UI (#18) | Speculative — not planned |
| CI independent package publishing | Low-priority infra — local `uv` workflow sufficient for now |

## Next Milestone: v2.0 — Platform Foundations

**Goal:** Scene decoupling + PyPI publishing + plugin authoring guide = a shareable platform. The codebase is now correct and reliable (v1.6); v2.0 makes it extensible and distributable.

**Phases:** 34 (First-Class Scenes) → 35 (State Schema Versioning) → 36 (Plugin Authoring Guide) → 37 (PyPI Publishing + CI) → 38 (YAML Config Schema Docs) → 39 (Reference Third-Party Plugin)

## Current State

Phases 1–33.1 shipped across v1.0–v1.6 (7 milestones). Next milestone: v2.0 Platform Foundations.

**Milestone v1.6 shipped 2026-06-24:** 5 phases (29-33.1), 5 plans, 399 tests pass. Fixed CC catalog mismatch, per-device state tracking, MC6 clear SysEx flash persistence, per-parameter plan diffs, analog apply skip for matched state, and cross-scene device-only apply.

## Context

- **v1.6 shipped 2026-06-24**: 5 phases (29–33.1), 5 plans, ~10,961 LOC across all packages. 399 tests pass.
- **v1.5 shipped 2026-06-17**: 4 phases (25–28), 4 plans, 2,261 LOC in `packages/rig/src/`. 367 tests pass.
- **v1.4 shipped 2026-06-17**: 5 phases (20–24), 5 plans, 8,344 LOC Python across all packages
- **v1.3 shipped 2026-06-10**: 6 phases (14–19), 6 plans, 1,023 LOC in `rig_chasebliss/` package
- **v1.2 shipped 2026-06-08**: 5 phases (9–13), 8 plans, 7,349 LOC Python across all packages
- **v1.1 shipped 2026-06-07**: 3 phases (6–8), 8 plans
- **v1.0 shipped 2026-06-07**: 5 phases, 17 plans
- Config repo layout (current): single `rig.yaml` with inline devices, presets, and scenes
- State persisted at `.rig/state.json` in the config repo — tracks what has been applied to physical devices
- Plugin discovery: `importlib.metadata.entry_points('rig.devices')` — install a package, it appears; uninstall, it disappears
- `rig plan` is the read-only preview step; `rig apply` is the commit step — clean separation enforced by no-MIDI-in-plan constraint
- Type system (v1.4): single `Device` Protocol; concrete plugin config types; `Preset` Protocol; `DeviceApplyContext` sole apply context; `DeviceType` + `ActionStatus` StrEnums at all call sites
- CBA catalog auto-population: device YAML with `config.model: <Model Name>` auto-populates controls from catalog; explicit YAML controls take precedence
- Editor protocol (v1.5): `EditorProtocol` + `EditContext` in `plugin.py`; `isinstance` dispatch in CLI; CBA live CC editor, analog key-value editor, HX stub deferred;
- HX Stomp interactive editing intentionally deferred — no live MIDI SysEx read/write support yet; flagged as future milestone
- Known tech debt (resolved in v1.5): `AnalogApplier` `ConfirmationIO` gap closed in Phase 25 — all applier paths use `ConfirmationIO` Protocol

## Constraints

- **Tech stack**: Python 3.13, uv, Typer, Pydantic, Mido + rtmidi — no changes to core dependencies
- **MIDI**: No MIDI interaction in the `plan` command — plan is read-only against state.json
- **Protocol-first**: New abstractions use `Protocol` classes, not ABC inheritance
- **Side project velocity**: Ship working features; avoid over-engineering for hypothetical future frontends

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HXStompPreset has no block-level detail | Block parsing is a future concern; PC message + .hlx reference is sufficient for scenes | ✓ Good |
| Decouple engine before adding plan command | Clean seam makes plan testable and apply testable independently | ✓ Good — Phase 5 plan tests run without hardware |
| Plan command is read-only (no MIDI) | Separation of concerns; apply is the explicit commit step | ✓ Good |
| Three narrow Protocols over one fat interface | `ConfirmationIO`, `StateWriter`, `MidiConnectionIO` are each independently swappable | ✓ Good |
| `DeviceGraph` for topology ordering in `rig plan` | MC6 must be configured after all scenes it references | ✓ Good |
| `detect_cba_setup` forward-looking (all 3 phases in one call) | Single `rig apply` converges fresh CBA device; no re-detection loop | ✓ Good |
| `Device.plan()` / `Device.diff()` as forward stubs (NotImplementedError) | Phase 4 laid the Protocol; Phase 5 wires plan through `compute_plan`, not device methods | ⚠️ Revisit — stubs are dead code in current architecture |
| `Rig.scenes` as property not field | Scenes live in controller config; flat field was a historical compat shim — property aggregates from controllers, cleaner domain model | ✓ Good — v1.3 |
| Single `_get_preset_number` for all preset types | HX-specific branch in `compute.py` was dead code — `HXStompPreset.preset_number` works the same way as `DigitalPreset`; unified lookup reduces branching | ✓ Good — v1.3 |
| Entry points as sole discovery path (no code-level fallback) | Eliminates import-time coupling; enables third-party plugins without core changes | ✓ Good — v1.1 |
| Device-level MIDI lifecycle (`Device.setup()` owns connection) | Cleaner separation; engine doesn't need to know which devices need MIDI setup | ✓ Good — v1.1 |
| `MidiConnectionIO` Protocol removed entirely | Once devices own MIDI setup, the Protocol has no remaining purpose — remove rather than leave empty | ✓ Good — v1.1 |
| CBA-04 + CBA-01 + CBA-02 + CBA-03 grouped in Phase 14 | Single phase avoids partial state — `Control.default` field is prerequisite for complete catalogs | ✓ Good — v1.3 |
| Validation (Phase 15) before reset (Phase 16) | Both consume catalog controls; validation precedes any action that touches the device | ✓ Good — v1.3 |
| Imperative validation in apply(), not Pydantic model_validator | Catalog lookup at construction time would couple model layer to plugin | ✓ Good — v1.3 |
| Auto-populate only when controls list is empty | Explicit YAML controls always take precedence over catalog lookup | ✓ Good — v1.3 |
| Manufacturer hardcoded as "Chase Bliss Audio" in from_raw_yaml() | This is the CBA plugin — model is the only variable discriminator needed | ✓ Good — v1.3 |
| Phase 20 bundles all zero-dependency quick wins | TYPE-04, TEST-01, QUAL-01, QUAL-02 share no intra-group dependencies; batching reduces phase count without coupling risk | ✓ Good — v1.4 |
| TYPE-02 and TYPE-03 in same phase | Concrete plugin config types and Preset Protocol are co-dependent at the boundary; splitting leaves a half-typed codebase | ✓ Good — v1.4 |
| TYPE-01 (retire legacy Device model) isolated | Most impactful change; depends on Phase 21 being complete; isolated blast radius makes phase easy to verify | ✓ Good — v1.4 |
| TEST-02 bundled with TYPE-05 | stdin-capture test failures entangled with dual ApplyContext types; fixing context first gives correct ConfirmationIO foundation | ✓ Good — v1.4 |
| SkipValidation[list[Preset]] for MC6Device.presets | Pydantic cannot validate list[Protocol] at runtime (raises SchemaError); SkipValidation preserves typed annotation for static analysis | ✓ Good — v1.4 |
| ActionStatus(StrEnum) in models.py, not engine/plugin.py | Plan models are a separate concern from apply-time contracts (DeviceApplyContext lives in plugin.py) | ✓ Good — v1.4 |
| Phase 24 inserted to close audit gaps | v1.4 audit found 3 gaps (missing Phase 21 VERIFICATION.md, MC6 list[Any], QUAL-01 raw-string assignment sites); gap-close phase keeps milestone clean | ✓ Good — v1.4 |
| IO-01/IO-02 in their own phase (Phase 25) | Isolated, low-risk fix; folding into Phase 26 would obscure cleanup and make rollback harder | ✓ Good — v1.5 |
| PRESET-01/02/03 grouped in Phase 26 | Three requirements are a single coherent feature; cannot be partially delivered | ✓ Good — v1.5 |
| EDIT-01 folded into Phase 27 | Protocol extension has no observable behavior on its own; keeping Protocol + CLI + YAML writer together makes the first phase where rig edit runs end-to-end | ✓ Good — v1.5 |
| EDIT-04/05 kept in Phase 27 with CLI | YAML writer is the most novel piece but inseparable from save/discard lifecycle | ✓ Good — v1.5 |
| EDIT-03/06 in Phase 28 | Plugin implementations depend on Phase 27 Protocol and CLI being stable; isolated blast radius | ✓ Good — v1.5 |
| Unbounded retry loop in AnalogDevice.apply() | Matches original prompt_analog() behavior; no max-retry limit added | ✓ Good — v1.5 |
| Validation order: D-04 → D-05 → D-06 before MidiManager() | Pre-MIDI validation ensures no port opened on error; security mitigation T-26-01/03 | ✓ Good — v1.5 |
| EditContext fields ordered matching DeviceApplyContext | Consistency; config_path, dry_run, confirmation_io, rig, then midi | ✓ Good — v1.5 |
| EditContext.midi as optional last field | CC-based plugins need it; analog/hx don't; None default keeps backward compat | ✓ Good — v1.5 |
| Catalog constants at module level (not class-level) | Constants like `MOOD_MKII_WET_BYPASS_CC` are test-only aids; YAML remains the runtime truth; module-level keeps them importable without instantiation | ✓ Good — v1.6 |
| `ActionStatus.VERIFY` unified across all device types | No device-type-specific status; all devices use the same `VERIFY` status when state matches — simpler rendering and apply logic | ✓ Good — v1.6 |
| `clear_preset_messages()` defaults `save=True` | Aligns with sibling SysEx functions and MC6 web UI; RAM-only is the explicit opt-in, not the default; eliminates power-cycle regression | ✓ Good — v1.6 |
| `ParamDiff` on `DeviceAction`, not a separate data structure | Param diffs are a property of the action, not a separate query; zero overhead for HX/no-change devices (empty list by default) | ✓ Good — v1.6 |
| `device_filter` param on `apply_plan()` (not a new engine function) | Single entry point with optional filter is simpler than `apply_device()` alongside `apply_plan()`; gate on `action.device != device_filter` is readable | ✓ Good — v1.6 |
| Phase 33.1 inserted for Apply-01/02 (not reusing Phase 33 slot) | Phase 33 original plan was stale; creating 33.1 preserves clean planning artifact history without overwriting the original 33 research docs | ✓ Good — v1.6 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-24 — v1.6 milestone complete*
