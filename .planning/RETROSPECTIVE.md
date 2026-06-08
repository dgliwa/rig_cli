# Retrospective: rig-cli

## Milestone: v1.0 — I/O Decoupling & Plugin Architecture

**Shipped:** 2026-06-07
**Phases:** 5 | **Plans:** 17

### What Was Built

- CBA tech-debt cleaned — `mark_preset_saved` helper + public `detect_cba_setup` API
- Engine I/O fully decoupled via three Protocol ports (`ConfirmationIO`, `StateWriter`, `MidiConnectionIO`) with in-memory fakes for testing
- MC6 / Controller modeled as first-class `ControllerConfig` device in discriminated union
- `DeviceGraph` for DFS topology ordering — `Rig.apply_order()` drives apply and plan sequencing
- All appliers migrated to `Device` Protocol + `PluginRegistry` — engine has zero direct applier imports
- `rig plan` command shipped: graph-ordered output, before/after diff, exit codes, JSON mode, scene filter, cold-start warning
- CBA single-apply convergence — one `rig apply` brings a fresh device through all 3 setup phases

### What Worked

- **Protocol-first design**: Defining the seam as a `Protocol` before implementing both sides kept the decoupling clean and the test fakes minimal
- **Phase sequencing**: Decoupling I/O before adding the plan command meant Phase 5 plan tests ran without hardware from the start
- **Small plan granularity**: 17 plans across 5 phases kept each execution atomic and easy to reason about
- **Nyquist validation**: Retroactive validation tests caught one real gap (MC6 banks path in Phase 4) that would have been a silent runtime failure

### What Was Inefficient

- Phase 3 was replanned mid-stream — original goal was "plan command" but domain model gaps (missing Controller type, no graph) required a full refactor first; the replanning added a phase
- `Device.plan()` / `Device.diff()` stubs were added in Phase 4 but never used — forward stubs that became dead code when Phase 5 wired plan through `compute_plan` instead
- Some SUMMARY.md one-liners from gsd-tools extraction were code-review rule citations, not accomplishment descriptions — extraction quality could be improved

### Patterns Established

- `ports.py` as the canonical home for I/O Protocol definitions
- `DeviceApplyContext` dataclass (not Pydantic) for runtime-only apply context — Pydantic for domain data, dataclass for context objects
- `tests/fakes.py` as the single module for in-memory test doubles
- Plugin registration at module level in `devices.py` — no runtime magic, explicit wiring

### Key Lessons

- **Topology matters before behavior**: The graph-based ordering (DeviceGraph) was needed before the plan command could produce correct output — establishing the model first saved rework
- **Forward stubs add confusion**: `Device.plan()` / `Device.diff()` raising `NotImplementedError` is now misleading; prefer not adding stubs until they're wired
- **Protocol ports over patching**: Replacing `patch("builtins.input")` with `InMemoryPromptAdapter` made tests deterministic and readable — worth the upfront Protocol design cost

### Cost Observations

- Sessions: multiple across 7 days
- Notable: Phase 5 was the most complex (6 plans) but executed cleanly because all infrastructure from Phases 2-4 was in place

---

## Milestone: v1.1 — Package Extraction & Plugin Isolation

**Shipped:** 2026-06-07
**Phases:** 3 (6–8) | **Plans:** 8

### What Was Built

- `rig.devices` entry point group declared in core; `get_registry()` discovers plugins via `importlib.metadata.entry_points()` — zero hard plugin dependencies
- All 4 device plugins (`rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar`) extracted as independently installable pip packages with own `pyproject.toml`
- `Device.setup()` now owns MIDI connection lifecycle; Phase -1 engine loop removed
- HXStompDevice and full ChaseBlissDevice created in their respective packages with device-level MIDI
- 7 dead core files deleted; plugins own their full implementations including prompts

### What Worked

- **Clear sequencing**: Phase 6 (discovery infra) → Phase 7 (wire plugins + MIDI) → Phase 8 (delete dead code) was a natural execution order with no backtracking
- **Protocol removal as signal**: Deleting `MidiConnectionIO` entirely (rather than leaving it empty) was the right call — confirmed the seam was clean
- **Audit-first close**: The milestone audit clearly enumerated what was done and what was deferred — made this close conversation fast

### What Was Inefficient

- Phase 8 executed without SUMMARY.md files — GSD workflow gap; execution was done outside the standard gsd-execute-phase flow
- No VERIFICATION.md for any v1.1 phase — same gap; made audit rely on ad hoc evidence
- First milestone close attempt was reverted (commit e35bc97) — likely a partial run; clean state required manual inspection before retry

### Patterns Established

- Plugin packages as the canonical unit of device ownership: device class + entry point + prompts + tests all live in the plugin package
- `Device.setup()` contract: all MIDI connection happens here, before the engine dispatches `apply()`
- `tests/fakes.py` extended with `_fake_midi_connect` helper for per-device MIDI testing without hardware

### Key Lessons

- **Remove, don't empty**: When a Protocol or abstraction has no remaining purpose, delete it rather than leaving an empty shell — the empty `MidiConnectionIO` would have been confusing
- **Phase 8 cleanup phases work best when run inline**: Dead code deletion is mechanical; running it outside gsd workflow means no SUMMARY/VERIFICATION artifacts — worth using the standard flow even for cleanup
- **Entry point discovery is an all-or-nothing switch**: Once the registry is entry-point driven, there's no fallback — a missing `pip install` gives a silent empty registry rather than an error. Worth documenting this for the plugin authoring guide

### Cost Observations

- Sessions: 1 intensive day (same day as v1.0)
- Notable: All 3 phases executed in a single session sprint — rapid because the v1.0 plugin architecture scaffolding was already in place

---

## Milestone: v1.2 — Cleaner Core

**Shipped:** 2026-06-08
**Phases:** 5 (9–13) | **Plans:** 8

### What Was Built

- Single `rig.yaml` replaces multi-file config repo — device list order defines signal chain; `SignalChainPosition` removed; presets inline per device
- All plugin config types evicted from core — `Device.config: Any`; discriminated union gone; plugin device models own their config types
- Loader rewritten — `load_rig()` parses one file; scenes extracted from controller device config; plugin dispatch by `config.type` entry point key
- Dead code sweep — `rig generate mc6` command removed; `composes` validation removed; all `TODO: 1.2` markers cleared; multi-file compat paths deleted
- `Rig.scenes` converted from stored field to `@property` over controller devices; `is_hx` branch removed from `compute.py`; all preset lookups unified through `_get_preset_number`

### What Worked

- **Atomic wave structure in Phase 9**: Breaking core model cleanup into 4 focused waves (Scene/Rig → signal chain → plugin configs → cleanup) let each wave be committed and verified independently — no big-bang refactor failure mode
- **Loader rewrite as a single plan**: Phase 10's single plan approach worked well because the design was fully specified upfront (single-file schema documented in PLAN.md) before any code was touched
- **Phase 12 as dedicated deferred-items cleanup**: Explicitly scoping a phase for removing deferred items rather than leaving them as tech debt ensures they get done

### What Was Inefficient

- Phase 11 and Phase 13 executed outside the standard gsd-execute-phase flow — no SUMMARY.md artifacts generated (same recurring gap as v1.1 Phases 7/8)
- The v1.3 / v1.2 milestone boundary was blurry — Phase 13 was scoped as v1.3 in the ROADMAP but the REQUIREMENTS.md covered it as v1.2; resulted in closing everything as v1.2 at the end
- Phase 9 Wave 3 had a cross-wave dependency surprise (generator.py needed to be updated in Wave 1 due to `rig.mc6` removal) — cross-wave dependencies are harder to catch in planning than cross-phase ones

### Patterns Established

- `Device.config: Any` with dict-aware access pattern — `config.get("key") if isinstance(config, dict) else getattr(config, "key", None)` handles both loader-constructed dicts and plugin-constructed models
- Single `rig.yaml` as the canonical config schema — no multi-file layout support to maintain
- `Rig.scenes` as a computed property over controller device configs — not a stored field

### Key Lessons

- **Scope creep at milestone boundaries costs audit overhead**: When a "v1.3" phase is really just the tail of v1.2 work, either fold it into v1.2 from the start or explicitly create a new REQUIREMENTS.md for the new milestone scope — half-measures create confusion at close time
- **`Device.config: Any` is a sharp tool**: Removing the discriminated union simplified core but pushed isinstance checks into every plugin that accesses config. Worth documenting the dict/model dual-access pattern as an explicit convention
- **Wave-based execution for model refactors**: Breaking a large model cleanup into 4 sequential waves (each with its own commit) worked much better than trying to do it all at once

### Cost Observations

- Sessions: 1 intensive day (2026-06-08)
- Plans: 8 total across 5 phases
- Notable: Phase 9 was the most complex (4 plans, 45 min for Wave 3 alone) because it required untangling the discriminated union from core while keeping all plugin consumers working

---

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 | v1.2 |
|--------|------|------|------|
| Phases | 5 | 3 | 5 |
| Plans | 17 | 8 | 8 |
| LOC (Python) | 3,625 | ~20,658 | 7,349 |
| Timeline | 7 days | 1 day | 1 day |
| Replanning events | 1 (Phase 3) | 0 | 0 |
| Missing SUMMARY.md | 0 | 2 | 2 |
