---
phase: 04-plugin-migration
verified: 2026-06-06T05:04:13Z
status: gaps_found
score: 11/12 must-haves verified
overrides_applied: 0
gaps:
  - truth: "MC6Device.apply() delegates to MC6Applier.apply_banks logic using DeviceApplyContext"
    status: partial
    reason: "MC6Device.apply() uses self.banks (always empty [] when device is loaded from real YAML via loader) instead of self.config.banks. apply.py gates on mc6_device.config.banks correctly, but MC6Device.apply() ignores config.banks and reads self.banks — which is never populated by loader. In production (with real MIDI hardware), MC6 programming silently returns 'skipped' instead of executing. Tests mask this by constructing MC6Device with explicit banks= kwarg or by using the old Device model for mc6 in TestDevicePluginRouting."
    artifacts:
      - path: "src/rig/engine/devices.py"
        issue: "MC6Device.apply() line 301: `if not self.banks or ctx.midi is None` — self.banks is the instance field (default=[]), not config.banks. Banks from YAML land in self.config.banks but apply() never reads it."
    missing:
      - "MC6Device.apply() should read banks from self.config.banks (or ctx.rig.controller.config.banks) not self.banks"
      - "A test verifying that an MC6Device loaded from the sample_rig fixture (where banks are in config) actually executes the programming path (not just returns skipped)"
---

# Phase 4: Plugin Migration Verification Report

**Phase Goal:** Migrate existing appliers (CBA, MC6, HX Stomp, Analog) to the plugin architecture; CLI and engine route through registry
**Verified:** 2026-06-06T05:04:13Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Note on Requirement IDs

The verification request cited DEC-01 through DEC-07 as Phase 4 requirement IDs. However, REQUIREMENTS.md traceability maps DEC-01 through DEC-07 to **Phase 2** (Engine I/O Decoupling), and they are marked Complete there. All three Phase 4 PLAN files (`04-P1-PLAN.md`, `04-P2-PLAN.md`, `04-P3-PLAN.md`) have `requirements: []`. The ROADMAP marks Phase 4 requirements as "TBD." DEC-01 through DEC-07 are verified as already satisfied (Phase 2 completions) and are included in Requirements Coverage for completeness, but they are not Phase 4 work.

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | Device Protocol exists in plugin.py with id, name, config properties and plan/diff/apply methods | VERIFIED | `src/rig/engine/plugin.py` line 41: `class Device(Protocol)` with all required methods and properties |
| 2   | DeviceApplyContext dataclass exists with all required fields (action, state, rig, dry_run, confirmation_io, midi, connected_devices, config_path) | VERIFIED | `src/rig/engine/plugin.py` lines 30-38: all 8 fields confirmed |
| 3   | PluginRegistry has register_model/get_model; get_registry() returns default registry with all four types registered | VERIFIED | `plugin_registry.py` has both methods; `get_registry()` lazy-imports `devices.default_registry`; all four types confirmed by `python -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(r.get_model('manual'))"` |
| 4   | DevicePlugin Protocol removed from plugin.py | VERIFIED | `class DevicePlugin` not found anywhere in src/; test `test_device_plugin_not_importable_from_plugin_module` in test_plugin.py passes |
| 5   | AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device exist as Pydantic BaseModel subclasses with correct fields | VERIFIED | `src/rig/engine/devices.py` — all four classes inherit BaseModel with id, name, config, type, presets fields; plan/diff raise NotImplementedError |
| 6   | AnalogDevice.apply() and MidiDevice.apply() replicate applier logic correctly | VERIFIED | Code traces match AnalogApplier/MidiApplier logic; tests in test_devices.py pass; CBA delegates to _midi_device.apply() which reads from ctx.action not self — delegation works correctly |
| 7   | MC6Device.apply() delegates to MC6Applier.apply_banks logic using DeviceApplyContext | PARTIAL/FAILED | Code is inline (not delegated), but uses `self.banks` which is always `[]` when device is loaded from real YAML. Config banks live in `self.config.banks` which apply() never reads. MC6 programming silently returns "skipped" in production. |
| 8   | loader.py uses registry.get_model(config_type) to parse device YAML | VERIFIED | `src/rig/config/loader.py` line 45: `model_class = get_registry().get_model(config_type)` with ValidationError on unknown type |
| 9   | apply.py routes scene actions through device.apply(ctx) — no get_scene_applier() calls remain | VERIFIED | `apply.py` lines 170-180: `device_ctx = DeviceApplyContext(...)` then `action_result = device.apply(device_ctx)`; grep confirms no `get_scene_applier` or `get_mc6_applier` in src/ |
| 10  | apply.py has no import from rig.engine.appliers.registry | VERIFIED | grep confirms zero matches for `from rig.engine.appliers.registry import` in src/ |
| 11  | Old applier files deleted (analog.py, midi_device.py, mc6.py, registry.py); base.py and chase_bliss.py kept | VERIFIED | `ls src/rig/engine/appliers/` shows only: `__init__.py`, `base.py`, `chase_bliss.py` |
| 12  | All tests pass: uv run pytest tests/ -q | VERIFIED | 238 passed in 0.45s |

**Score:** 11/12 truths verified (1 partial/failed — MC6Device.apply() banks bug)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/rig/engine/plugin.py` | Device Protocol, DeviceApplyContext, PluginContext | VERIFIED | All three exist with correct shapes |
| `src/rig/engine/plugin_registry.py` | PluginRegistry with register_model/get_model, get_registry() | VERIFIED | All present; get_registry() lazy-imports to avoid circular import |
| `src/rig/engine/devices.py` | AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device + default_registry | VERIFIED | 394 lines; all four concrete types and default_registry at module level |
| `src/rig/config/loader.py` | Registry-driven device YAML dispatch via get_model() | VERIFIED | _parse_device() uses get_registry().get_model(config_type) |
| `src/rig/engine/apply.py` | Device-Protocol routing with no direct applier imports | VERIFIED | DeviceApplyContext used for scene loop and MC6 phase; CBA setup deferred per plan |
| `tests/test_devices.py` | Protocol compliance and apply() behavior tests | VERIFIED | Protocol conformance tests + apply() dry_run/confirm/quit tests for all four types |
| `tests/test_plugin.py` | Plugin registry and Device Protocol tests | VERIFIED | Passes; includes DevicePlugin-not-importable test |
| `tests/test_loader.py` | Registry dispatch produces concrete types | VERIFIED | TestRegistryDispatch class with tests for all four config types + unknown type error |
| `tests/test_apply.py` | Device Plugin routing tests | VERIFIED | TestDevicePluginRouting: test_device_apply_called_for_scene_action + test_no_get_scene_applier_import_in_apply |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/rig/config/loader.py` | `src/rig/engine/plugin_registry.py` | `from rig.engine.plugin_registry import get_registry` | VERIFIED | Line 8 of loader.py; used in _parse_device() line 45 |
| `src/rig/engine/apply.py` | `src/rig/engine/plugin.py` | `from rig.engine.plugin import DeviceApplyContext` | VERIFIED | Line 16 of apply.py; DeviceApplyContext constructed at lines 170-179 and 221-230 |
| `src/rig/engine/devices.py` | `src/rig/engine/appliers/analog.py` (logic inlined) | AnalogDevice.apply() replicates AnalogApplier logic | VERIFIED | Logic inlined; analog.py deleted; behavior preserved by tests |
| `src/rig/engine/devices.py` | `src/rig/engine/appliers/midi_device.py` (logic inlined) | MidiDevice.apply() replicates MidiApplier logic | VERIFIED | Logic inlined; midi_device.py deleted; behavior preserved by tests |
| `src/rig/engine/devices.py` | `src/rig/engine/appliers/mc6.py` (logic inlined) | MC6Device.apply() inlines apply_banks logic | PARTIAL | Logic inlined; mc6.py deleted. BUT: apply() uses `self.banks` (always []) instead of `self.config.banks`. Silently skips in production. |
| `src/rig/engine/plugin_registry.py` | `src/rig/engine/devices.py` | `get_registry()` lazy-imports `default_registry` | VERIFIED | Lines 35-37 of plugin_registry.py; avoids circular import |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `MC6Device.apply()` | `self.banks` | MC6Device instance field (default=[]) | No — empty when loaded from YAML | DISCONNECTED |
| `MC6Device` (via loader) | `self.config.banks` | ControllerConfig parsed from YAML | Yes — populated by loader | FLOWING |
| `AnalogDevice.apply()` | `ctx.action.*` | DeviceAction passed at call site | Yes | FLOWING |
| `MidiDevice.apply()` | `ctx.action.*` | DeviceAction passed at call site | Yes | FLOWING |

**Root cause:** MC6Device has two banks data paths. `self.config.banks` is populated by the loader from YAML. `self.banks` is an independent list field that stays `[]`. `MC6Device.apply()` reads `self.banks`, not `self.config.banks`, so the production apply path always evaluates `not self.banks` as True and returns immediately with status="skipped".

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| All four device types importable without circular imports | `python -c "from rig.engine.devices import AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device; print('ok')"` | ok | PASS |
| Registry returns correct model classes for all four types | `python -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(r.get_model('manual'))"` | `<class 'rig.engine.devices.AnalogDevice'>` | PASS |
| Loader produces MC6Device from fixture YAML | Verified programmatically | `type(mc6).__name__ == 'MC6Device'` | PASS |
| MC6Device.apply() processes banks when loaded from real YAML in dry_run | Verified programmatically | Returns `status="skipped"` (WRONG — should print switch info) | FAIL |
| Full test suite passes | `uv run pytest tests/ -q` | 238 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| DEC-01 | Phase 2 (not Phase 4) | ConfirmationIO Protocol defined in ports.py | SATISFIED | `class ConfirmationIO(Protocol)` at line 26 of ports.py |
| DEC-02 | Phase 2 (not Phase 4) | StateWriter Protocol defined in ports.py | SATISFIED | `class StateWriter(Protocol)` at line 57 of ports.py |
| DEC-03 | Phase 2 (not Phase 4) | MidiConnectionIO Protocol defined in ports.py | SATISFIED | `class MidiConnectionIO(Protocol)` at line 65 of ports.py |
| DEC-04 | Phase 2 (not Phase 4) | ApplyContext has confirmation_io field | SATISFIED | `confirmation_io: ConfirmationIO` at line 29 of appliers/base.py |
| DEC-05 | Phase 2 (not Phase 4) | apply_plan accepts state_writer, midi_connection_io | SATISFIED | apply.py lines 53-54: both params present |
| DEC-06 | Phase 2 (not Phase 4) | Scene state only written when at least one confirmed | SATISFIED | apply.py lines 135 and 195: `if any(r.status == "confirmed" ...)` |
| DEC-07 | Phase 2 (not Phase 4) | InMemoryStateAdapter and InMemoryPromptAdapter in fakes.py | SATISFIED | tests/fakes.py lines 21 and 79 |

All DEC requirements belong to Phase 2 and were completed then. No Phase 4-specific requirement IDs exist in REQUIREMENTS.md (ROADMAP.md marks Phase 4 requirements as "TBD").

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/rig/engine/apply.py` | 50, 85, 125 | TODO comments | Info | These are design-level architectural notes ("this is too big", "don't like this on the plan"), not incomplete implementation. All TODOs lack issue references but do not block functionality — marked Info per side-project mode (TODO markers acceptable per global CLAUDE.md). |
| `src/rig/config/loader.py` | 24, 75, 87, 99, 107, 131, 165 | TODO comments | Info | Design-level notes about future cleanup. None block current operation. |
| `src/rig/engine/devices.py` | 228 | `_midi_device: MidiDevice = MidiDevice(id="", name="", config=None)` — class-level attribute with stub id/config | Warning | ChaseBlissDevice delegates apply() to this stub MidiDevice. Works correctly because MidiDevice.apply() reads from ctx.action not from self. The stub id/config are never accessed during apply(). However, the design is fragile and not self-documenting. Pydantic creates fresh instances per ChaseBlissDevice so no shared-state risk. |
| `src/rig/engine/devices.py` | 278, 301 | `banks: list[dict] = []` field on MC6Device never populated by loader | Blocker | MC6Device.apply() uses `self.banks` which is always empty when loaded from YAML. Banks live in `self.config.banks`. This causes MC6 programming to silently return "skipped" in production. |

### Human Verification Required

None identified. All core behaviors are testable programmatically.

### Gaps Summary

One behavioral gap identified:

**MC6Device.apply() banks disconnect.** `MC6Device` has a `banks: list[dict] = []` field that defaults to empty and is never populated by the loader (loader writes banks into `config.banks` via `ControllerConfig`). `MC6Device.apply()` checks `if not self.banks` and returns `"skipped"` immediately when no banks are present — which is always the case in production. The data is there (`self.config.banks`) but apply() reads the wrong attribute.

The fix is a one-liner: change `if not self.banks or ctx.midi is None:` to `if not self.config.banks or ctx.midi is None:` and update the `for bank in self.banks:` loops to `for bank in self.config.banks:` (two places in apply()). A test using `load_rig` against the sample_rig fixture and calling `mc6.apply(ctx)` in dry_run mode would catch this.

This gap is not caught by the existing test suite because: (1) `test_devices.py` constructs `MC6Device(banks=[...])` directly with the `banks` field, (2) `TestDevicePluginRouting` in `test_apply.py` uses the old `Device` model for the mc6 controller (not `MC6Device`), so the MC6 programming path in apply.py is never exercised with a real `MC6Device` instance.

All other phase goals are achieved:
- Device Protocol architecture is complete and structurally sound
- All four concrete types satisfy the Protocol
- loader.py routes through registry for device construction
- apply.py routes scene actions through device.apply(ctx) with no old applier registry imports
- Old applier files (analog.py, midi_device.py, mc6.py, registry.py) deleted
- 238 tests pass

---

_Verified: 2026-06-06T05:04:13Z_
_Verifier: Claude (gsd-verifier)_
