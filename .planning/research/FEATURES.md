# Feature Landscape: `plan` Command + Engine I/O Decoupling

**Domain:** IaC CLI for guitar rig (physical device configuration)
**Milestone scope:** `plan` command + engine I/O decoupling
**Researched:** 2026-06-04
**Confidence:** HIGH — codebase read directly; IaC patterns from Terraform/Pulumi docs

---

## Context: What Already Exists

`plan.py` is partially implemented. `compute_plan` produces a `Plan` with `ScenePlan` and `DeviceAction` objects. `cli.py` already has a `plan` command that calls `compute_plan` and renders text/JSON output. The action taxonomy (configure / verify / analog / no_change) is defined on `DeviceAction.status`.

The gap is not "build plan from scratch" — it is:
1. The engine has I/O mixed in (`apply.py` calls `prompt()`, writes state, sends MIDI inline)
2. `plan` has a known bug: `compute_plan` always starts from empty state when `root_path` is None
3. `diff.py` always marks existing scenes as "changed" regardless of preset drift
4. `_detect_cba_setup` is called from `plan.py` but also re-called during `apply.py` — the plan output is not self-contained
5. Scene state stored as empty dict means per-scene preset tracking is impossible

---

## Table Stakes

Features the user is blocked without. These must ship.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Correct `no_change` detection | Without it, `plan` always shows changes and `apply` always prompts; the core value proposition breaks | Medium | Requires fixing `compute_diff` always-changed bug and `state.scenes[name] = {}` empty storage |
| Action type taxonomy covers all device types | Missing or wrong action types produce misleading output; user acts on wrong information | Low | Four types already defined: `configure`, `verify`, `analog`, `no_change`. Must be applied consistently including for CBA devices |
| `--format json` machine-readable output | `apply` reads the plan; scripting/automation requires stable JSON | Low | Already scaffolded in CLI; must ensure `DeviceAction` and `Plan` models are stable and complete |
| Human-readable text output with visual hierarchy | User must be able to scan plan output at a glance before running `apply` | Low | Already scaffolded; needs `no_change` clean path and CBA action rendering |
| Plan is read-only (zero side effects) | If `plan` writes state or sends MIDI it violates the preview contract | Low | Currently correct; must remain so after decoupling refactor |
| `--scene <name>` filter | User needs to preview a single scene without reading the whole rig | Low | Already in CLI; must work after decoupling |
| Summary line at end of text output | "N changes, M manual, K already correct" — gives instant signal whether apply is needed | Low | Not yet implemented; Terraform pattern: "Plan: X to add, Y to change" |
| Clean exit code semantics | `exit 0` when clean, `exit 1` on config error, non-zero on changes-detected (for scripting) | Low | Not yet implemented in CLI; blocks CI/CD use |

---

## Differentiators

Features that make the tool significantly better for this domain, not strictly required.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `analog` actions show the preset name and device label prominently | Unlike digital devices, analog changes require the user to physically touch knobs — the plan must clearly mark these as "you must do this manually" so nothing is silently skipped | Low | Current rendering uses `⚠` symbol; wording should say "manual" explicitly |
| CBA setup actions inline with scene actions | CBA 3-phase setup (channel → preset build → scene register) is a prerequisite for scene apply; showing it as a separate "CBA Setup Required" block (current approach) is good — but should indicate which scenes are blocked until setup completes | Medium | Requires `_detect_cba_setup` output to be self-contained; the re-detection-during-apply bug must be fixed |
| `--format json` stable schema for apply re-use | `apply` can consume `plan --format json` output directly (pipe workflow: `rig plan -f json \| rig apply --plan-file`). Not yet wired but the models support it. | Medium | Deferred to future milestone per PROJECT.md; but schema must be stable now or apply integration breaks later |
| `no_change` scenes shown at reduced verbosity | If 8 scenes are clean and 1 has changes, the user should see 1 change clearly, not scroll through 8 "already set" lines. Default: omit `no_change` scenes. `--verbose` or `--show-unchanged` reveals them. | Low | Terraform hides unchanged resources by default; Pulumi has `--show-sames` flag |
| State source annotation in output | `State source: .rig/state.json (last applied: <timestamp>)` tells the user whether the plan is based on real device history or a cold start | Low | Cold-start (no state file) should print a warning: "No state found — all scenes will appear as new" |

---

## Anti-Features

Things to deliberately NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| `plan --apply` / `--auto-approve` shortcut | Blurs the plan/apply boundary. The whole point of a plan command is a review gate. | Keep `rig apply` as the separate apply path |
| Saving plan output to a file (`--out`) | Terraform does this for CI governance; this rig has one user, one machine, one state file. The complexity is not justified yet. | If needed later, `rig plan -f json > plan.json && rig apply --plan-file plan.json` can be added as a future milestone |
| Per-preset diff history / changelog | Tracking "preset was X, then Y, then Z" over time requires a log structure, not just a state snapshot | Current state model (last_preset per device) is correct for the scope |
| Parallel scene planning | Scenes are independent at plan time, but apply is sequential (MIDI is serial). Parallelizing plan would complicate the code with no real benefit for a 5-15 scene rig | Keep single-pass loop |
| Interactive plan approval prompt inside `plan` | `plan` is read-only; prompting inside it couples I/O to the engine, which is the exact problem being solved in this milestone | Approval lives in `apply` |
| Device connectivity check during plan | Checking whether a MIDI port is live during plan would require hardware. Plan must remain executable without physical devices connected. | Port availability check belongs in `apply` pre-flight only |

---

## Feature Dependencies

```
Fix empty scene state storage (.rig/state.json scenes: {})
    → Correct no_change detection for digital/HX devices
        → Accurate plan summary line (N changes vs M unchanged)
            → Trustworthy exit code semantics

Fix _detect_cba_setup re-call during apply
    → Self-contained plan output (CBA setup fully enumerated at plan time)
        → CBA phase inline with scene actions in plan output

Engine I/O decoupling (extract prompt / state-write / MIDI from apply_plan)
    → Plan engine testable without hardware
        → apply can consume plan output without re-computing
```

---

## The Action Type Taxonomy (Canonical)

This covers all rig change scenarios. The taxonomy must be exhaustive — every device action in every scene lands in exactly one bucket.

| Action | When | Automation | Displayed As |
|--------|------|------------|--------------|
| `configure` | Desired preset != last_preset in state; device is digital/modeler/CBA | MIDI PC/CC sent by `apply` | `→ device: PC#N 'preset-name' (ch N)` |
| `verify` | Desired preset == last_preset in state; device is digital/modeler/CBA | No MIDI needed; state already correct | `✓ device: 'preset-name' (already set)` |
| `analog` | Device type is `analog`; any preset change | Manual only; user must adjust knobs | `⚠ device: set to 'preset-name' (manual)` |
| `no_change` | Scene status is `unchanged` AND all device actions are `verify` | Nothing to do | Hidden by default; `--show-unchanged` reveals |

Note: `analog` actions always require manual intervention regardless of state. The current implementation marks `scene_has_changes = True` when analog preset differs from state, which is correct — analog devices do cause scene-level change status.

---

## Plan Output Contract (Text Format)

The text output must follow this structure to be scannable:

```
~ scene-name (changed)
  → hx-stomp: PC#5 'Fuzz Lead' (ch 1)
  ✓ mood-mkii: 'Dark Wash' (already set)
  ⚠ bluesky: set to 'Shimmer' (manual)

+ new-scene (new)
  → hx-stomp: PC#12 'Clean Pad' (ch 1)

CBA Setup Required:
  🔧 blooper: establish MIDI channel 3
  🔧 blooper: build preset #1 'Looper A'

─────────────────────────────────────
Plan: 2 to configure, 1 manual, 1 already set
State source: .rig/state.json
```

Summary line format: `Plan: N to configure, M manual, K already set` or `No changes. Rig is up to date.`

---

## Plan Output Contract (JSON Format)

The existing `Plan.model_dump_json()` output is the stable contract. Fields that must remain stable:

- `plan.status` — `"clean"` | `"changes_detected"`
- `plan.scenes[name].status` — `"new"` | `"changed"` | `"unchanged"`
- `plan.scenes[name].device_actions[].status` — `"configure"` | `"verify"` | `"analog"` | `"no_change"`
- `plan.scenes[name].device_actions[].device` — device ID string
- `plan.scenes[name].device_actions[].preset_number` — nullable int (absent for analog)
- `plan.scenes[name].device_actions[].midi_channel` — nullable int
- `plan.cba_setup[].type` — `"establish_channel"` | `"build_preset"` | `"register_scenes"`

Do not add fields to `DeviceAction` or `CbaSetupAction` in this milestone beyond what is needed to fix bugs. Schema stability matters for `apply` integration.

---

## Integration with `apply`

The plan/apply contract today:
1. `cli.py apply` calls `compute_plan(rig, root_path)` internally — plan is not shared with user
2. `apply_plan(plan, ...)` consumes the `Plan` object directly

After decoupling, the contract should be:
1. `plan` command renders `Plan` for user review
2. `apply` command recomputes `Plan` from same inputs (idempotent; no state mutation between plan and apply)
3. `apply` does NOT need to accept a plan file in this milestone — recomputing is safe and simpler

The key invariant: `compute_plan` is pure (reads state, reads rig config, emits `Plan` — no mutations). This must remain true after the I/O decoupling refactor.

---

## MVP for This Milestone

**Must have (blocking):**
1. Fix `compute_diff` always-changed bug (scenes that haven't changed must be `unchanged`)
2. Fix `_detect_cba_setup` re-detection during apply (plan output must be self-contained)
3. Engine I/O decoupling — extract `prompt`, `write_state`, and MIDI calls from engine logic behind Protocol boundaries so plan and apply are unit-testable without hardware
4. Summary line in text output
5. Cold-start warning when no state file exists
6. Correct exit codes (`exit 0` = clean, non-zero = changes detected or error)

**Should have (high value, low effort):**
7. Hide `no_change` scenes by default in text output; add `--show-unchanged` flag
8. State source annotation at bottom of text output

**Defer:**
- Plan file output (`--out`) — future milestone
- Pipe workflow (`plan -f json | apply --plan-file`) — future milestone
- Per-device validation hooks (Protocol-based) — tech debt; separate PR

---

## Sources

- Codebase direct read: `src/rig/engine/plan.py`, `src/rig/engine/apply.py`, `src/rig/engine/diff.py`, `src/rig/engine/state.py`, `src/rig/cli.py`
- Codebase concerns audit: `.planning/codebase/CONCERNS.md`
- Project context: `.planning/PROJECT.md`
- Terraform plan design: [Terraform Plan Command: Output, Flags & Examples](https://spacelift.io/blog/terraform-plan) — HIGH confidence
- Pulumi preview design: [Update Plans | Pulumi Concepts](https://www.pulumi.com/docs/iac/guides/basics/update-plans/) — MEDIUM confidence (search result, not fetched)
- IaC plan/apply workflow patterns: [IaC Architecture Patterns](https://spacelift.io/blog/iac-architecture-patterns-terragrunt) — MEDIUM confidence
