from rig_chasebliss.catalog import Control, ControlType
from rig_chasebliss.device import ChaseBlissDevice, validate_cc_params


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


def test_from_raw_yaml_known_model_populates_controls():
    device = ChaseBlissDevice.from_raw_yaml(
        {"id": "mood", "name": "Mood MkII", "config": {"type": "chase_bliss", "model": "Mood MkII"}}
    )
    assert len(device.config.controls) > 0
    assert any(c.name == "time" for c in device.config.controls)


def test_from_raw_yaml_unknown_model_leaves_controls_empty():
    device = ChaseBlissDevice.from_raw_yaml(
        {
            "id": "x",
            "name": "Unknown",
            "config": {"type": "chase_bliss", "model": "Nonexistent Model"},
        }
    )
    assert device.config.controls == []


def test_from_raw_yaml_explicit_controls_not_overwritten():
    explicit = [{"name": "volume", "type": "knob", "midi_cc": 15}]
    device = ChaseBlissDevice.from_raw_yaml(
        {
            "id": "mood",
            "name": "Mood MkII",
            "config": {"type": "chase_bliss", "model": "Mood MkII", "controls": explicit},
        }
    )
    assert len(device.config.controls) == 1
    assert device.config.controls[0].name == "volume"


def test_from_raw_yaml_no_model_leaves_controls_empty():
    device = ChaseBlissDevice.from_raw_yaml(
        {"id": "x", "name": "Mystery", "config": {"type": "chase_bliss"}}
    )
    assert device.config.controls == []
