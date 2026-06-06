# Phase 5: Dependency Graph & Plan Command - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 5-dependency-graph-plan-command
**Areas discussed:** DeviceGraph formalization, Unused/missing preset output, Plan output structure, PLAN-10 & apply.py scope

---

## DeviceGraph Formalization

| Option | Description | Selected |
|--------|-------------|----------|
| New DeviceGraph type in models/ | Standalone class in models/graph.py; Rig.apply_order() delegates to it | ✓ |
| Enhance Rig.apply_order() in-place | Add topological sort + cycle detection directly to existing method | |
| New DeviceGraph in engine/ | Put it in engine/graph.py as a computation, not a domain model | |

**User's choice:** New DeviceGraph type in models/graph.py

---

| Option | Description | Selected |
|--------|-------------|----------|
| Signal chain order only | Edges follow signal_chain positions; controller always last | ✓ |
| Explicit depends_on in device YAML | Add optional depends_on field to device YAML | |
| You decide | Pick whichever approach makes graph cleanest | |

**User's choice:** Signal chain order only — no config-repo changes needed

---

| Option | Description | Selected |
|--------|-------------|----------|
| Raise ConfigError | Raise ConfigError naming cycle participants — consistent with loader pattern | ✓ |
| Log and skip, continue with partial order | Warn and apply best-effort | |
| You decide | Pick whatever is most consistent with codebase error handling | |

**User's choice:** Raise ConfigError with cycle participants named

---

## Unused/Missing Preset Output

| Option | Description | Selected |
|--------|-------------|----------|
| Both: missing device OR missing preset ID | Flag if device missing or preset ID not found on device | ✓ |
| Missing preset ID only | Only flag when device exists but has no matching preset | |
| You decide | Pick whatever makes rig plan most useful as a diagnostic | |

**User's choice:** Both — missing device OR missing preset ID on existing device

---

| Option | Description | Selected |
|--------|-------------|----------|
| Unused = digital/HX presets never in any scene; skip analog | Only DigitalPreset and HXStompPreset; AnalogPresets excluded | ✓ |
| Unused = ALL preset types never in any scene | Flag every preset type | |
| You decide | Pick what makes check most signal-to-noise useful | |

**User's choice:** Unused = digital/HX only; AnalogPresets excluded (they document knob positions)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Warnings section at bottom; missing = non-zero exit, unused = zero exit | Missing refs are errors; unused are informational | ✓ |
| Warnings inline under each scene; both affect exit code | Show issue where it occurs; both non-zero | |
| Separate rig lint command | Don't put this in plan at all | |

**User's choice:** Warnings section at bottom; missing = non-zero exit, unused = informational only

---

## Plan Output Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Stay scene-grouped, devices in apply_order within each scene | Natural for a rig — you're activating scenes | |
| Flip to device-grouped | One block per device, scenes listed inside | |
| Two sections: setup actions first, then scene list | CBA setup in apply order, then scene-by-scene | ✓ |

**User's choice:** Two sections — mirrors how apply actually works (setup then scenes)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same ~ configure marker for all CBA setup actions | All "needs doing" actions get same visual weight | ✓ |
| Unique markers per CBA setup type | Distinctive markers per action type | |
| You decide | Pick what reads most clearly at terminal | |

**User's choice:** Same `~` marker for all setup actions; action label provides distinction

---

| Option | Description | Selected |
|--------|-------------|----------|
| Count CBA setup actions as 'to configure' | Lumped with configure in summary | ✓ |
| Separate CBA count in summary | 'Plan: 2 to configure, 1 CBA setup, 1 manual, 2 already set' | |
| You decide | Pick most useful summary line | |

**User's choice:** CBA setup actions counted as "to configure"

---

## PLAN-10 & Apply.py Scope

| Option | Description | Selected |
|--------|-------------|----------|
| apply.py consumes pre-computed Plan; detect_cba_setup removed from apply path | CLI computes plan, passes to apply; removes the TODO | ✓ |
| Minimal: just remove duplicate detect_cba_setup in compute_plan | Only fix the immediate TODO; apply.py internals unchanged | |
| Full pipeline: plan → apply chain enforced at CLI level | rig apply always runs plan first, asks confirmation | |

**User's choice:** apply.py consumes pre-computed Plan; detect_cba_setup removed from apply path

---

| Option | Description | Selected |
|--------|-------------|----------|
| apply_plan() calls compute_plan() internally as fallback | rig apply remains a single-command workflow | ✓ |
| apply_plan() requires a Plan argument — fail loudly if not provided | Forces plan-then-apply workflow | |
| You decide | Pick what keeps CLI most ergonomic for single user | |

**User's choice:** apply_plan() self-computes as fallback — preserves single-command UX

---

## Claude's Discretion

None — all four areas were explicitly decided by the user.

## Deferred Ideas

- **Full plan→apply pipeline UX** (plan shows output, asks for confirmation, then executes) — was raised as an option, deferred. `rig apply` stays single-command.
- **Device trigger registration protocol** — from Phase 3/4 deferred lists; still deferred.
- **Plugin context subclassing per device type** — from Phase 4 deferred list; Phase 5 only needs minimum context for plan()/diff() implementation.
