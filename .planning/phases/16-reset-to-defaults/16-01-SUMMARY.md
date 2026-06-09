# Plan 16-01 SUMMARY: Reset-to-Defaults

**Phase:** 16 (reset-to-defaults)
**Plan:** 01
**Status:** ✅ Complete
**Completed:** 2026-06-08

## Objective

Add a reset-to-defaults step inside `ChaseBlissApplier._build_preset()` in
`packages/rig-chasebliss/src/rig_chasebliss/applier.py`. Before sending each preset's CC
parameter values, send a batch of CC messages to drive all resettable controls (those with
a non-`None` catalog default) to their factory default values.

## Implementation

### Changes to `applier.py`

1. **`_find_device()` helper** (module-level function) — Looks up a device by ID in the rig,
   returns `None` gracefully when `rig` is None or the device is not found.

2. **Dry-run branch updated** — Computes `reset_count` from `device.config.controls`,
   shows `"  [dim]→ reset {N} defaults before {M} CC params[/dim]"` when there are
   resettable controls.

3. **`_send_reset_ccs()` inner function** — Iterates `device.config.controls`, filters to
   those with `c.default is not None and c.midi_cc is not None`, sends each via
   `ctx.midi.send_control_change(device, cc, int(default), channel)`. Uses same
   error-handling pattern as `_send_ccs()` (individual failures caught, logged, non-blocking).

4. **Call site** — `_send_reset_ccs()` is called immediately before `_send_ccs()`, before
   the user-facing `prompt_cba_build_preset()` interaction.

### Changes to `tests/test_applier.py`

12 tests covering:
- `_find_device` helper edge cases (unknown ID, None rig, existing device)
- Reset sent before preset CC params (mocked call order verification)
- Reset excludes `default=None` controls
- Dry-run returns `"skipped"` without crashing
- No reset when all controls have `default=None`
- Reset failure is non-blocking (preset CCs still sent)
- Reset fires on every `_build_preset` invocation (per-preset, D-02)
- Empty controls list handled gracefully
- `ctx.rig=None` handled gracefully
- Multiple resettable controls each get their reset CC

### Key Design Decisions

| Decision | Applied |
|----------|---------|
| D-01: Reset inline in `_build_preset` (no new action type) | ✅ |
| D-02: Unconditional per-preset | ✅ |
| D-03: Reset CC computed at apply time from `device.config.controls` | ✅ |
| D-04: Filter `default is not None and midi_cc is not None`; format `int(default)` | ✅ |
| D-05: Dry-run prints reset count | ✅ |
| D-06: Individual CC failures non-blocking | ✅ |

## Test Results

```
uv run pytest packages/rig-chasebliss/ -q
....................................                                     [100%]
36 passed in 0.10s
```

## Verification

| Check | Result |
|-------|--------|
| `pytest` exits 0 | ✅ 36 passed |
| `_send_reset_ccs` defined + called | ✅ 2 references |
| `_find_device` defined + called | ✅ 3 references |
| `_find_device` importable | ✅ |
| `default is not None` filter | ✅ 2 occurrences |
| No spurious `default=None` | ✅ 0 occurrences (correct) |
