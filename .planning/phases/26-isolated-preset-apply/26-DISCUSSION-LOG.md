# Phase 26: Isolated Preset Apply - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 26-isolated-preset-apply
**Areas discussed:** Plan integration approach, Device setup scope, --scene flag interaction, Error handling strategy

---

## Plan Integration Approach

| Option | Description | Selected |
|--------|-------------|----------|
| A — Bypass scenes (new function) | Build DeviceAction directly from device+preset lookup; call new `apply_device_preset()`; skip `compute_plan` and scene loop entirely | ✓ |
| B — Filter the plan (extend compute_plan) | `compute_plan` gains a filter; produces a minimal Plan with one ScenePlan; existing apply loop handles it | |
| C — Apply-level filter (skip in apply loop) | Compute full plan, filter non-matching actions during execution | |

**User's choice:** A — Bypass scenes (new function)
**Notes:** Isolated apply is a distinct mode. No scene context needed. This also aligns with the direction Phase 27 (editor mode) is heading — device+preset-centric operations without scene coupling.

---

## Device Setup Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted setup only | Call `setup()` only on the target device before `apply()` | ✓ |
| Skip setup, apply() handles it | Don't call `setup()` — let `device.apply()` manage connection | |

**User's choice:** Targeted setup only
**Notes:** Keeps the setup→apply contract consistent with how the full apply works, just scoped to one device.

---

## --scene Flag Interaction

| Option | Description | Selected |
|--------|-------------|----------|
| --device/--preset exclusive with --scene (error if combined) | Print error and exit if both are passed | ✓ |
| --device/--preset silently ignore --scene | Ignore --scene if device+preset given | |
| --scene required with --device/--preset | Force scene context for isolated apply | |

**User's choice:** Exclusive with --scene (error if combined)
**Notes:** Makes the two modes clearly distinct. Avoids silent intent-swallowing.

---

## Error Handling Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast in CLI before MIDI (use existing ConfigError) | Validate device+preset IDs after loading config, before MIDI; use existing red-error pattern | ✓ |
| Fail in apply_device_preset() with ValueError | Engine validates; CLI catches ValueError | |

**User's choice:** Fail fast in CLI before any MIDI
**Notes:** Consistent with existing ConfigError handling pattern in the apply command. No MIDI ports opened for bad input.

---

## Claude's Discretion

- `DeviceAction` status field: using `ActionStatus.CONFIGURE` (standard value for changed preset)
- `apply_device_preset()` signature mirrors `apply_plan()` style (keyword-only args)
- State update: only `state.devices[device_id]` updated; `state.scenes` intentionally left stale

## Deferred Ideas

None — discussion stayed within phase scope.
