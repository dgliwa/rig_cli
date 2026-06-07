from rig.models.device import Control, ControlType

MOOD_MKII_CONTROLS: list[Control] = [
    Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127),
    Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    Control(name="length", type=ControlType.KNOB, midi_cc=16, min=0, max=127),
    Control(name="wet_modify", type=ControlType.KNOB, midi_cc=17, min=0, max=127),
    Control(name="clock", type=ControlType.KNOB, midi_cc=18, min=0, max=127),
    Control(name="loop_modify", type=ControlType.KNOB, midi_cc=19, min=0, max=127),
    Control(name="ramp_speed", type=ControlType.KNOB, midi_cc=20, min=0, max=127),
    Control(name="wet_channel", type=ControlType.TOGGLE, midi_cc=21, min=0, max=127, positions=["reverb", "delay", "slip"]),
    Control(name="routing", type=ControlType.TOGGLE, midi_cc=22, min=0, max=127, positions=["in", "wet_and_in", "wet"]),
    Control(name="loop", type=ControlType.TOGGLE, midi_cc=23, min=0, max=127, positions=["env", "tape", "stretch"]),
    Control(name="wet_clock", type=ControlType.TOGGLE, midi_cc=53, min=0, max=7, positions=["32nd", "16th", "eighth_triplet", "eighth", "dotted_eighth", "quarter", "half", "whole"]),
    Control(name="loop_clock_division", type=ControlType.TOGGLE, midi_cc=54, min=0, max=7, positions=["32nd", "16th", "eighth_triplet", "eighth", "dotted_eighth", "quarter", "half", "whole"]),
    Control(name="true_bypass", type=ControlType.SWITCH, midi_cc=55, min=0, max=127),
    Control(name="micro_bypass", type=ControlType.SWITCH, midi_cc=102, min=0, max=127),
    Control(name="wet_bypass", type=ControlType.SWITCH, midi_cc=103, min=0, max=127),
    Control(name="freeze", type=ControlType.SWITCH, midi_cc=105, min=0, max=127),
    Control(name="loop_overdub", type=ControlType.SWITCH, midi_cc=106, min=0, max=127),
    Control(name="tap_tempo", type=ControlType.SWITCH, midi_cc=107, min=0, max=127),
    Control(name="dip_l_time", type=ControlType.DIPSWITCH, midi_cc=61, min=0, max=127),
    Control(name="dip_l_wet_modify", type=ControlType.DIPSWITCH, midi_cc=62, min=0, max=127),
    Control(name="dip_l_clock", type=ControlType.DIPSWITCH, midi_cc=63, min=0, max=127),
    Control(name="dip_l_loop_modify", type=ControlType.DIPSWITCH, midi_cc=64, min=0, max=127),
    Control(name="dip_l_length", type=ControlType.DIPSWITCH, midi_cc=65, min=0, max=127),
    Control(name="dip_l_bounce", type=ControlType.DIPSWITCH, midi_cc=66, min=0, max=127),
    Control(name="dip_l_sweep", type=ControlType.DIPSWITCH, midi_cc=67, min=0, max=127),
    Control(name="dip_l_polarity", type=ControlType.DIPSWITCH, midi_cc=68, min=0, max=127),
    Control(name="dip_r_classic", type=ControlType.DIPSWITCH, midi_cc=71, min=0, max=127),
    Control(name="dip_r_miso", type=ControlType.DIPSWITCH, midi_cc=72, min=0, max=127),
    Control(name="dip_r_spread", type=ControlType.DIPSWITCH, midi_cc=73, min=0, max=127),
    Control(name="dip_r_dry_kill", type=ControlType.DIPSWITCH, midi_cc=74, min=0, max=127),
    Control(name="dip_r_trails", type=ControlType.DIPSWITCH, midi_cc=75, min=0, max=127),
    Control(name="dip_r_latch", type=ControlType.DIPSWITCH, midi_cc=76, min=0, max=127),
    Control(name="dip_r_no_dub", type=ControlType.DIPSWITCH, midi_cc=77, min=0, max=127),
    Control(name="dip_r_smooth", type=ControlType.DIPSWITCH, midi_cc=78, min=0, max=127),
]

_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
}


def get_controls(manufacturer: str, model: str) -> list[Control]:
    return _CATALOG.get(f"{manufacturer}/{model}", [])
