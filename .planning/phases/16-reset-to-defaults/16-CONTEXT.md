# Phase 16: Reset-to-Defaults - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Before each CBA preset's CC parameter values are sent during apply Phase 2 (`_build_preset`), all catalog controls with a non-`None` default value are first driven to their catalog default via CC messages. Footswitch and utility controls (`default=None`) are excluded from the reset batch. The reset fires per-preset, immediately before that preset's own CC messages.

This phase adds a reset step inside the existing `_build_preset` code path — no new action types, no state tracking, no changes to the plan engine.

</domain>

<decisions>
## Implementation Decisions

### D-01: Reset mechanism — inline in `_build_preset`
- No new `CbaSetupAction` type (user chose against a separate `"reset_defaults"` type)
- Before sending each preset's CC params, `_build_preset` builds and sends a batch of "reset" CC messages
- `_send_ccs()` is established pattern — reset CCs follow the same `send_control_change` approach

### D-02: Reset frequency — unconditional per-preset
- Every `build_preset` invocation sends defaults first, regardless of whether prior presets were already built in the same apply session
- No `reset_done` flag added to state.json
- Simpler and more reliable for multi-preset sessions (no edge cases)

### D-03: Reset CC computation — at apply time
- The reset CC batch is computed inside `_build_preset` at the moment of apply, using `device.config.controls`
- Device lookup: `next(d for d in ctx.rig.devices if d.id == action.device)`
- No action-level reset data fields — `CbaSetupAction` stays unchanged

### D-04: Reset CC filter and format
- Source: `device.config.controls` (already populated by the loader from the catalog)
- Filter: `control.default is not None and control.midi_cc is not None`
- Format per reset CC: `{"cc": <midi_cc>, "value": int(<default>)}`
- `Control.default` is `float | None`; `int(default)` converts cleanly for MIDI

### D-05: Dry-run and logging
- Dry-run: print `"  [dim]→ reset {N} defaults before {M} CC params[/dim]"` alongside existing CC param output
- Live mode: log count of reset CCs sent on success; log individual failures per CC
- No separate user prompt for the reset step — it's transparent

### D-06: Error handling for reset CCs
- Individual CC send failures during reset are logged but do NOT block the preset's CCs from being sent
- Same error handling pattern as the existing `_send_ccs()` inner function in `_build_preset`
- Failures are non-blocking — the reset is a best-effort cleanup

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CBA apply flow
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — `_build_preset()` method where reset CCs are inserted before preset CCs
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — `_detect_cba_setup_for_device()`, `ChaseBlissConfig`, `get_cc_params()`
- `packages/rig-chasebliss/src/rig_chasebliss/models.py` — `CbaSetupAction` (unchanged)

### CBA catalog (controls with defaults)
- `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` — `Control.default` field; all catalog entries (Mood MkII, Wombtone MkII, Brothers AM) with defaults populated

### Engine context (available in _build_preset)
- `packages/rig/src/rig/engine/appliers/base.py` — `ApplyContext` (has `rig` field for device lookup)

### Tests
- `packages/rig-chasebliss/tests/test_device.py` — Existing validation tests; reset tests go here
- `packages/rig-chasebliss/tests/test_catalog.py` — Existing catalog tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Point
- `ChaseBlissApplier._build_preset()` in `applier.py` line ~55-100 — the inner `_send_ccs()` function is the established pattern for sending CC batches. Reset CCs are sent via the same pattern, before the preset CCs.

### Device Lookup at Apply Time
- `ctx.rig.devices` — list of all devices in the rig. Inside `_build_preset`, lookup by `action.device` ID to access `device.config.controls`.

### Established Patterns
- CC sends use `ctx.midi.send_control_change(device_id, cc, value, channel)` — same for reset
- CC failure handling: `try/except Exception` around each send, log error, continue
- Dry-run: console.print with `[dim]` markup, return `DeviceApplyResult(status="skipped")`

</code_context>

<specifics>
## Specific Ideas

- No delay/sleep between reset and preset CC sends — CBA pedals handle rapid CC messages (confirmed in Phase 15 context)
- MIDI RESET (CC110) is explicitly out of scope — factory reset behavior, never invoked as part of apply
- The existing `_send_ccs()` inner function can be reused or inlined for the reset batch — same `send_control_change` call

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-reset-to-defaults*
*Context gathered: 2026-06-08*
