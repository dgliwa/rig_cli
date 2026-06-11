from rig_chasebliss.catalog import Control, ControlType
from rig_chasebliss.device import ChaseBlissDevice, _get_cc_params, validate_cc_params


def test_validate_valid_params():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
        Control(name="mix", type=ControlType.KNOB, midi_cc=16, min=0, max=127),
    ]
    assert validate_cc_params({"volume": 64, "mix": 100}, controls) == []


def test_validate_unknown_param():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    ]
    errs = validate_cc_params({"nonexistent": 0}, controls)
    assert len(errs) == 1
    assert "nonexistent" in errs[0]


def test_validate_out_of_range_high():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    ]
    errs = validate_cc_params({"volume": 999}, controls)
    assert len(errs) == 1
    assert "out of range" in errs[0]


def test_validate_out_of_range_low():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    ]
    errs = validate_cc_params({"volume": -5}, controls)
    assert len(errs) == 1
    assert "out of range" in errs[0]


def test_validate_toggle_position_string():
    controls = [
        Control(
            name="channel",
            type=ControlType.TOGGLE,
            midi_cc=21,
            min=0,
            max=3,
            positions=["a", "b", "c"],
        ),
    ]
    assert validate_cc_params({"channel": "b"}, controls) == []


def test_validate_toggle_position_string_invalid():
    controls = [
        Control(
            name="channel",
            type=ControlType.TOGGLE,
            midi_cc=21,
            min=0,
            max=3,
            positions=["a", "b", "c"],
        ),
    ]
    errs = validate_cc_params({"channel": "z"}, controls)
    assert len(errs) == 1
    assert "not a valid position" in errs[0]


def test_validate_toggle_position_index_out_of_range():
    controls = [
        Control(
            name="channel",
            type=ControlType.TOGGLE,
            midi_cc=21,
            min=0,
            max=3,
            positions=["a", "b", "c"],
        ),
    ]
    errs = validate_cc_params({"channel": 99}, controls)
    assert len(errs) == 1
    assert "out of range" in errs[0]


def test_validate_empty_params():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    ]
    assert validate_cc_params({}, controls) == []


def test_validate_multiple_errors():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
        Control(name="mix", type=ControlType.KNOB, midi_cc=16, min=0, max=127),
    ]
    errs = validate_cc_params({"bad1": 0, "bad2": 1, "bad3": 2}, controls)
    assert len(errs) == 3


def test_validate_min_max_not_applicable():
    controls = [
        Control(name="volume", type=ControlType.KNOB, midi_cc=15),
        Control(name="switch", type=ControlType.SWITCH, midi_cc=55),
    ]
    # min and max are None — should not crash
    assert validate_cc_params({"volume": 64, "switch": 0}, controls) == []


def test_get_cc_params_threshold_toggle_by_index():
    # Mood MkII-style: ENV=0-1, TAPE=2, STRETCH=>2 — index 1 must send 2, not 1
    controls = [
        Control(
            name="loop",
            type=ControlType.TOGGLE,
            midi_cc=23,
            positions=["env", "tape", "stretch"],
            position_cc_values=[0, 2, 3],
        ),
    ]
    assert _get_cc_params({"loop": 0}, controls) == [{"cc": 23, "value": 0}]
    assert _get_cc_params({"loop": 1}, controls) == [{"cc": 23, "value": 2}]
    assert _get_cc_params({"loop": 2}, controls) == [{"cc": 23, "value": 3}]


def test_get_cc_params_threshold_toggle_by_name():
    controls = [
        Control(
            name="loop",
            type=ControlType.TOGGLE,
            midi_cc=23,
            positions=["env", "tape", "stretch"],
            position_cc_values=[0, 2, 3],
        ),
    ]
    assert _get_cc_params({"loop": "env"}, controls) == [{"cc": 23, "value": 0}]
    assert _get_cc_params({"loop": "tape"}, controls) == [{"cc": 23, "value": 2}]
    assert _get_cc_params({"loop": "stretch"}, controls) == [{"cc": 23, "value": 3}]


def test_get_cc_params_indexed_toggle_no_cc_values():
    # Clock divisions are 1:1 indexed — no position_cc_values, falls back to index
    controls = [
        Control(
            name="wet_clock",
            type=ControlType.TOGGLE,
            midi_cc=53,
            positions=["32nd", "16th", "eighth", "quarter"],
        ),
    ]
    assert _get_cc_params({"wet_clock": 3}, controls) == [{"cc": 53, "value": 3}]


def test_get_cc_params_knob_passthrough():
    controls = [
        Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127),
    ]
    assert _get_cc_params({"time": 95}, controls) == [{"cc": 14, "value": 95}]


def test_from_raw_yaml_known_model_stores_model_name():
    device = ChaseBlissDevice.from_raw_yaml(
        {"id": "mood", "name": "Mood MkII", "config": {"type": "chase_bliss", "model": "Mood MkII"}}
    )
    assert device.config.model == "Mood MkII"
    assert not hasattr(device.config, "controls")


def test_from_raw_yaml_unknown_model_stores_model_name():
    device = ChaseBlissDevice.from_raw_yaml(
        {
            "id": "x",
            "name": "Unknown",
            "config": {"type": "chase_bliss", "model": "Nonexistent Model"},
        }
    )
    assert device.config.model == "Nonexistent Model"


def test_from_raw_yaml_controls_in_yaml_are_ignored():
    # ChaseBlissConfig has extra="ignore" — controls key is silently dropped
    explicit = [{"name": "volume", "type": "knob", "midi_cc": 15}]
    device = ChaseBlissDevice.from_raw_yaml(
        {
            "id": "mood",
            "name": "Mood MkII",
            "config": {"type": "chase_bliss", "model": "Mood MkII", "controls": explicit},
        }
    )
    assert not hasattr(device.config, "controls")


def test_from_raw_yaml_no_model_is_none():
    device = ChaseBlissDevice.from_raw_yaml(
        {"id": "x", "name": "Mystery", "config": {"type": "chase_bliss"}}
    )
    assert device.config.model is None
