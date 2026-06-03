from rig.models.device import Control, ControlType

MOOD_MKII_CONTROLS: list[Control] = [
    Control(
        name="time",  # wet channel delay/reverb time
        type=ControlType.KNOB,
        midi_cc=14,
        min=0,
        max=127,
    ),
    Control(
        name="mix",  # wet/dry blend for the wet channel
        type=ControlType.KNOB,
        midi_cc=15,
        min=0,
        max=127,
    ),
    Control(
        name="length",  # micro looper loop length
        type=ControlType.KNOB,
        midi_cc=16,
        min=0,
        max=127,
    ),
    Control(
        name="wet_modify",  # modify knob for the wet channel (effect varies by mode)
        type=ControlType.KNOB,
        midi_cc=17,
        min=0,
        max=127,
    ),
    Control(
        name="clock",  # internal clock rate / tap tempo multiplier
        type=ControlType.KNOB,
        midi_cc=18,
        min=0,
        max=127,
    ),
    Control(
        name="micro_looper_modify",  # modify knob for the micro looper channel
        type=ControlType.KNOB,
        midi_cc=19,
        min=0,
        max=127,
    ),
    Control(
        name="ramp_speed",  # speed of the ramp function when ramping is enabled
        type=ControlType.KNOB,
        midi_cc=20,
        min=0,
        max=127,
    ),
    Control(
        name="wet_bypass",  # bypass switch for the wet (delay/reverb) channel
        type=ControlType.SWITCH,
        midi_cc=103,
        min=0,
        max=127,
    ),
    Control(
        name="micro_bypass",  # bypass switch for the micro looper channel
        type=ControlType.SWITCH,
        midi_cc=102,
        min=0,
        max=127,
    ),
    # Left dip switch bank (CC 61–68)
    Control(
        name="dip_l_1",  # clock source: off = internal, on = external
        type=ControlType.DIPSWITCH,
        midi_cc=61,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_2",  # left channel input: off = mono, on = stereo
        type=ControlType.DIPSWITCH,
        midi_cc=62,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_3",  # wet signal only: on = bypasses dry signal, wet out only
        type=ControlType.DIPSWITCH,
        midi_cc=63,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_4",  # infinite loop hold: on = freezes the current loop indefinitely
        type=ControlType.DIPSWITCH,
        midi_cc=64,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_5",  # reverse playback: on = plays the loop/buffer in reverse
        type=ControlType.DIPSWITCH,
        midi_cc=65,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_6",  # octave down: on = shifts playback down one octave
        type=ControlType.DIPSWITCH,
        midi_cc=66,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_7",  # stutter mode: on = enables stutter/glitch playback
        type=ControlType.DIPSWITCH,
        midi_cc=67,
        min=0,
        max=127,
    ),
    Control(
        name="dip_l_8",  # self-oscillation: on = allows feedback to build into self-oscillation
        type=ControlType.DIPSWITCH,
        midi_cc=68,
        min=0,
        max=127,
    ),
    # Right dip switch bank (CC 71–78)
    Control(
        name="dip_r_1",  # right channel WET bypass: on = wet signal bypassed on right channel
        type=ControlType.DIPSWITCH,
        midi_cc=71,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_2",  # right channel input: off = mono, on = stereo
        type=ControlType.DIPSWITCH,
        midi_cc=72,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_3",  # bypass mode: off = latching, on = momentary
        type=ControlType.DIPSWITCH,
        midi_cc=73,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_4",  # tap tempo subdivision: on = half note
        type=ControlType.DIPSWITCH,
        midi_cc=74,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_5",  # tap tempo subdivision: on = quarter note
        type=ControlType.DIPSWITCH,
        midi_cc=75,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_6",  # MIDI clock out: on = sends MIDI clock to downstream devices
        type=ControlType.DIPSWITCH,
        midi_cc=76,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_7",  # expression pedal polarity: on = inverts expression pedal direction
        type=ControlType.DIPSWITCH,
        midi_cc=77,
        min=0,
        max=127,
    ),
    Control(
        name="dip_r_8",  # ramping: on = enables ramping (slow swell) on the wet channel
        type=ControlType.DIPSWITCH,
        midi_cc=78,
        min=0,
        max=127,
    ),
]

_CATALOG: dict[str, list[Control]] = {
    "Chase Bliss Audio/Mood MkII": MOOD_MKII_CONTROLS,
}


def get_controls(manufacturer: str, model: str) -> list[Control]:
    return _CATALOG.get(f"{manufacturer}/{model}", [])
