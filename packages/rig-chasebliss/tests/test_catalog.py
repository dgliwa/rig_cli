from rig_chasebliss.catalog import (
    BROTHERS_AM_CONTROLS,
    MOOD_MKII_CONTROLS,
    MOOD_MKII_LOOP_BYPASS_CC,
    MOOD_MKII_WET_BYPASS_CC,
    WOMBTONE_MKII_CONTROLS,
    Control,
    ControlType,
    get_controls,
)


def test_control_default_field_accepts_none():
    c = Control(name="x", type=ControlType.KNOB)
    assert c.default is None


def test_control_default_field_accepts_float():
    c = Control(name="x", type=ControlType.KNOB, default=64.0)
    assert c.default == 64.0


def test_control_default_field_accepts_zero():
    c = Control(name="x", type=ControlType.KNOB, default=0)
    assert c.default == 0


def test_mood_cc102_named_wet_bypass():
    ccs = {c.midi_cc: c for c in MOOD_MKII_CONTROLS}
    assert ccs[MOOD_MKII_WET_BYPASS_CC].name == "wet_bypass"


def test_mood_cc103_named_loop_bypass():
    ccs = {c.midi_cc: c for c in MOOD_MKII_CONTROLS}
    assert ccs[MOOD_MKII_LOOP_BYPASS_CC].name == "loop_bypass"


def test_mood_switch_controls_have_default_none():
    for c in MOOD_MKII_CONTROLS:
        if c.type == ControlType.SWITCH:
            assert c.default is None, f"SWITCH {c.name} default should be None, got {c.default}"


def test_mood_knob_controls_have_numeric_default():
    for c in MOOD_MKII_CONTROLS:
        if c.type == ControlType.KNOB:
            assert c.default is not None, f"KNOB {c.name} has no default"
            assert isinstance(c.default, (int, float))


def test_mood_missing_ccs_are_present():
    present = {c.midi_cc for c in MOOD_MKII_CONTROLS}
    for cc in [24, 25, 26, 27, 28, 29, 31, 32, 33, 52]:
        assert cc in present, f"CC{cc} missing from MOOD_MKII_CONTROLS"


def test_wombtone_has_parameter_controls_cc14_to_21():
    present = {c.midi_cc for c in WOMBTONE_MKII_CONTROLS}
    for cc in range(14, 22):
        assert cc in present, f"Wombtone CC{cc} missing"


def test_brothers_knobs_have_default_64():
    for c in BROTHERS_AM_CONTROLS:
        if c.type == ControlType.KNOB:
            assert c.default == 64, f"Brothers KNOB {c.name} default={c.default}"


def test_brothers_dipswitches_have_default_0():
    for c in BROTHERS_AM_CONTROLS:
        if c.type == ControlType.DIPSWITCH:
            assert c.default == 0, f"Brothers DIPSWITCH {c.name} default={c.default}"


def test_get_controls_wombtone_returns_nonempty():
    assert len(get_controls("Chase Bliss Audio", "Wombtone MkII")) > 0


def test_get_controls_brothers_returns_nonempty():
    assert len(get_controls("Chase Bliss Audio", "Brothers AM")) > 0


def test_get_controls_unknown_returns_empty_list():
    assert get_controls("unknown", "pedal") == []


def test_mood_wet_bypass_cc_value_is_102():
    assert MOOD_MKII_WET_BYPASS_CC == 102


def test_mood_loop_bypass_cc_value_is_103():
    assert MOOD_MKII_LOOP_BYPASS_CC == 103
