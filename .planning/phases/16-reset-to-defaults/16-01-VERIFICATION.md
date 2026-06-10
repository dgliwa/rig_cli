---
phase: 16-reset-to-defaults
verified: 2026-06-10T12:00:00Z
status: passed
score: 9/9 must-haves verified
---

# Phase 16: Reset-to-Defaults — Verification Report

**Phase Goal:** Before each preset's CC values are sent to a CBA pedal, all resettable controls are first driven to their catalog default, ensuring clean preset creation
**Verified:** 2026-06-10T12:00:00Z
**Status:** passed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_send_reset_ccs()` defined and called before `_send_ccs()` in `_build_preset()` | ✓ VERIFIED | `applier.py:170` — `_send_reset_ccs()` defined; line 210: `reset_sent = _send_reset_ccs()` called before `_send_ccs()` on line 215 |
| 2 | Reset excludes controls with `default=None` (footswitches, utility CCs) | ✓ VERIFIED | `applier.py:177` — filter: `c.default is not None and c.midi_cc is not None`; script confirms footswitches have `default=None` |
| 3 | Dry-run shows reset count without sending CCs | ✓ VERIFIED | `applier.py:139-152` — dry-run branch computes `reset_count` from controls; prints `reset {N} defaults` message; no MIDI calls |
| 4 | Reset fires per-preset (inside `_build_preset()`, not once per session) | ✓ VERIFIED | `_send_reset_ccs()` defined and called inside `_build_preset()` method (line 138), which is called per-preset at line 59 |
| 5 | Empty controls list handled gracefully (no reset attempted) | ✓ VERIFIED | `applier.py:179` — `if not resettable: return sent`; also `if device is None: return sent` |
| 6 | `_find_device()` returns None gracefully when rig is None | ✓ VERIFIED | `applier.py:173` — `if device is None or not hasattr(device.config, "controls"): return sent` |
| 7 | Individual reset CC failures are non-blocking (preset CCs still sent) | ✓ VERIFIED | `applier.py:190-194` — try/except catches exceptions for each CC, logs error, continues loop; preset CCs on line 215 still execute |
| 8 | `uv run pytest packages/rig-chasebliss/tests/test_applier.py -q` passes (12+ tests) | ✓ VERIFIED | `12 passed in 0.12s` — exit 0 |
| 9 | `uv run pytest packages/rig-chasebliss/ -q` passes | ✓ VERIFIED | `40 passed in 0.10s` — exit 0 |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/rig-chasebliss/src/rig_chasebliss/applier.py` | `_send_reset_ccs()`, wired before `_send_ccs()` | ✓ EXISTS + SUBSTANTIVE | `_send_reset_ccs()` defined at line 170; called at line 210; `_send_ccs()` called at line 215 |
| `packages/rig-chasebliss/tests/test_applier.py` | 12 tests covering reset behavior | ✓ EXISTS + SUBSTANTIVE | `12 passed` — covers call order, exclusion, dry-run, empty controls, failure safety, per-preset |

**Artifacts:** 2/2 verified

## Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| CBA-06: Reset-to-defaults before preset CC messages | ✓ SATISFIED | — |

**Coverage:** 1/1 requirements satisfied

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| applier.py | 170 | `_send_reset_ccs()` lacks `connected_devices` gate | ⚠️ Warning | Reset CCs attempted even when device not in `ctx.connected_devices` (asymmetric with `_send_ccs()` gate). Exceptions are caught — non-blocking, no crash. Documented tech debt. |

## Human Verification Required

None — all verifiable items checked programmatically.

## Gaps Summary

**No gaps found.** Phase goal achieved. Ready to proceed.

## Verification Metadata

**Verification approach:** Goal-backward (derived from phase goal)
**Must-haves source:** ROADMAP.md success criteria + 16-01-SUMMARY.md must-haves
**Automated checks:** 9 passed, 0 failed
**Human checks required:** 0
**Total verification time:** < 1 min

---
*Verified: 2026-06-10T12:00:00Z*
*Verifier: Claude (automated verification)*
