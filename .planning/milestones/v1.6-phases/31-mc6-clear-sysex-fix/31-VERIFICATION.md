---
phase: 31-mc6-clear-sysex-fix
verified: 2026-06-22T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 31: MC6 Clear SysEx Fix — Verification Report

**Phase Goal:** Fix the MC6 clear SysEx default so `clear_preset_messages()` defaults to `save=True` (Op6=0x7F, flash persistence), matching the MC6 web UI behavior and preventing cleared switches from reverting after power cycle.
**Verified:** 2026-06-22
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                 | Status     | Evidence                                                                                                                    |
|----|---------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------------|
| 1  | `clear_preset_messages()` signature has `save: bool = True`                          | VERIFIED   | `sysex.py:79` — `def clear_preset_messages(preset_idx: int, save: bool = True) -> list[list[int]]:`                       |
| 2  | Default call produces 16 messages each with byte index 11 = 0x7F                     | VERIFIED   | `sysex.py:85-86`; direct Python execution confirmed `byte[11] = 0x7f` for all 16 slots                                    |
| 3  | Explicit `save=False` produces byte index 11 = 0x00                                  | VERIFIED   | `sysex.py:85` — `save_byte = 0x7F if save else 0x00`; confirmed via direct execution: `byte[11] = 0x0`                   |
| 4  | `uv run pytest packages/ -q` exits 0 with no failures                                | VERIFIED   | Suite ran: 392 passed in 0.61s                                                                                             |
| 5  | No stale "avoids MC6 bank navigation" comment in test files                           | VERIFIED   | `grep` across all three modified files returned no matches (exit 1 = no lines found)                                       |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                           | Expected                                       | Status    | Details                                                                                         |
|--------------------------------------------------------------------|------------------------------------------------|-----------|-------------------------------------------------------------------------------------------------|
| `packages/rig-morningstar/src/rig_morningstar/sysex.py`            | `save: bool = True` default; `0x7F` save byte | VERIFIED  | Line 79: signature correct; line 85: `save_byte = 0x7F if save else 0x00`                      |
| `packages/rig-morningstar/tests/test_sysex.py`                     | Tests for default flash and explicit no-save   | VERIFIED  | `test_default_saves_to_flash` (line 50) asserts `msg[11] == 0x7F`; `test_explicit_no_save` (line 54) asserts `msg[11] == 0x00` |
| `packages/rig/tests/test_mc6_sysex.py`                             | Updated slot sequence assertion; no-save test  | VERIFIED  | Line 90: `assert msg[11] == 0x7F  # save flag (default True — writes to flash)`; `test_clear_preset_messages_no_save` at line 93 asserts `0x00` |

### Key Link Verification

| From                              | To                                | Via                      | Status   | Details                                                                                    |
|-----------------------------------|-----------------------------------|--------------------------|----------|--------------------------------------------------------------------------------------------|
| `clear_preset_messages(save=True)` | `_build(... op6=0x7F ...)`        | `save_byte = 0x7F if save else 0x00` | WIRED | `sysex.py:85-86` — `save_byte` passed as `op6` to `_build`; byte[11] in assembled message = `op6` |
| `test_default_saves_to_flash`     | `clear_preset_messages(0)`        | `assert msg[11] == 0x7F` | WIRED    | `test_sysex.py:51-52` — directly asserts the flash byte                                   |
| `test_clear_preset_messages_slot_sequence` | `clear_preset_messages(2)` | `assert msg[11] == 0x7F` | WIRED | `test_mc6_sysex.py:90` — assertion updated from `0x00` to `0x7F`                        |

### Data-Flow Trace (Level 4)

Not applicable. This phase produces SysEx message builders (pure functions returning byte lists), not components that render dynamic data from an external source.

### Behavioral Spot-Checks

| Behavior                                     | Command                                                                 | Result                             | Status |
|----------------------------------------------|-------------------------------------------------------------------------|------------------------------------|--------|
| Default call yields `byte[11] = 0x7F`        | `python3 -c "from rig_morningstar.sysex import clear_preset_messages; ..."` | All 16 msgs: `byte[11] = 0x7f`  | PASS   |
| Explicit `save=False` yields `byte[11] = 0x00` | Same script, `clear_preset_messages(0, save=False)`                    | All 16 msgs: `byte[11] = 0x0`     | PASS   |
| Full package test suite                      | `uv run pytest packages/ -q`                                            | 392 passed in 0.61s               | PASS   |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                 | Status    | Evidence                                                                        |
|-------------|------------|-----------------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------|
| MC6-01      | 31-01-PLAN | MC6 clear SysEx matches web UI byte sequence (Op6=0x7F for flash persistence) | SATISFIED | `sysex.py:85-86`; tests `test_default_saves_to_flash`, `test_clear_preset_messages_slot_sequence` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No `TBD`, `FIXME`, or `XXX` markers in any modified file. No stubs, hardcoded returns, or empty implementations detected.

### Human Verification Required

None. All critical behavior (byte values, test coverage, suite pass) is verifiable programmatically and was verified above.

### Gaps Summary

No gaps. All five must-have truths are confirmed against the actual source code and running test suite.

---

_Verified: 2026-06-22_
_Verifier: Claude (gsd-verifier)_
