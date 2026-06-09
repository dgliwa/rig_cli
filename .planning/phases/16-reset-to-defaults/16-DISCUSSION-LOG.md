# Phase 16: Reset-to-Defaults - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 16-Reset-to-Defaults
**Areas discussed:** Reset mechanism, State tracking, Reset CC computation

---

## Area 1: Reset Mechanism Design

| Option | Description | Selected |
|--------|-------------|----------|
| A: Inline in `_build_preset` | `_build_preset` computes and sends reset CCs before the preset's own CCs. No new action type. Simple, localized. | ✓ |
| B: Separate action type | New `"reset_defaults"` in `CbaSetupAction`. Emitted before each `build_preset`. Visible in plan output. | |
| C: Dedicated reset-everything action | One reset action per apply session, then subsequent builds skip reset. | |

**User's choice:** Inline in `_build_preset`
**Notes:** "1" — Quick, decisive choice for the simplest option.

---

## Area 2: State Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| A: Unconditional per-preset | Before every `build_preset`, send defaults. No state needed. More CC traffic but reliable. | ✓ |
| B: Track in device state | Track `reset_done` per device in state.json. More efficient for multi-preset sessions. | |

**User's choice:** Unconditional per-preset
**Notes:** "2" — No state tracking overhead.

---

## Area 3: Reset CC Computation

| Option | Description | Selected |
|--------|-------------|----------|
| A: At apply time | In `_build_preset`, compute reset batch from `device.config.controls` at the moment of apply. Always current. | ✓ |
| B: At action creation time | `_detect_cba_setup_for_device` computes reset list, stores on action. Planner determines what to reset. | |

**User's choice:** At apply time
**Notes:** "3" — Uses current device config, no action changes needed.

---

## Claude's Discretion

None — all three areas had explicit user decisions.

## Deferred Ideas

None
