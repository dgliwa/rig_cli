"""Tests for MC6 SysEx message builders."""

from rig.midi.mc6 import (
    DEVICE_ID,
    _build,
    _checksum,
    clear_preset_messages,
    update_preset_name,
    update_preset_pc,
)


def test_checksum_xors_all_bytes_and_masks():
    assert _checksum([0xF0, 0x00, 0x21, 0x24]) == (0xF0 ^ 0x00 ^ 0x21 ^ 0x24) & 0x7F


def test_checksum_always_7bit():
    result = _checksum(list(range(16)))
    assert 0 <= result <= 127


def test_build_framing():
    msg = _build(0x01, 0x00, 0x7F, 0x00, 0x00, 0x00, 0x00, [])
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    assert msg[4] == DEVICE_ID
    assert msg[6] == 0x70  # Op1 fixed


def test_build_checksum_is_valid():
    msg = _build(0x01, 0x02, 0x7F, 0x00, 0x00, 0x00, 0x00, [0x41, 0x42])
    body = msg[:-2]  # everything before checksum and F7
    expected_cs = _checksum(body)
    assert msg[-2] == expected_cs


def test_update_preset_name_opcode_and_padding():
    msg = update_preset_name(0, "CLEAN")
    assert msg[7] == 0x01  # Op2 = 01h
    assert msg[8] == 0x00  # preset_idx A = 0
    assert msg[9] == 0x7F  # save flag
    payload = msg[16:-2]
    assert payload[:5] == list("CLEAN".encode("ascii"))
    assert payload[5:8] == [0x20, 0x20, 0x20]  # padded with spaces
    assert len(payload) == 8


def test_update_preset_name_truncates_at_8():
    msg = update_preset_name(1, "TOOLONGNAME")
    payload = msg[16:-2]
    assert len(payload) == 8


def test_update_preset_pc_opcode_and_payload():
    msg = update_preset_pc(preset_idx=0, msg_slot=0, pc_number=3, midi_channel=2)
    assert msg[7] == 0x04  # Op2 = 04h
    assert msg[8] == 0x00  # preset_idx
    assert msg[9] == 0x00  # msg_slot
    assert msg[10] == 0x01  # msgType = PC
    assert msg[11] == 0x7F  # save flag
    payload = msg[16:-2]
    assert payload[0] == 0x01  # PRESS
    assert payload[1] == 0x00  # POS 1
    assert payload[2] == 3  # pc_number
    assert payload[3] == 2  # channel 2 → 1-indexed = 2


def test_update_preset_pc_channel_one_indexed():
    msg = update_preset_pc(0, 0, 0, midi_channel=1)
    assert msg[16 + 3] == 1  # channel 1 → 1-indexed = 1


def test_update_preset_pc_no_save():
    msg = update_preset_pc(0, 0, 0, 1, save=False)
    assert msg[11] == 0x00  # save flag off


def test_clear_preset_messages_returns_16():
    msgs = clear_preset_messages(0)
    assert len(msgs) == 16


def test_clear_preset_messages_slot_sequence():
    msgs = clear_preset_messages(2)
    for slot, msg in enumerate(msgs):
        assert msg[7] == 0x04  # Op2 = 04h
        assert msg[8] == 0x02  # preset_idx
        assert msg[9] == slot  # msg_slot increments
        assert msg[10] == 0x00  # msgType = NOTHING
        assert msg[11] == 0x7F  # save flag
