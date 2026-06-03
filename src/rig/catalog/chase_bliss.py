from rig.models.device import Control, ControlType

MOOD_MKII_CONTROLS: list[Control] = [
    # Knobs (CC 14–20)
    Control(
        name="time",  # wet channel delay/reverb time; specific increments map to subdivisions
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
        name="length",  # micro looper loop length; specific increments map to divisions
        type=ControlType.KNOB,
        midi_cc=16,
        min=0,
        max=127,
    ),
    Control(
        name="wet_modify",  # modify knob for the wet channel; effect varies by wet channel mode
        type=ControlType.KNOB,
        midi_cc=17,
        min=0,
        max=127,
    ),
    Control(
        name="clock",  # internal clock rate; specific increments map to BPM/subdivision values
        type=ControlType.KNOB,
        midi_cc=18,
        min=0,
        max=127,
    ),
    Control(
        name="loop_modify",  # modify knob for the micro looper; specific increments affect loop behavior
        type=ControlType.KNOB,
        midi_cc=19,
        min=0,
        max=127,
    ),
    Control(
        name="ramp_speed",  # speed of the ramp swell when ramping is enabled
        type=ControlType.KNOB,
        midi_cc=20,
        min=0,
        max=127,
    ),
    # 3-way toggles (CC 21–23)
    Control(
        name="wet_channel",  # wet channel algorithm: 0–1 = reverb, 2 = delay, >=3 = slip
        type=ControlType.TOGGLE,
        midi_cc=21,
        min=0,
        max=127,
        positions=["reverb", "delay", "slip"],
    ),
    Control(
        name="routing",  # signal routing: 0–1 = in series, 2 = wet + in parallel, >=3 = wet only
        type=ControlType.TOGGLE,
        midi_cc=22,
        min=0,
        max=127,
        positions=["in", "wet_and_in", "wet"],
    ),
    Control(
        name="loop",  # looper mode: 0–1 = envelope, 2 = tape, >=3 = stretch
        type=ControlType.TOGGLE,
        midi_cc=23,
        min=0,
        max=127,
        positions=["env", "tape", "stretch"],
    ),
    # Clock division selects (CC 53–54)
    Control(
        name="wet_clock",  # clock division for the wet channel: 0=32nd, 1=16th, 2=eighth triplet, 3=eighth, 4=dotted eighth, 5=quarter, 6=half, 7=whole
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
    ),
    Control(
        name="loop_clock_division",  # clock division for the micro looper: same positions as wet_clock
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
    ),
    # Bypass mode (CC 55)
    Control(
        name="true_bypass",  # bypass type: 0 = buffered (standard), >=1 = true bypass
        type=ControlType.SWITCH,
        midi_cc=55,
        min=0,
        max=127,
    ),
    # Footswitch actions (CC 102–107)
    Control(
        name="loop_bypass",  # bypass switch for the micro looper channel: 0 = engaged, >=1 = bypassed
        type=ControlType.SWITCH,
        midi_cc=102,
        min=0,
        max=127,
    ),
    Control(
        name="wet_bypass",  # bypass switch for the wet (delay/reverb) channel: 0 = engaged, >=1 = bypassed
        type=ControlType.SWITCH,
        midi_cc=103,
        min=0,
        max=127,
    ),
    Control(
        name="freeze",  # freeze: >=1 = holds the current buffer/loop indefinitely
        type=ControlType.SWITCH,
        midi_cc=105,
        min=0,
        max=127,
    ),
    Control(
        name="loop_overdub",  # loop overdub: >=1 = layers additional audio onto the current loop
        type=ControlType.SWITCH,
        midi_cc=106,
        min=0,
        max=127,
    ),
    Control(
        name="tap_tempo",  # tap tempo: any value >0 registers a tap; sets internal clock BPM
        type=ControlType.SWITCH,
        midi_cc=107,
        min=0,
        max=127,
    ),
    # Left dip switch bank (CC 61–68) — ramp/expression assign and loop behavior
    Control(
        name="dip_time",  # on = time knob is assigned to the ramp/expression input
        type=ControlType.DIPSWITCH,
        midi_cc=61,
        min=0,
        max=127,
    ),
    Control(
        name="dip_wet_modify",  # on = wet modify knob is assigned to the ramp/expression input
        type=ControlType.DIPSWITCH,
        midi_cc=62,
        min=0,
        max=127,
    ),
    Control(
        name="dip_clock",  # on = clock knob is assigned to the ramp/expression input
        type=ControlType.DIPSWITCH,
        midi_cc=63,
        min=0,
        max=127,
    ),
    Control(
        name="dip_loop_modify",  # on = loop modify knob is assigned to the ramp/expression input
        type=ControlType.DIPSWITCH,
        midi_cc=64,
        min=0,
        max=127,
    ),
    Control(
        name="dip_length",  # on = length knob is assigned to the ramp/expression input
        type=ControlType.DIPSWITCH,
        midi_cc=65,
        min=0,
        max=127,
    ),
    Control(
        name="dip_bounce",  # on = looper plays forward then reverses (bounce/ping-pong playback)
        type=ControlType.DIPSWITCH,
        midi_cc=66,
        min=0,
        max=127,
    ),
    Control(
        name="dip_sweep",  # on = enables sweep mode; the ramp continuously oscillates back and forth
        type=ControlType.DIPSWITCH,
        midi_cc=67,
        min=0,
        max=127,
    ),
    Control(
        name="dip_polarity",  # on = inverts the ramp/expression direction (high becomes low, low becomes high)
        type=ControlType.DIPSWITCH,
        midi_cc=68,
        min=0,
        max=127,
    ),
    # Right dip switch bank (CC 71–78) — output and MIDI behavior
    Control(
        name="dip_classic",  # on = classic MOOD v1 algorithm behavior for the wet channel
        type=ControlType.DIPSWITCH,
        midi_cc=71,
        min=0,
        max=127,
    ),
    Control(
        name="dip_miso",  # on = MISO mode (MIDI in / serial out); pedal receives MIDI and passes clock downstream
        type=ControlType.DIPSWITCH,
        midi_cc=72,
        min=0,
        max=127,
    ),
    Control(
        name="dip_spread",  # on = stereo spread; left and right outputs carry different wet signals
        type=ControlType.DIPSWITCH,
        midi_cc=73,
        min=0,
        max=127,
    ),
    Control(
        name="dip_dry_kill",  # on = dry signal is removed; wet output only
        type=ControlType.DIPSWITCH,
        midi_cc=74,
        min=0,
        max=127,
    ),
    Control(
        name="dip_trails",  # on = wet channel trails off naturally after bypass instead of cutting abruptly
        type=ControlType.DIPSWITCH,
        midi_cc=75,
        min=0,
        max=127,
    ),
    Control(
        name="dip_latch",  # on = loop record/play footswitch latches (press once to start, once to stop)
        type=ControlType.DIPSWITCH,
        midi_cc=76,
        min=0,
        max=127,
    ),
    Control(
        name="dip_no_dub",  # on = disables overdubbing; loop plays back but new audio is not layered in
        type=ControlType.DIPSWITCH,
        midi_cc=77,
        min=0,
        max=127,
    ),
    Control(
        name="dip_smooth",  # on = smooths transitions when switching loop or wet channel modes
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
