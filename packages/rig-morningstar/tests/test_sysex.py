from __future__ import annotations

from rig_morningstar.sysex import (
    SWITCH_INDEX,
    bank_down,
    clear_preset_messages,
    update_preset_name,
    update_preset_pc,
)


class TestSwitchIndex:
    def test_all_six_switches_defined(self):
        assert set(SWITCH_INDEX.keys()) == {"A", "B", "C", "D", "E", "F"}

    def test_values_are_sequential(self):
        assert list(SWITCH_INDEX.values()) == [0, 1, 2, 3, 4, 5]


class TestUpdatePresetName:
    def test_returns_nonempty_sysex(self):
        msg = update_preset_name(0, "Clean")
        assert msg[0] == 0xF0
        assert msg[-1] == 0xF7
        assert len(msg) > 16

    def test_long_name_truncated_to_8_chars(self):
        msg = update_preset_name(0, "A" * 20)
        msg_short = update_preset_name(0, "A" * 8)
        assert msg == msg_short


class TestUpdatePresetPc:
    def test_returns_nonempty_sysex(self):
        msg = update_preset_pc(0, 0, 12, 1)
        assert msg[0] == 0xF0
        assert msg[-1] == 0xF7


class TestClearPresetMessages:
    def test_returns_16_messages(self):
        msgs = clear_preset_messages(0)
        assert len(msgs) == 16

    def test_each_is_valid_sysex(self):
        for msg in clear_preset_messages(2):
            assert msg[0] == 0xF0
            assert msg[-1] == 0xF7


class TestBankDown:
    def test_returns_valid_sysex(self):
        msg = bank_down()
        assert msg[0] == 0xF0
        assert msg[-1] == 0xF7
