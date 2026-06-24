# Milestones

## v1.6 Correctness & State Reliability (Shipped: 2026-06-24)

**Phases completed:** 5 phases (29-33.1), 5 plans
**Files changed:** 82 files, 9,772 insertions / 100 deletions
**Total Python LOC:** ~10,961 (packages/)
**Timeline:** 2026-06-17 → 2026-06-24 (7 days)
**Test suite at close:** 399 passed, 0 failures

**Key accomplishments:**

- Fixed Mood MkII CC swap (`wet_bypass=102`, `loop_bypass=103`); named catalog constants replace magic numbers in all tests — CAT-01 satisfied
- Fixed `state.json` per-device `last_preset` tracking after every apply; `rig plan` now shows VERIFY (not CHANGED) for already-applied presets — STATE-01 satisfied
- Fixed MC6 clear SysEx: `clear_preset_messages()` defaults to `save=True` (flash persist), matching MC6 web UI byte-for-byte — MC6-01 satisfied
- Added `ParamDiff` model: `rig plan` shows `gain: 5.0 → 8.0` per control, cold-start shows `?: 8.0`; JSON includes full diff structure — PLAN-01, PLAN-02 satisfied
- Analog apply skips manual prompt when state already matches desired preset; `--device <id>` applies cross-scene without `--preset` — APPLY-01, APPLY-02 satisfied
- Post-close blocker fix: MC6 controller-only apply now persists to `state.json` (commit a098afb)

---

## v1.5 milestone (Shipped: 2026-06-18)

**Phases completed:** 4 phases, 4 plans, 7 tasks

**Key accomplishments:**

- ConfirmationIO fully threaded through AnalogDevice.apply() — last raw input() call eliminated from all applier paths; prompt_analog() deleted; 3 tests migrated to InMemoryPromptAdapter
- `apply_device_preset()` engine function + `--device`/`--preset` CLI flags for isolated single-device preset apply without scene-based plan.
- EditorProtocol and EditContext protocol contract with ruamel.yaml round-trip write-back and `rig edit` CLI command dispatched via isinstance check on skeleton-stubbed CBA and HX Stomp devices.

---

## v1.0 I/O Decoupling & Plugin Architecture (Shipped: 2026-06-07)

**Phases completed:** 5 phases, 17 plans, 11 tasks

**Key accomplishments:**

- Consolidate CBA state mutations through `mark_preset_saved` and promote `_detect_cba_setup` to a public API to eliminate cross-module private symbol references.
- 1. [Rule 1 - Bug] Plan verify step used invalid single-char side_effect values
- 1. [Rule 3 - Blocking] Global editable install shadows worktree source during pytest
- 1. [Rule 1 - Bug] Updated all affected test _make_rig() helpers and loader.py
- Device Protocol with id/name/config properties replaces DevicePlugin; DeviceApplyContext dataclass added for apply-time context; PluginRegistry gains model-class registration for P3 loader dispatch.
- Four concrete Device Protocol types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) as Pydantic models migrating applier logic into apply() methods, registered in a module-level default PluginRegistry.
- Plugin migration complete: loader.py dispatches via registry, apply.py routes through device.apply(DeviceApplyContext), old applier files deleted — adding a new device type now requires only plugin registration.
- 1. [Rule 1 - Bug] Cold-start warning printed before JSON mode check
- T9 — apply_plan() signature change
- Made `detect_cba_setup()` forward-looking so a single `rig apply` converges a fresh CBA device through all 3 phases, and removed the `_enqueue_new_actions` re-detection from `ChaseBlissApplier`.

---

## v1.1 Package Extraction & Plugin Isolation (Shipped: 2026-06-07)

**Phases completed:** 3 phases (6–8), 8 plans
**Files changed:** 68, 3,466 insertions / 1,826 deletions
**Total Python LOC:** ~20,658

**Key accomplishments:**

- Declared `rig.devices` entry point group; `get_registry()` discovers plugins via `importlib.metadata.entry_points()` — zero hard plugin dependencies in core
- Removed hardcoded `default_registry` — entry points are the single discovery path; `rig` works with no plugins installed and gains devices when plugins are `pip install`-ed
- Wired all 4 plugin packages (`rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar`) as independently installable pip packages with own `pyproject.toml`
- Created HXStompDevice and full ChaseBlissDevice with device-level MIDI lifecycle; engine no longer manages MIDI connections
- Removed Phase -1 MIDI connection loop from `apply.py` — `Device.setup()` is now the sole MIDI connection mechanism
- Deleted 7 dead core files (mc6.py, chase_bliss.py, appliers/chase_bliss.py, catalog, controller model) — plugins own their full implementations

**Known deferred items at close:** 0 (see STATE.md Deferred Items)

---
## v1.2 Cleaner Core (Shipped: 2026-06-08)

**Phases completed:** 5 phases (9–13), 8 plans
**Files changed:** 82, 5,588 insertions / 2,238 deletions
**Total Python LOC:** 7,349

**Key accomplishments:**

- Single `rig.yaml` replaces multi-file config repo — device list order defines signal chain; `SignalChainPosition` and `signal_chain.py` deleted; presets inline per device
- All plugin config types evicted from core (`ManualConfig`, `MidiConfig`, `ChaseBlissConfig`, `ControllerConfig`, `Control`, `ControlType`) — `Device.config: Any`
- Loader rewritten for single-file schema — `load_rig()` parses one `rig.yaml`; plugin dispatch by `config.type` entry point key; scenes extracted from controller device config
- Dead code sweep — `rig generate mc6` command removed; `composes` validation removed; all `TODO: 1.2` markers cleared; multi-file compat paths deleted
- `Rig.scenes` converted from stored field to `@property` over controller devices; `is_hx` branch removed from `compute.py`

**Known deferred items at close:** 0

---
## v1.3 Chase Bliss Pedal Support (Shipped: 2026-06-10)

**Phases completed:** 6 phases (14–19), 6 plans
**Files changed:** 83, 5,919 insertions / 1,304 deletions
**Python LOC in rig-chasebliss package:** 1,023

**Key accomplishments:**

- **CBA Catalog Expansion** — Added `Control.default` field, complete Wombtone MkII (CC14-21), Brothers AM (24 controls), and Mood MkII (47 controls) catalogs
- **Preset Parameter Validation** — `validate_cc_params()` rejects unknown names and out-of-range values with `ValidationError` before pedal interaction
- **Reset-to-Defaults** — `_send_reset_ccs()` per-preset reset of all resettable controls before preset CC sends, excluding footswitches/utilities
- **Catalog Auto-Population** — `ChaseBlissConfig.model` field + `get_controls()` wired into `from_raw_yaml()` — device YAML with a model name auto-populates controls
- **Verification & Validation Docs** — Created VERIFICATION.md and VALIDATION.md for phases 14-18 (10 files), closing all audit gaps
- **Full test suite:** 300 passed, 0 failures across all v1.3 changes

**Known deferred items at close:** 2 (see STATE.md Deferred Items — validation state-gating, reset CC connected_devices gate)

---

## v1.4 Architecture & Type Integrity (Shipped: 2026-06-17)

**Phases completed:** 5 phases (20-24), 5 plans
**Files changed:** 94, +5,144 / -5,606 lines
**Total Python LOC:** 8,344 (packages/)
**Timeline:** 2026-06-10 → 2026-06-17 (7 days)

**Key accomplishments:**

- Retired `Device(BaseModel)` legacy model from `models/device.py`; `Rig.devices` typed against Protocol end-to-end — no `hasattr` guards, no `cast(Any)` in engine or loader
- All 4 plugins carry concrete config types (`AnalogConfig`, `HXStompConfig`, `ChaseBlissConfig`, `MC6Config`); YAML construction validates against concrete type
- `Preset` Protocol defined in core; `MC6Device.presets: SkipValidation[list[Preset]]` eliminates the last `list[Any]` field in the plugin boundary
- Dead `plan()`/`diff()` stubs removed from Protocol and all 4 plugin device files; deleted 8 stub tests
- `appliers/base.py` deleted — legacy `ApplyContext` dataclass retired; `DeviceApplyContext` is the sole apply context type in `apply.py`
- 3 stdin-capture tests now pass without `-s`; `ConfirmationIO.prompt()` threaded through all 4 CBA interaction functions; `InMemoryPromptAdapter` replaces `builtins.input` monkeypatching
- `ActionStatus(StrEnum)` added; `DeviceAction` fully enum-typed (`device_type: DeviceType`, `status: ActionStatus`) — no raw string literals at any construction site
- Root `tests/` directory deleted (9 import errors eliminated); 309 passed, 0 failures

**Known deferred items at close:** 1 (AnalogApplier bypasses `ConfirmationIO` — `prompt_analog()` still calls `input()` directly; analog parity deferred to v1.5)

---
