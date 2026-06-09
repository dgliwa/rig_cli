from enum import StrEnum

from pydantic import BaseModel, Field


class ControlType(StrEnum):
    KNOB = "knob"
    SWITCH = "switch"
    TOGGLE = "toggle"
    DIPSWITCH = "dipswitch"


class Control(BaseModel):
    name: str = Field(..., min_length=1)
    type: ControlType
    midi_cc: int | None = None
    min: float | str | bool | None = None
    max: float | str | bool | None = None
    positions: list[int | str] = []
    expression_assignable: bool = False
    default: float | None = None


MOOD_MKII_CONTROLS: list[Control] = [
    Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127, default=64),
    Control(name="length", type=ControlType.KNOB, midi_cc=16, min=0, max=127, default=64),
    Control(name="wet_modify", type=ControlType.KNOB, midi_cc=17, min=0, max=127, default=64),
    Control(name="clock", type=ControlType.KNOB, midi_cc=18, min=0, max=127, default=64),
    Control(name="loop_modify", type=ControlType.KNOB, midi_cc=19, min=0, max=127, default=64),
    Control(name="ramp_speed", type=ControlType.KNOB, midi_cc=20, min=0, max=127, default=64),
    Control(
        name="wet_channel",
        type=ControlType.TOGGLE,
        midi_cc=21,
        min=0,
        max=127,
        positions=["reverb", "delay", "slip"],
        default=0,
    ),
    Control(
        name="routing",
        type=ControlType.TOGGLE,
        midi_cc=22,
        min=0,
        max=127,
        positions=["in", "wet_and_in", "wet"],
        default=0,
    ),
    Control(
        name="loop",
        type=ControlType.TOGGLE,
        midi_cc=23,
        min=0,
        max=127,
        positions=["env", "tape", "stretch"],
        default=0,
    ),
    Control(name="stereo_width", type=ControlType.KNOB, midi_cc=24, min=0, max=127, default=64),
    Control(name="ramping_waveform", type=ControlType.KNOB, midi_cc=25, min=0, max=127, default=64),
    Control(name="fade", type=ControlType.KNOB, midi_cc=26, min=0, max=127, default=64),
    Control(name="tone", type=ControlType.KNOB, midi_cc=27, min=0, max=127, default=64),
    Control(name="level_balance", type=ControlType.KNOB, midi_cc=28, min=0, max=127, default=64),
    Control(
        name="direct_micro_loop", type=ControlType.KNOB, midi_cc=29, min=0, max=127, default=64
    ),
    Control(
        name="sync",
        type=ControlType.TOGGLE,
        midi_cc=31,
        min=0,
        max=2,
        positions=["no_sync", "wet_only", "loop_only"],
        default=0,
    ),
    Control(
        name="spread",
        type=ControlType.TOGGLE,
        midi_cc=32,
        min=0,
        max=1,
        positions=["half", "full"],
        default=0,
    ),
    Control(
        name="buffer_length",
        type=ControlType.TOGGLE,
        midi_cc=33,
        min=0,
        max=1,
        positions=["half", "full"],
        default=0,
    ),
    Control(
        name="midi_clock_ignore", type=ControlType.SWITCH, midi_cc=51, min=0, max=127, default=None
    ),
    Control(name="stop_ramping", type=ControlType.SWITCH, midi_cc=52, min=0, max=127, default=None),
    Control(
        name="wet_clock",
        type=ControlType.TOGGLE,
        midi_cc=53,
        min=0,
        max=7,
        positions=[
            "32nd",
            "16th",
            "eighth_triplet",
            "eighth",
            "dotted_eighth",
            "quarter",
            "half",
            "whole",
        ],
        default=5,
    ),
    Control(
        name="loop_clock_division",
        type=ControlType.TOGGLE,
        midi_cc=54,
        min=0,
        max=7,
        positions=[
            "32nd",
            "16th",
            "eighth_triplet",
            "eighth",
            "dotted_eighth",
            "quarter",
            "half",
            "whole",
        ],
        default=5,
    ),
    Control(name="true_bypass", type=ControlType.SWITCH, midi_cc=55, min=0, max=127, default=None),
    Control(name="dip_l_time", type=ControlType.DIPSWITCH, midi_cc=61, min=0, max=127, default=0),
    Control(
        name="dip_l_wet_modify", type=ControlType.DIPSWITCH, midi_cc=62, min=0, max=127, default=0
    ),
    Control(name="dip_l_clock", type=ControlType.DIPSWITCH, midi_cc=63, min=0, max=127, default=0),
    Control(
        name="dip_l_loop_modify", type=ControlType.DIPSWITCH, midi_cc=64, min=0, max=127, default=0
    ),
    Control(name="dip_l_length", type=ControlType.DIPSWITCH, midi_cc=65, min=0, max=127, default=0),
    Control(name="dip_l_bounce", type=ControlType.DIPSWITCH, midi_cc=66, min=0, max=127, default=0),
    Control(name="dip_l_sweep", type=ControlType.DIPSWITCH, midi_cc=67, min=0, max=127, default=0),
    Control(
        name="dip_l_polarity", type=ControlType.DIPSWITCH, midi_cc=68, min=0, max=127, default=0
    ),
    Control(
        name="dip_r_classic", type=ControlType.DIPSWITCH, midi_cc=71, min=0, max=127, default=0
    ),
    Control(name="dip_r_miso", type=ControlType.DIPSWITCH, midi_cc=72, min=0, max=127, default=0),
    Control(name="dip_r_spread", type=ControlType.DIPSWITCH, midi_cc=73, min=0, max=127, default=0),
    Control(
        name="dip_r_dry_kill", type=ControlType.DIPSWITCH, midi_cc=74, min=0, max=127, default=0
    ),
    Control(name="dip_r_trails", type=ControlType.DIPSWITCH, midi_cc=75, min=0, max=127, default=0),
    Control(name="dip_r_latch", type=ControlType.DIPSWITCH, midi_cc=76, min=0, max=127, default=0),
    Control(name="dip_r_no_dub", type=ControlType.DIPSWITCH, midi_cc=77, min=0, max=127, default=0),
    Control(name="dip_r_smooth", type=ControlType.DIPSWITCH, midi_cc=78, min=0, max=127, default=0),
    Control(name="wet_bypass", type=ControlType.SWITCH, midi_cc=102, min=0, max=127, default=None),
    Control(name="loop_bypass", type=ControlType.SWITCH, midi_cc=103, min=0, max=127, default=None),
    Control(name="freeze", type=ControlType.SWITCH, midi_cc=105, min=0, max=127, default=None),
    Control(
        name="loop_overdub", type=ControlType.SWITCH, midi_cc=106, min=0, max=127, default=None
    ),
    Control(name="tap_tempo", type=ControlType.SWITCH, midi_cc=107, min=0, max=127, default=None),
]

WOMBTONE_MKII_CONTROLS: list[Control] = [
    Control(name="feed", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    Control(name="volume", type=ControlType.KNOB, midi_cc=15, min=0, max=127, default=64),
    Control(name="mix", type=ControlType.KNOB, midi_cc=16, min=0, max=127, default=64),
    Control(name="rate", type=ControlType.KNOB, midi_cc=17, min=0, max=127, default=64),
    Control(name="depth", type=ControlType.KNOB, midi_cc=18, min=0, max=127, default=64),
    Control(name="form", type=ControlType.KNOB, midi_cc=19, min=0, max=127, default=64),
    Control(name="ramp", type=ControlType.KNOB, midi_cc=20, min=0, max=127, default=64),
    Control(
        name="clock_division",
        type=ControlType.TOGGLE,
        midi_cc=21,
        min=0,
        max=5,
        positions=["whole", "half", "quarter_triplet", "quarter", "eighth", "sixteenth"],
        default=3,
    ),
    Control(
        name="midi_clock_ignore", type=ControlType.SWITCH, midi_cc=51, min=0, max=127, default=None
    ),
    Control(name="tap_tempo", type=ControlType.SWITCH, midi_cc=93, min=0, max=127, default=None),
    Control(
        name="expression_over_midi",
        type=ControlType.SWITCH,
        midi_cc=100,
        min=0,
        max=127,
        default=None,
    ),
    Control(name="bypass", type=ControlType.SWITCH, midi_cc=102, min=0, max=127, default=None),
]

BROTHERS_AM_CONTROLS: list[Control] = [
    Control(name="gain_2", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    Control(name="volume_2", type=ControlType.KNOB, midi_cc=15, min=0, max=127, default=64),
    Control(name="gain_1", type=ControlType.KNOB, midi_cc=16, min=0, max=127, default=64),
    Control(name="tone_2", type=ControlType.KNOB, midi_cc=17, min=0, max=127, default=64),
    Control(name="volume_1", type=ControlType.KNOB, midi_cc=18, min=0, max=127, default=64),
    Control(name="tone_1", type=ControlType.KNOB, midi_cc=19, min=0, max=127, default=64),
    Control(name="presence_2", type=ControlType.KNOB, midi_cc=27, min=0, max=127, default=64),
    Control(name="presence_1", type=ControlType.KNOB, midi_cc=29, min=0, max=127, default=64),
    Control(
        name="gain_2_type",
        type=ControlType.TOGGLE,
        midi_cc=21,
        min=0,
        max=3,
        positions=["boost", "od", "dist"],
        default=0,
    ),
    Control(
        name="treble_boost",
        type=ControlType.TOGGLE,
        midi_cc=22,
        min=0,
        max=3,
        positions=["full_sun", "off", "half_sun"],
        default=0,
    ),
    Control(
        name="gain_1_type",
        type=ControlType.TOGGLE,
        midi_cc=23,
        min=0,
        max=3,
        positions=["dist", "od", "boost"],
        default=0,
    ),
    Control(name="dip_volume_1", type=ControlType.DIPSWITCH, midi_cc=61, min=0, max=1, default=0),
    Control(name="dip_volume_2", type=ControlType.DIPSWITCH, midi_cc=62, min=0, max=1, default=0),
    Control(name="dip_gain_1", type=ControlType.DIPSWITCH, midi_cc=63, min=0, max=1, default=0),
    Control(name="dip_gain_2", type=ControlType.DIPSWITCH, midi_cc=64, min=0, max=1, default=0),
    Control(name="dip_tone_1", type=ControlType.DIPSWITCH, midi_cc=65, min=0, max=1, default=0),
    Control(name="dip_tone_2", type=ControlType.DIPSWITCH, midi_cc=66, min=0, max=1, default=0),
    Control(name="dip_sweep", type=ControlType.DIPSWITCH, midi_cc=67, min=0, max=1, default=0),
    Control(name="dip_polarity", type=ControlType.DIPSWITCH, midi_cc=68, min=0, max=1, default=0),
    Control(name="dip_hi_gain_1", type=ControlType.DIPSWITCH, midi_cc=71, min=0, max=1, default=0),
    Control(name="dip_hi_gain_2", type=ControlType.DIPSWITCH, midi_cc=72, min=0, max=1, default=0),
    Control(name="dip_motobyp_1", type=ControlType.DIPSWITCH, midi_cc=73, min=0, max=1, default=0),
    Control(name="dip_motobyp_2", type=ControlType.DIPSWITCH, midi_cc=74, min=0, max=1, default=0),
    Control(
        name="dip_pres_link_1", type=ControlType.DIPSWITCH, midi_cc=75, min=0, max=1, default=0
    ),
    Control(
        name="dip_pres_link_2", type=ControlType.DIPSWITCH, midi_cc=76, min=0, max=1, default=0
    ),
    Control(name="dip_master", type=ControlType.DIPSWITCH, midi_cc=77, min=0, max=1, default=0),
    Control(
        name="channel_1_bypass", type=ControlType.SWITCH, midi_cc=102, min=0, max=127, default=None
    ),
    Control(
        name="channel_2_bypass", type=ControlType.SWITCH, midi_cc=103, min=0, max=127, default=None
    ),
]

_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
    "Chase Bliss Audio/Wombtone MkII": WOMBTONE_MKII_CONTROLS,
    "Chase Bliss Audio/Brothers AM": BROTHERS_AM_CONTROLS,
}


def get_controls(manufacturer: str, model: str) -> list[Control]:
    key = f"{manufacturer}/{model}"
    return _CATALOG.get(key, [])
