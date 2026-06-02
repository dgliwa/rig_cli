from rig.models.pedal import Control, ControlType

MOOD_MKII_CONTROLS: list[Control] = [
    Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127),
    Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
    Control(name="length", type=ControlType.KNOB, midi_cc=16, min=0, max=127),
    Control(name="wet_modify", type=ControlType.KNOB, midi_cc=17, min=0, max=127),
    Control(name="clock", type=ControlType.KNOB, midi_cc=18, min=0, max=127),
    Control(name="micro_looper_modify", type=ControlType.KNOB, midi_cc=19, min=0, max=127),
    Control(name="ramp_speed", type=ControlType.KNOB, midi_cc=20, min=0, max=127),
    Control(name="wet_bypass", type=ControlType.SWITCH, midi_cc=103, min=0, max=127),
    Control(name="micro_bypass", type=ControlType.SWITCH, midi_cc=102, min=0, max=127),
    # Left dip switch bank (CC 61–68)
    Control(name="dip_l_1", type=ControlType.DIPSWITCH, midi_cc=61, min=0, max=127),
    Control(name="dip_l_2", type=ControlType.DIPSWITCH, midi_cc=62, min=0, max=127),
    Control(name="dip_l_3", type=ControlType.DIPSWITCH, midi_cc=63, min=0, max=127),
    Control(name="dip_l_4", type=ControlType.DIPSWITCH, midi_cc=64, min=0, max=127),
    Control(name="dip_l_5", type=ControlType.DIPSWITCH, midi_cc=65, min=0, max=127),
    Control(name="dip_l_6", type=ControlType.DIPSWITCH, midi_cc=66, min=0, max=127),
    Control(name="dip_l_7", type=ControlType.DIPSWITCH, midi_cc=67, min=0, max=127),
    Control(name="dip_l_8", type=ControlType.DIPSWITCH, midi_cc=68, min=0, max=127),
    # Right dip switch bank (CC 71–78)
    Control(name="dip_r_1", type=ControlType.DIPSWITCH, midi_cc=71, min=0, max=127),
    Control(name="dip_r_2", type=ControlType.DIPSWITCH, midi_cc=72, min=0, max=127),
    Control(name="dip_r_3", type=ControlType.DIPSWITCH, midi_cc=73, min=0, max=127),
    Control(name="dip_r_4", type=ControlType.DIPSWITCH, midi_cc=74, min=0, max=127),
    Control(name="dip_r_5", type=ControlType.DIPSWITCH, midi_cc=75, min=0, max=127),
    Control(name="dip_r_6", type=ControlType.DIPSWITCH, midi_cc=76, min=0, max=127),
    Control(name="dip_r_7", type=ControlType.DIPSWITCH, midi_cc=77, min=0, max=127),
    Control(name="dip_r_8", type=ControlType.DIPSWITCH, midi_cc=78, min=0, max=127),
]

_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
}


def get_controls(manufacturer: str, model: str) -> list[Control]:
    return _CATALOG.get(f"{manufacturer}/{model}", [])
