"""SysEx message builders for the Morningstar MC6 MkII.

Protocol: https://helpdesk.morningstar.io/support/solutions/articles/43000681034

Commands operate on the currently active bank — callers must navigate
to the correct bank before calling write functions.
"""

from __future__ import annotations

DEVICE_ID = 0x03  # MC6 MkII
SHORT_NAME_MAX = 8

SWITCH_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}


def _checksum(msg: list[int]) -> int:
    """XOR all bytes in msg (including F0), mask to 7-bit."""
    result = 0
    for b in msg:
        result ^= b
    return result & 0x7F


def _build(
    op2: int, op3: int, op4: int, op5: int, op6: int, op7: int, txn: int, payload: list[int]
) -> list[int]:
    """Assemble a complete SysEx message including F0/F7 framing and checksum."""
    body = [
        0xF0,
        0x00,
        0x21,
        0x24,
        DEVICE_ID,
        0x00,
        0x70,
        op2,
        op3,
        op4,
        op5,
        op6,
        op7,
        txn,
        0x00,
        0x00,
    ] + payload
    return body + [_checksum(body), 0xF7]


def update_preset_name(preset_idx: int, name: str, save: bool = True) -> list[int]:
    """01h — Set the short name for a preset slot (A=0 … F=5)."""
    name_bytes = list(name.encode("ascii")[:SHORT_NAME_MAX])
    name_bytes += [0x20] * (SHORT_NAME_MAX - len(name_bytes))
    return _build(0x01, preset_idx, 0x7F if save else 0x00, 0x00, 0x00, 0x00, 0x00, name_bytes)


def update_preset_pc(
    preset_idx: int,
    msg_slot: int,
    pc_number: int,
    midi_channel: int,
    save: bool = True,
) -> list[int]:
    """04h — Write a Program Change into one message slot of a preset.

    midi_channel is 1-indexed (1–16); the Morningstar SysEx protocol uses the
    same 1-indexed convention, so it is written directly to the payload.
    msg_slot is 0–15.
    """
    payload = [
        0x01,  # Action Type: PRESS
        0x00,  # Toggle Type: POS 1
        pc_number,
        midi_channel,  # SysEx uses 1-indexed channels (1-16)
    ]
    return _build(0x04, preset_idx, msg_slot, 0x01, 0x7F if save else 0x00, 0x00, 0x00, payload)


def clear_preset_messages(preset_idx: int, save: bool = True) -> list[list[int]]:
    """04h/00h — Set all 16 message slots on a preset to NOTHING, returning one message per slot.

    save=True (default): Op6=0x7F writes to flash, matching MC6 web UI behaviour.
    save=False: Op6=0x00 keeps change in RAM only (lost on power cycle).
    """
    save_byte = 0x7F if save else 0x00
    return [_build(0x04, preset_idx, slot, 0x00, save_byte, 0x00, 0x00, []) for slot in range(16)]


def bank_down() -> list[int]:
    """00h/01h — Navigate the MC6 one bank down."""
    return _build(0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, [])
