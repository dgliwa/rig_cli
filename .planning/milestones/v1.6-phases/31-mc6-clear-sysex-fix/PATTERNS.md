# Phase 31: MC6 Clear SysEx Fix - Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 2 (sysex.py, test_mc6_sysex.py)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/rig-morningstar/src/rig_morningstar/sysex.py` | utility | transform | `update_preset_name`, `update_preset_pc` in same file | exact |
| `packages/rig/tests/test_mc6_sysex.py` | test | request-response | `packages/rig-morningstar/tests/test_sysex.py` | exact |

## Pattern Assignments

### `sysex.py` — `clear_preset_messages` default parameter fix

**File:** `packages/rig-morningstar/src/rig_morningstar/sysex.py`

**Analog patterns from same file** (lines 50-82):

`update_preset_name` signature with `save=True` (line 50):
```python
def update_preset_name(preset_idx: int, name: str, save: bool = True) -> list[int]:
```

`update_preset_pc` signature with `save=True` (lines 57-62):
```python
def update_preset_pc(
    preset_idx: int,
    msg_slot: int,
    pc_number: int,
    midi_channel: int,
    save: bool = True,
) -> list[int]:
```

`clear_preset_messages` current (broken) signature (line 79):
```python
def clear_preset_messages(preset_idx: int, save: bool = False) -> list[list[int]]:
```

`save_byte` compute pattern used in all three functions (lines 54, 76, 81):
```python
# update_preset_name
return _build(0x01, preset_idx, 0x7F if save else 0x00, ...)

# update_preset_pc
return _build(0x04, preset_idx, msg_slot, 0x01, 0x7F if save else 0x00, ...)

# clear_preset_messages
save_byte = 0x7F if save else 0x00
return [_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, []) for slot in range(16)]
```

**Fix:** Change line 79 default from `save: bool = False` to `save: bool = True`.

---

### `test_mc6_sysex.py` — byte 11 assertion fix

**File:** `packages/rig/tests/test_mc6_sysex.py`

**Analog:** `packages/rig-morningstar/tests/test_sysex.py`

**Existing save-flag assertion pattern** (`test_sysex.py` lines 60-61, 74-75):
```python
# update_preset_pc save=True (default)
assert msg[11] == 0x7F  # save flag

# update_preset_pc save=False (explicit)
def test_update_preset_pc_no_save():
    msg = update_preset_pc(0, 0, 0, 1, save=False)
    assert msg[11] == 0x00  # save flag off
```

**Current (broken) clear test in `test_sysex.py`** (lines 83-92):
```python
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

**Fix for `test_mc6_sysex.py`:** Any assertion on the clear message byte 11 that currently expects `0x00` must be updated to `0x7F`. Same applies to the comment in `test_sysex.py` if that test is also updated.

Byte position reference (from `update_preset_pc` test at line 54-65):
```
msg[7]  = Op2 opcode
msg[8]  = preset_idx
msg[9]  = msg_slot
msg[10] = msgType (0x00 = NOTHING, 0x01 = PC)
msg[11] = save flag (0x7F = save, 0x00 = no save)
msg[16:] = payload bytes
```

---

## Shared Patterns

### Save flag byte encoding
**Source:** `packages/rig-morningstar/src/rig_morningstar/sysex.py` lines 54, 76, 81
**Apply to:** `clear_preset_messages` fix

```python
0x7F if save else 0x00
```

`save=True` encodes as `0x7F`; `save=False` encodes as `0x00`. The fix changes the default from `False` to `True`, aligning `clear_preset_messages` with `update_preset_name` and `update_preset_pc`.

### Test byte-position assertion style
**Source:** `packages/rig-morningstar/tests/test_sysex.py` lines 54-75
**Apply to:** `test_mc6_sysex.py` assertion update

```python
assert msg[11] == 0x7F  # save flag
```

Comments explain the semantic meaning of each byte position. When updating the assertion, update the inline comment to remove the old rationale and reflect the new default.

## No Analog Found

None — both files have direct in-codebase analogs.

## Metadata

**Analog search scope:** `packages/rig-morningstar/src/`, `packages/rig-morningstar/tests/`, `packages/rig/tests/`
**Files scanned:** 2
**Pattern extraction date:** 2026-06-22
