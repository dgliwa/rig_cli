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

## Milestone: v1.3 — Chase Bliss Pedal Support

**Shipped:** 2026-06-10
**Phases:** 6 (14–19) | **Plans:** 6

### What Was Built

- CBA Catalog Expansion — `Control.default` field, complete Wombtone MkII (12 controls, CC14-21), Brothers AM (28 controls, 8 knobs + 3 toggles + 15 dipswitches + 2 footswitches), Mood MkII (47 controls, backfilled CC24-29, CC31-33, CC52; CC102/103 name fix)
- Preset Parameter Validation — `validate_cc_params()` rejects unknown names and out-of-range values with grouped `ValidationError` before any pedal interaction
- Reset-to-Defaults — `_send_reset_ccs()` per-preset CC reset of all resettable controls (non-None defaults) before preset CC sends, excluding footswitches/utilities
- Catalog Auto-Population — `ChaseBlissConfig.model` field + `get_controls()` wired into `from_raw_yaml()` so device YAML with a model name auto-populates controls
- Verification & Validation Docs — Created VERIFICATION.md and VALIDATION.md for phases 14-18 (10 files), closing all audit procedural gaps

### What Worked

- **Phase 18 as a targeted gap-closure phase**: The single-purpose phase (add model field + wire get_controls) was exactly right — narrow scope, fast execution, clear success criteria
- **Milestone audit caught real gaps**: The audit identified that `get_controls()` was defined but had zero production callers — a genuine wiring gap that would have made CBA-01/CBA-02 catalogs inert. The audit also caught all 5 missing VERIFICATION.md/VALIDATION.md files
- **Phase 19 documentation phase**: Creating all 11 missing documentation files in a single documentation-only phase was efficient — no code changes needed, just thorough verification evidence
- **All 6 CBA requirements satisfied**: Despite the milestone expanding from 3 to 6 phases, all requirements shipped with full test coverage

### What Was Inefficient

- **Catalog tests left stale after Phase 14**: Phase 14 expanded Mood MkII from 7 to 47 controls but the existing test assertions weren't updated until Phase 17 — a 3-phase gap that required a dedicated fix phase. A post-phase cross-phase test sweep would have caught this immediately
- **`get_controls()` defined but unwired in Phase 14**: The catalog function was written and tested in Phase 14 but had no production callers until Phase 18 — a 4-phase gap between definition and wiring. The plan assumed `get_controls()` would be wired at the entry point, but that wiring path wasn't plumbed until the loader schema rewrite (v1.2) was deployed
- **No VERIFICATION.md/VALIDATION.md created during execution**: All 5 phases were implemented without formal verification documentation — a recurring GSD workflow gap across all milestones. Phase 19 closed this retroactively
- **STATS.md never completed**: Performance metrics columns remain empty across all phases — missed opportunity for velocity tracking

### Patterns Established

- `ChaseBlissConfig.model` + `from_raw_yaml()` catalog auto-population pattern — explicit YAML controls take precedence; catalog is the fallback
- Retroactive documentation phases for closing audit gaps — Phase 19 served as the canonical example of a docs-only gap-closure phase with measurable success criteria
- `_send_reset_ccs()` as a distinct inner function in `_build_preset()` — separated the reset concern from the preset CC send concern within the same method

### Key Lessons

- **Test every new function immediately**: `get_controls()` was tested in isolation in Phase 14 but its wiring should have been verified right away — the 3-phase gap between function definition and integration test was too long. Either wire in the same phase or add an integration-level test with mocked entry point discovery
- **Documentation phases are cheap insurance**: Adding VERIFICATION.md and VALIDATION.md during execution takes < 30 seconds per phase — the retroactive docs phase took 5 minutes for 11 files because all the evidence was already in the code. Doing it inline during execution would have been faster
- **Audit gaps reveal blind spots**: The milestone audit found all the procedural gaps that every previous milestone also had — the workflow was systematically not creating validation artifacts. Fixing the workflow (creating VERIFICATION.md/VALIDATION.md during execution) would prevent this for future milestones
- **Narrow gap-closure phases work**: Phases 17 (test fix), 18 (wiring), and 19 (docs) had single responsibilities — each was < 5 minutes of execution time. This granularity made them easy to reason about, commit, and verify

### Cost Observations

- Sessions: 2 sessions across 3 days (2026-06-08 to 2026-06-10)
- Plans: 6 total across 6 phases
- Notable: Phase 14 catalog expansion was the highest value (3 complete catalogs in one commit); Phase 19 docs closure was the fastest (11 files in < 5 min)

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 | v1.2 | v1.3 |
|--------|------|------|------|------|
| Phases | 5 | 3 | 5 | 6 |
| Plans | 17 | 8 | 8 | 6 |
| LOC (Python) | 3,625 | ~20,658 | 7,349 | 1,023 |
| Timeline | 7 days | 1 day | 1 day | 3 days |
| Replanning events | 1 (Phase 3) | 0 | 0 | 0 |
| Missing SUMMARY.md | 0 | 2 | 2 | 0 |
| Missing VERIFICATION.md | N/A | N/A | N/A | 0 (closed in Phase 19) |

| Metric | v1.0 | v1.1 | v1.2 |
|--------|------|------|------|
| Phases | 5 | 3 | 5 |
| Plans | 17 | 8 | 8 |
| LOC (Python) | 3,625 | ~20,658 | 7,349 |
| Timeline | 7 days | 1 day | 1 day |
| Replanning events | 1 (Phase 3) | 0 | 0 |
| Missing SUMMARY.md | 0 | 2 | 2 |
