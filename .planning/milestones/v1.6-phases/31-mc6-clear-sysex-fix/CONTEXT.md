# Phase 31: MC6 Clear SysEx Fix — Context

## Phase Goal

`rig apply` sends the correct SysEx sequence when clearing an MC6 switch slot — matching exactly what the MC6 web UI sends.

## Requirement

**MC6-01** (v1.6): `rig apply` clearing a switch slot emits the same SysEx byte sequence the MC6 web UI emits when a user clicks "Clear" on a preset slot.

## Problem Statement

The current `clear_preset_messages()` in `packages/rig-morningstar/src/rig_morningstar/sysex.py` sends 16 individual SysEx messages (one per message slot, 0–15) using op2=0x04, setting each slot type to 0x00 (NOTHING) with `save=False` by default.

The MC6 web UI sends a different byte sequence when clearing a preset slot (tracked in GitHub issue #17). The specific discrepancy is unknown until the captured SysEx from the web UI is consulted, but likely candidates are:
- A dedicated "clear preset" opcode rather than 16 individual slot-write commands
- The save byte: current code defaults to `save=False` (0x00), but web UI may always save (0x7F)
- Different message structure or payload layout

## Files in Scope

| File | Change |
|------|--------|
| `packages/rig-morningstar/src/rig_morningstar/sysex.py` | Fix `clear_preset_messages()` to match web UI byte sequence; possibly add a new `clear_preset()` function |
| `packages/rig-morningstar/src/rig_morningstar/device.py` | Update `MC6Device.apply()` to call the corrected clear function |
| `packages/rig-morningstar/tests/test_sysex.py` | Update/add tests covering the correct clear sequence |
| `packages/rig/tests/test_mc6_sysex.py` | Update/add integration tests if they reference clear behavior |

## Success Criteria

1. Captured SysEx from MC6 web UI "clear" action is documented and reproduced in `rig-morningstar`
2. `rig apply` clearing a switch slot sends the identical byte sequence the web UI sends
3. Existing MC6 SysEx tests updated to cover the correct clear case

## Architecture Context

- Protocol reference: https://helpdesk.morningstar.io/support/solutions/articles/43000681034
- `DEVICE_ID = 0x03` (MC6 MkII)
- `_build(op2, op3, op4, op5, op6, op7, txn, payload)` assembles all SysEx messages with F0/F7 framing + XOR checksum
- `clear_preset_messages(preset_idx)` currently returns `list[list[int]]` — 16 messages
- `MC6Device.apply()` in `device.py` calls `clear_preset_messages(preset_idx)` in a loop before writing scene data
- `SWITCH_INDEX = {"A": 0, ..., "F": 5}` maps switch labels to preset indices 0–5

## Current `clear_preset_messages` Implementation

```python
def clear_preset_messages(preset_idx: int, save: bool = False) -> list[list[int]]:
    """04h/00h — Set all 16 message slots on a preset to NOTHING, returning one message per slot."""
    save_byte = 0x7F if save else 0x00
    return [_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, []) for slot in range(16)]
```

Key observation: `save=False` means these messages don't persist to MC6 flash — a likely bug if the web UI always saves.

## Key Question

What does the MC6 web UI actually send when clearing a preset slot? The Morningstar SysEx protocol docs (linked above) describe all available opcodes. The researcher should fetch and analyze these docs to determine the correct "clear" command structure.
