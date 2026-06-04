---
phase: 01-cba-tech-debt-cleanup
reviewed: 2026-06-04T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/rig/engine/appliers/base.py
  - src/rig/engine/plan.py
  - src/rig/engine/appliers/chase_bliss.py
findings:
  critical: 1
  warning: 4
  info: 0
  total: 5
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-04
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed `base.py`, `plan.py`, and `chase_bliss.py`. The domain model and state
management patterns are coherent and the Protocol-based applier design is clean.
One critical behavioral bug exists in `_establish_channel`: the device state is
marked `channel_established=True` even when the PC#0 MIDI message was never sent
(because the device was not connected at apply time). Four warnings cover dead code
and a backward-compat import that violates the project's stated convention.

## Critical Issues

### CR-01: `channel_established` Set True When MIDI Was Never Sent

**File:** `src/rig/engine/appliers/chase_bliss.py:134`

**Issue:** In `_establish_channel`, after the first user-prompt loop (lines 98–101)
the code attempts to send PC#0 only when `action.device in ctx.connected_devices`
(line 110). If the device is absent from `connected_devices`, `midi_sent` stays
`False` and the second confirmation loop (lines 120–129) is skipped entirely. The
final state-write at line 134 then tests `if res == "confirm"` — but `res` still
holds the value the user entered in the *first* prompt ("ready to send"). The user
said "I'm ready", not "the channel is saved", yet `channel_established=True` is
written to state. On the next `plan` run the CBA setup phase will be skipped,
even though the pedal's MIDI channel was never programmed.

The bug is not covered by tests: all three `test_establish_channel_*` tests use
`connected={"cba-mood"}`; the unconnected path is never exercised.

**Fix:** Gate the state write on `midi_sent` actually being `True`, or restructure
the method so the step-1 "ready" confirm is semantically distinct from the step-2
"channel saved" confirm. Minimal fix:

```python
# Only mark established if we successfully sent the PC
if res == "confirm" and midi_sent:
    update_device_state(
        ctx.state,
        action.device,
        channel_established=True,
        midi_channel=action.midi_channel,
    )
# Return skipped (not confirmed) when MIDI was never sent
return DeviceApplyResult(
    device=action.device,
    status="confirmed" if (res == "confirm" and midi_sent) else "skipped",
    preset=None,
)
```

---

## Warnings

### WR-01: Dead Function `_hx_preset_number` in `plan.py`

**File:** `src/rig/engine/plan.py:46`

**Issue:** `_hx_preset_number` is defined but never called anywhere in the
codebase. The HX preset lookup is duplicated inline at lines 170–173 inside
`compute_plan`, making this function permanently dead. Its presence implies a
future caller exists or once existed; neither is true.

**Fix:** Remove lines 46–51 and inline nothing — the identical lookup is already
present at lines 170–173. If unification is desired, replace the inline block with
a call to the existing `_get_preset_number`-style helper (or rename and repurpose
`_hx_preset_number`).

---

### WR-02: `detect_cba_setup` Imports from Legacy Compat Module

**File:** `src/rig/engine/plan.py:68`

**Issue:** `detect_cba_setup` imports `ChaseBlissConfig` from
`rig.models.pedal` (the backward-compat re-export shim) rather than from
`rig.models.device` (canonical source). The shim's own module docstring reads
"Re-exports for backward compatibility — prefer rig.models.device for new code."
This import is new code in the CBA setup path and contradicts the project
convention documented in `CLAUDE.md` and `pedal.py` itself.

**Fix:**
```python
# Before (plan.py line 68)
from rig.models.pedal import ChaseBlissConfig

# After
from rig.models.device import ChaseBlissConfig
```

---

### WR-03: `DeviceAction.status` Literal Contains Unreachable Value `"no_change"`

**File:** `src/rig/engine/plan.py:16`

**Issue:** `DeviceAction.status` is typed as
`Literal["configure", "verify", "analog", "no_change"]` but `compute_plan` never
emits `"no_change"` — it emits only `"configure"`, `"verify"`, or `"analog"`. The
value `"no_change"` only appears as a filter in `apply.py` line 152. This orphaned
value causes two problems: (1) static analysers infer a broader type than is
actually produced, and (2) readers assume some code path emits `"no_change"` when
none does, creating a maintenance trap.

**Fix:** Remove `"no_change"` from the `Literal` and update `apply.py` line 152
accordingly (or emit `"no_change"` from `compute_plan` when a device is already
correct and `"verify"` is inappropriate). Either direction closes the gap; the
current state is contradictory.

---

### WR-04: `collect_midi_devices` Has a Dead `rig` Parameter

**File:** `src/rig/interaction.py:216` (called from `src/rig/engine/apply.py:82`)

**Issue:** `collect_midi_devices(plan: Plan, rig: Rig) -> set[str]` accepts `rig`
as a required, non-optional parameter but never references it in the function body.
The caller in `apply.py` passes `rig` which is typed `Rig | None`; when `midi` is
truthy and `rig` is `None`, `None` is silently passed for a parameter typed `Rig`.
This is both a dead parameter (no-op) and a misleading type contract.

**Fix:** Remove the `rig` parameter from `collect_midi_devices` and update the
call site in `apply.py`:

```python
# interaction.py
def collect_midi_devices(plan: Plan) -> set[str]:
    ...

# apply.py line 82
midi_devices = collect_midi_devices(plan) if midi else set()
```

---

_Reviewed: 2026-06-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
