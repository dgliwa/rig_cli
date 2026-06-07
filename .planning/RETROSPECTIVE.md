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

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 5 |
| Plans | 17 |
| LOC (Python) | 3,625 |
| Timeline | 7 days |
| Replanning events | 1 (Phase 3) |
