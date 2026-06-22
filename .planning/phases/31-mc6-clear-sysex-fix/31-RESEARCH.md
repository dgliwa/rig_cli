# Phase 31: MC6 Clear SysEx Fix - Research

**Researched:** 2026-06-22
**Domain:** Morningstar MC6 MkII SysEx Protocol — preset message clear behavior
**Confidence:** HIGH

## Summary

The Morningstar MC6 MkII SysEx protocol has no dedicated "clear preset" opcode. Clearing all message slots on a preset requires sending 16 individual Op2=`04h` messages — one per slot (0–15) — each with Op5=`00h` (NOTHING) and an empty payload. The current `clear_preset_messages()` implementation has the correct opcode, correct slot count, and correct byte positions. The sole defect is the save byte: the function defaults to `save=False` (Op6=`0x00`), meaning clears are written to the MC6's active RAM only and are lost on power cycle. The MC6 web UI always sends Op6=`0x7F` (save to flash) when clearing a preset slot, which is why re-powering the MC6 reverts slots that `rig apply` thought it had cleared.

The fix is a one-line change: flip the default from `save=False` to `save=True` in `clear_preset_messages()`. The function signature can remain unchanged because `device.py` calls it without keyword arguments and only needs the correct default. Two test assertions in `test_mc6_sysex.py` that currently pin `msg[11] == 0x00` must be updated to `0x7F` to reflect the corrected behavior. The higher-level tests in `test_sysex.py` are byte-agnostic and require no changes.

**Primary recommendation:** Change `save=False` to `save=True` in `clear_preset_messages()`. Update the two test assertions that pin the save byte to `0x00`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SysEx message construction | `rig-morningstar/sysex.py` | — | All byte-level protocol logic lives here |
| MC6 apply orchestration | `rig-morningstar/device.py` | — | Calls sysex builders; owns the send loop |
| Persistence to flash | Morningstar MC6 hardware | sysex.py Op6 byte | Op6=0x7F tells the device to write to flash |
| Protocol correctness tests | `test_mc6_sysex.py` | `test_sysex.py` | mc6_sysex has byte-level assertions; test_sysex tests structural invariants |

## Protocol Analysis

### MC6 MkII SysEx Frame Structure

Every MC6 SysEx message uses the following 16-byte fixed header followed by an optional payload:

```
Byte  0: F0          SysEx start
Byte  1: 00          Manufacturer ID byte 1
Byte  2: 21          Manufacturer ID byte 2
Byte  3: 24          Manufacturer ID byte 3
Byte  4: 03          Device Model ID (DEVICE_ID = 0x03 for MC6 MkII)
Byte  5: 00          Ignore
Byte  6: 70          Op1 (fixed for all write commands)
Byte  7: xx          Op2 (command selector)
Byte  8: xx          Op3 (command-specific operand)
Byte  9: xx          Op4 (command-specific operand)
Byte 10: xx          Op5 (command-specific operand)
Byte 11: xx          Op6 (command-specific operand)
Byte 12: xx          Op7 (command-specific operand)
Byte 13: xx          Transaction ID
Byte 14: 00          Ignore
Byte 15: 00          Ignore (or start of payload in some framing variants)
Byte 16+: [payload]  Variable-length payload
Byte n-1: cs         XOR checksum (XOR of all bytes from F0 through byte n-2, masked to 7 bits)
Byte n:  F7          SysEx end
```

[CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034]

### Op2=04h — Update Preset Message

This is the opcode used to write (or erase) a single message slot on a preset. The save flag lives at Op6 (byte 11):

```
Byte  7: 04          Op2 = Update Preset Message
Byte  8: xx          Op3 = Preset index (A=0, B=1, C=2, D=3, E=4, F=5)
Byte  9: xx          Op4 = Message slot number (0x00–0x0F)
Byte 10: xx          Op5 = Message type (00h=NOTHING, 01h=PC, 02h=CC, …)
Byte 11: xx          Op6 = Save flag (7F=write to flash, 00=active RAM only)
Byte 12: 00          Op7 (unused)
Byte 13: 00          Transaction ID
Byte 14: 00          Ignore
Byte 15: 00          Ignore
Byte 16+: [payload]  Message-type-specific data (empty for NOTHING)
```

[CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034]

**Message type `00h` (NOTHING):** No payload bytes. The message slot is considered empty.

**Save flag semantics:**
- `0x7F` — write the change to flash (survives power cycle, matches web UI behavior)
- `0x00` — write to active RAM only (change is visible immediately but lost on power cycle)

[CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034]

### Complete Op2 Opcode Inventory

There is no dedicated "clear all slots" opcode. The full opcode list confirms this:

| Op2 | Name | Purpose |
|-----|------|---------|
| `00h` | Controller Functions | Bank up/down, other navigation |
| `01h` | Update Preset Short Name | Set 8-char display name |
| `02h` | Update Preset Toggle Name | Set toggle state display name |
| `03h` | Update Preset Long Name | Set long name |
| `04h` | Update Preset Message | Write/clear one message slot |
| `05h` | Other Preset Data | Toggle, blink, scroll, group settings |
| `10h` | Update Current Bank Name | Set current bank name |
| `11h` | Display Message on LCD | Show temporary text on screen |
| `21h` | Get Preset Short Name | Query current short name |
| `22h` | Get Preset Toggle Name | Query toggle name |
| `23h` | Get Preset Long Name | Query long name |
| `30h` | Get Current Bank Name | Query bank name |
| `31h` | Get Toggle State Presets | Query toggle state |
| `32h` | Get Controller Information | Device info query |
| `7Fh` | Return/ACK | Response from MC6 |

[CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034]

**Finding:** To clear all 16 message slots, the protocol requires exactly 16 separate `04h` messages — one per slot. There is no batch-clear command. [CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034]

## Root Cause

The current `clear_preset_messages()` in `packages/rig-morningstar/src/rig_morningstar/sysex.py`:

```python
def clear_preset_messages(preset_idx: int, save: bool = False) -> list[list[int]]:
    """04h/00h — Set all 16 message slots on a preset to NOTHING, returning one message per slot."""
    save_byte = 0x7F if save else 0x00
    return [_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, []) for slot in range(16)]
```

The `_build` call maps correctly to the protocol:
- `op2=0x04` — correct opcode
- `op3=preset_idx` — correct preset index
- `op4=slot` — correct slot number (0–15)
- `op5=0x00` — correct: NOTHING message type
- `op6=save_byte` — correct byte position for save flag
- Empty payload — correct for NOTHING type

**The only defect is `save=False` as the default.** When `device.py` calls `clear_preset_messages(preset_idx)` without keyword arguments, `save_byte` becomes `0x00`, so Op6=`0x00`. The MC6 writes the NOTHING values into active RAM but does not flush to flash. The next power cycle reverts all slots to their pre-clear state.

The web UI always sends Op6=`0x7F` when clearing, writing directly to flash.

**Contrast with other builders:**

| Function | Save default | Op6 behavior |
|----------|-------------|--------------|
| `update_preset_pc()` | `save=True` | 0x7F — always persists |
| `update_preset_name()` | `save=True` | 0x7F — always persists |
| `clear_preset_messages()` | `save=False` | 0x00 — BUG: does not persist |

The comment in the existing test (`# save flag (default False — avoids MC6 bank navigation on rapid clears)`) reflects a historical theory that saving during clear triggers unwanted MC6 navigation behavior. This theory is unsubstantiated by the protocol documentation and contradicts the web UI's behavior. [ASSUMED — the comment's reasoning was not confirmed against actual MC6 hardware behavior]

## Correct Implementation

### Exact byte sequence the web UI sends (per slot)

For preset slot A (preset_idx=0), message slot 0:

```
F0 00 21 24 03 00 70 04 00 00 00 7F 00 00 00 00 [cs] F7
```

Where:
- Byte 7: `04` — Op2: Update Preset Message
- Byte 8: `00` — Op3: preset index 0 (switch A)
- Byte 9: `00` — Op4: message slot 0
- Byte 10: `00` — Op5: message type NOTHING
- Byte 11: `7F` — Op6: save to flash
- Bytes 12–15: `00 00 00 00` — Op7, txn, ignore, ignore
- No payload bytes (NOTHING type has empty payload)

For slot 1 through slot 15, only byte 9 (Op4) increments: `01`, `02`, … `0F`.

### Required `_build()` call

```python
_build(0x04, preset_idx, slot, 0x00, 0x7F, 0x00, 0x00, [])
```

### Fixed function

```python
def clear_preset_messages(preset_idx: int, save: bool = True) -> list[list[int]]:
    """04h/00h — Set all 16 message slots on a preset to NOTHING, returning one message per slot.

    save=True (default) writes to flash so changes survive power cycle — matching MC6 web UI behavior.
    Pass save=False only in tests or scenarios where temporary-only changes are intentional.
    """
    save_byte = 0x7F if save else 0x00
    return [_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, []) for slot in range(16)]
```

The only change is `save: bool = False` → `save: bool = True`. Body and return type are unchanged.

## Impact on device.py

**No change required.** `MC6Device.apply()` calls `clear_preset_messages(preset_idx)` without keyword arguments at line 109:

```python
for msg in clear_preset_messages(preset_idx):
    ctx.midi.send_sysex(self.id, msg)
```

With `save=True` as the new default, this call will automatically produce Op6=`0x7F` — no update to `device.py` is needed. The function signature is backward-compatible: any caller that explicitly passes `save=False` retains the old behavior.

## Test Changes

### Tests requiring updates

**File: `packages/rig/tests/test_mc6_sysex.py`**

Two assertions pin the save byte to `0x00` and must be updated to `0x7F`:

```python
# BEFORE (incorrect — tests the bug, not the correct behavior)
def test_clear_preset_messages_slot_sequence():
    msgs = clear_preset_messages(2)
    for slot, msg in enumerate(msgs):
        assert msg[7] == 0x04  # Op2 = 04h
        assert msg[8] == 0x02  # preset_idx
        assert msg[9] == slot  # msg_slot increments
        assert msg[10] == 0x00  # msgType = NOTHING
        assert (
            msg[11] == 0x00
        )  # save flag (default False — avoids MC6 bank navigation on rapid clears)
```

```python
# AFTER (correct — tests the fixed behavior)
def test_clear_preset_messages_slot_sequence():
    msgs = clear_preset_messages(2)
    for slot, msg in enumerate(msgs):
        assert msg[7] == 0x04   # Op2 = 04h
        assert msg[8] == 0x02   # preset_idx
        assert msg[9] == slot   # msg_slot increments
        assert msg[10] == 0x00  # msgType = NOTHING
        assert msg[11] == 0x7F  # save flag: default True — persists to flash (matches web UI)
```

### New tests to add

Add to `packages/rig/tests/test_mc6_sysex.py`:

```python
def test_clear_preset_messages_saves_by_default():
    """Default save=True writes to flash — matches MC6 web UI behavior."""
    msgs = clear_preset_messages(0)
    for msg in msgs:
        assert msg[11] == 0x7F  # Op6: save to flash


def test_clear_preset_messages_no_save_is_explicit():
    """Passing save=False produces temporary-only (RAM) clears."""
    msgs = clear_preset_messages(0, save=False)
    for msg in msgs:
        assert msg[11] == 0x00  # Op6: active RAM only
```

### Tests requiring NO changes

**File: `packages/rig-morningstar/tests/test_sysex.py`**

The existing `TestClearPresetMessages` tests are byte-agnostic — they only check `msg[0] == 0xF0`, `msg[-1] == 0xF7`, and `len(msgs) == 16`. These pass with both the current and fixed implementation and require no update.

## Standard Stack

No external packages are added by this phase. This is a pure protocol correctness fix.

| Component | Location | Change |
|-----------|----------|--------|
| `sysex.py` | `packages/rig-morningstar/src/rig_morningstar/sysex.py` | Change `save=False` → `save=True` in `clear_preset_messages` |
| `test_mc6_sysex.py` | `packages/rig/tests/test_mc6_sysex.py` | Update 1 assertion, add 2 new tests |
| `device.py` | `packages/rig-morningstar/src/rig_morningstar/device.py` | No change needed |
| `test_sysex.py` | `packages/rig-morningstar/tests/test_sysex.py` | No change needed |

## Common Pitfalls

### Pitfall 1: Changing the function signature unnecessarily

**What goes wrong:** Adding a new `clear_preset()` function with a different name, or removing the `save` parameter entirely, creates churn and breaks any existing test that calls `clear_preset_messages(preset_idx, save=False)` for temporary-only behavior.

**How to avoid:** The fix is a one-character change to the default value. Preserve the `save` parameter.

### Pitfall 2: Changing device.py unnecessarily

**What goes wrong:** Updating the `device.py` call to `clear_preset_messages(preset_idx, save=True)` is redundant once the default is fixed. It introduces noise and makes the code look like there was intentional choice at the call site.

**How to avoid:** Leave `device.py` unchanged.

### Pitfall 3: Confusing Op6 position between opcodes

**What goes wrong:** For `Op2=01h` (Update Short Name), the save flag lives at Op4 (byte 9). For `Op2=04h` (Update Preset Message), the save flag lives at Op6 (byte 11). Misreading one opcode's layout as the other leads to writing the save flag to the wrong byte.

**How to avoid:** The existing `_build` call for `clear_preset_messages` is already correct: `_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, [])` places `save_byte` at position 5 in the operand list → Op6 → byte 11. Verify with the test assertion `msg[11]`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Checksum | Custom XOR loop | `_checksum()` — already in `sysex.py` |
| Frame construction | Custom byte array | `_build()` — already in `sysex.py` |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest packages/rig/tests/test_mc6_sysex.py packages/rig-morningstar/tests/test_sysex.py -q` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MC6-01 | Default clear writes save=0x7F to flash | unit | `uv run pytest packages/rig/tests/test_mc6_sysex.py::test_clear_preset_messages_saves_by_default -x` | Wave 0 gap |
| MC6-01 | Explicit save=False produces 0x00 save byte | unit | `uv run pytest packages/rig/tests/test_mc6_sysex.py::test_clear_preset_messages_no_save_is_explicit -x` | Wave 0 gap |
| MC6-01 | Slot sequence, opcode, and type bytes unchanged | unit | `uv run pytest packages/rig/tests/test_mc6_sysex.py::test_clear_preset_messages_slot_sequence -x` | exists (needs assertion update) |

### Wave 0 Gaps

- [ ] `test_clear_preset_messages_saves_by_default` — new test, covers MC6-01 flash persistence
- [ ] `test_clear_preset_messages_no_save_is_explicit` — new test, covers explicit save=False path

## Security Domain

This phase modifies MIDI SysEx byte sequences sent to a local hardware device. There are no network calls, user input paths, authentication surfaces, or data storage concerns. ASVS categories V2–V6 do not apply.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The historical comment "avoids MC6 bank navigation on rapid clears" is unsubstantiated — save=True does not trigger bank navigation | Root Cause | If save=True does trigger unwanted MC6 behavior, the fix would require a different approach (e.g., save only on the final slot, or add a delay between messages) |

## Open Questions

1. **Does save=True on all 16 clear messages trigger unwanted MC6 bank navigation?**
   - What we know: The protocol documentation makes no mention of save=True causing side effects
   - What's unclear: The historical comment in `test_mc6_sysex.py` suggests this was a concern at some point
   - Recommendation: Proceed with the fix (save=True default). If MC6 misbehaves on hardware test, consider sending save=False for slots 0–14 and save=True only for slot 15 (or no-save on all slots and a separate "save bank" command if one exists)

## Sources

### Primary (HIGH confidence)
- [CITED: https://helpdesk.morningstar.io/support/solutions/articles/43000681034] — Morningstar MC6 MkII SysEx protocol; Op2=04h byte layout, save flag at Op6, NOTHING type, full opcode table
- `packages/rig-morningstar/src/rig_morningstar/sysex.py` — current implementation, verified via direct file read
- `packages/rig/tests/test_mc6_sysex.py` — existing test assertions, verified via direct file read
- GitHub issue #17 — problem statement, confirmed no SysEx capture exists yet

### Metadata

**Confidence breakdown:**
- Protocol byte layout: HIGH — fetched from official Morningstar docs
- Root cause (save=False default): HIGH — confirmed by cross-referencing protocol docs with source code byte-by-byte
- No single-clear opcode: HIGH — confirmed by exhaustive opcode table from official docs
- Historical comment about navigation side effects: LOW — unverified, flagged as assumed

**Research date:** 2026-06-22
**Valid until:** Stable — protocol docs are versioned to MC6 MkII firmware; changes only if Morningstar updates the SysEx spec
