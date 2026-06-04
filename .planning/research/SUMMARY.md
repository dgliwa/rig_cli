# Project Research Summary

**Project:** rig-cli — I/O Decoupling & Plan Command Milestone
**Domain:** IaC CLI for physical MIDI device configuration
**Researched:** 2026-06-04
**Confidence:** HIGH

## Executive Summary

Three-phase milestone: clean up CBA tech-debt (PR 1), introduce three narrow Protocol ports to decouple the apply engine from I/O (PR 2), then fix plan command correctness bugs and expose `rig plan` as a trustworthy read-only preview command (PR 3). No new dependencies. All patterns derive from existing codebase patterns and stdlib `typing.Protocol`.

The apply engine is currently untestable without physical hardware because `apply.py` calls `input()`, writes files, and sends MIDI inline. The fix is a ports-and-adapters pattern: define three narrow Protocol interfaces (`ConfirmationIO`, `StateWriter`, `MidiConnectionIO`), thread them into `ApplyContext` and `apply_plan`, then wire production adapters at the CLI boundary.

Two CBA tech-debt items must be cleaned up first as a prerequisite: `_build_preset` bypasses the `update_device_state` helper with raw dict construction (#11), and `ChaseBlissApplier` imports a private symbol `_detect_cba_setup` from `plan.py` (#12). These are self-contained and ship in a separate PR before protocol work begins.

The `plan` command (#13) is already scaffolded. The milestone's job is to fix three correctness bugs that make it trustworthy: `compute_diff` unconditionally marks existing scenes as "changed", scene state is written as `{}` making `no_change` detection impossible, and `_detect_cba_setup` is re-called during apply causing plan/apply divergence.

## Key Findings

### Stack

No stack changes. Three Protocol ports use `typing.Protocol` (stdlib). Plan output stays as Pydantic `BaseModel` (crosses serialization boundary via `model_dump_json()`). `ApplyContext` stays as `@dataclass` (holds mutable `connected_devices: set`).

**Port interfaces:**
- `ConfirmationIO` — wraps `interaction.py` prompt functions; lives in `ApplyContext`
- `StateWriter` — wraps `read_state`/`write_state`; parameter to `apply_plan`
- `MidiConnectionIO` — wraps MIDI port selection in Phase -1; parameter to `apply_plan`

### Features

**Must have (table stakes):**
- Correct `no_change` detection — fix `compute_diff` always-changed bug and empty scene state storage
- `--format json` stable output contract (Pydantic `model_dump_json()`)
- Human-readable text output with visual hierarchy (`~`, `+`, `→`, `✓`, `⚠`)
- Plan is read-only — zero side effects; no MIDI, no state writes
- `--scene <name>` filter
- Summary line: `Plan: N to configure, M manual, K already set` or `No changes.`
- Exit codes: `0` = clean, non-zero = changes detected or error
- Cold-start warning when no state file exists

**Should have:**
- Hide `no_change` scenes by default; `--show-unchanged` flag

**Anti-features (do not build):**
- Plan file output / pipe workflow / `--auto-approve` — Terraform features without value for single-user rig

### Architecture

Two-PR structure within the milestone:

**PR 1 (cleanup, no protocol work):** `mark_preset_saved` helper in `base.py` (#11) + rename `_detect_cba_setup` → `detect_cba_setup` in `plan.py` (#12). Standalone, low-risk.

**PR 2 (protocol introduction):** Define protocols in dependency order — `ConfirmationIO` → thread into `ApplyContext` and appliers; `StateWriter` → replace `write_state` call in `apply_plan`; `MidiConnectionIO` → replace Phase -1 prompt block. New file: `src/rig/engine/ports.py`. New adapters in `src/rig/interaction.py`. Test fakes in `tests/fakes.py`.

**PR 3 (plan command):** Fix `compute_diff` always-changed bug, fix empty scene state, add `before`/`after` to `DeviceAction`, add summary line, exit codes, cold-start warning, `--show-unchanged`.

### Critical Pitfalls

1. **Fat Protocol wrapping `ApplyContext`** — define three narrow protocols; a method that takes `ApplyContext` as parameter means the concern isn't isolated
2. **Scene state written unconditionally** — `state.scenes[name] = {}` must be guarded: only write when at least one device returned `status == "confirmed"`
3. **Plan/apply divergence via `_detect_cba_setup` re-call** — after #12 is fixed, `apply` must NOT re-run plan-time detection mid-apply
4. **`compute_diff` always-changed bug** — fix before plan command ships; conflicting diff/plan output destroys trust
5. **Protocol signature drift invisible at runtime** — enforce `mypy`/`pyright` in CI; add integration test with real production adapter

## Roadmap Implications

### Phase 1: CBA Tech-Debt Cleanup
Addresses: #11, #12
Delivers: `mark_preset_saved` helper; `detect_cba_setup` public symbol
Avoids: Pitfall 3 setup, Pitfall double-dict overwrite

### Phase 2: Engine I/O Decoupling
Addresses: #1
Delivers: Apply engine fully testable without hardware; three Protocol ports
Avoids: Pitfall 1 (fat protocol), Pitfall 2 (unconditional scene write)

### Phase 3: Plan Command Correctness
Addresses: #13
Delivers: Trustworthy `rig plan`; correct `no_change` detection; summary line; exit codes; `--show-unchanged`; stable JSON schema
Avoids: Pitfall 3 (re-detection divergence), Pitfall 4 (silent cold-start), Pitfall 5 (always-changed diff)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against Python 3.13 docs; existing codebase patterns confirmed |
| Features | HIGH | Direct codebase read; IaC patterns from Terraform/Pulumi docs |
| Architecture | HIGH | Derived from direct code reading of all affected files |
| Pitfalls | HIGH | Each pitfall identified from direct codebase inspection with file/line references |

**Overall:** HIGH

## Open Questions

- `before`/`after` fields on `DeviceAction` — add in Phase 3 or defer?
- `CbaSetupAction` placement in plan output — flat list vs. integrated into `ScenePlan`?
- Exit code values — `1` = changes, `2` = error? Confirm before implementing.

---
*Research completed: 2026-06-04 | Ready for roadmap: yes*
