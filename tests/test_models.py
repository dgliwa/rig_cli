import pytest
from pydantic import ValidationError
from rig.models.pedal import PedalType, ControlType, Control, PedalDefinition
from rig.models.preset import AnalogPreset, DigitalPreset, HXBlock, HXStompPreset, MIDICommand, FootswitchAssignment
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.models.rig import RigConfig


class TestPedalModels:
    def test_pedal_definition_round_trips(self):
        pedal = PedalDefinition(
            id="tumnus", manufacturer="Wampler", model="Tumnus", type=PedalType.ANALOG,
            controls=[Control(name="Gain", type=ControlType.KNOB, min=0, max=10)],
        )
        assert pedal.id == "tumnus"
        assert pedal.controls[0].name == "Gain"

    def test_pedal_type_enum_values(self):
        assert PedalType.DIGITAL.value == "digital"
        assert PedalType.ANALOG.value == "analog"
        assert PedalType.MODELER.value == "modeler"
        assert PedalType.CONTROLLER.value == "controller"

    def invalid_control_rejected(self):
        with pytest.raises(ValidationError):
            Control(name="", type=ControlType.KNOB)

    def test_control_with_positions(self):
        ctrl = Control(name="BoostCut", type=ControlType.DIPSWITCH, positions=["Boost", "Cut"])
        assert ctrl.positions == ["Boost", "Cut"]

    def test_control_with_midi_cc(self):
        ctrl = Control(name="Gain", type=ControlType.KNOB, midi_cc=14)
        assert ctrl.midi_cc == 14

    def test_control_expression_defaults_to_false(self):
        ctrl = Control(name="Gain", type=ControlType.KNOB)
        assert ctrl.expression_assignable is False


class TestPresetModels:
    def test_analog_preset_round_trips_knob_values(self):
        preset = AnalogPreset(
            id="edge-of-breakup", pedal="tumnus", name="Edge of Breakup",
            values={"Gain": 3.5, "Level": 7.0, "Treble": 5.5},
        )
        assert preset.values["Gain"] == 3.5

    def test_analog_preset_with_tags(self):
        preset = AnalogPreset(
            id="test", pedal="tumnus", name="Test",
            values={"Gain": 5.0}, tags=["rhythm", "cleanish"],
        )
        assert "rhythm" in preset.tags

    def test_digital_preset_minimal(self):
        preset = DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain")
        assert preset.preset_number is None

    def test_digital_preset_with_parameters(self):
        preset = DigitalPreset(
            id="lead", pedal="brothers", name="Lead", preset_number=7,
            parameters={"Gain": 8, "Tone": 5},
        )
        assert preset.parameters["Gain"] == 8

    def test_hx_block_with_settings(self):
        block = HXBlock(name="Amp", type="amp", model="US Double Nrm", settings={"Drive": 4.5, "Bass": 5.0})
        assert block.settings["Drive"] == 4.5
        assert block.enabled is True

    def test_hx_block_can_be_disabled(self):
        block = HXBlock(name="Reverb", type="reverb", model="Plate", enabled=False)
        assert block.enabled is False

    def test_midi_command_pc(self):
        cmd = MIDICommand(type="pc", channel=3, value=4, label="Brothers → Low Gain")
        assert cmd.channel == 3

    def test_midi_command_cc_with_number(self):
        cmd = MIDICommand(type="cc", channel=4, cc_number=14, value=50)
        assert cmd.cc_number == 14

    def test_midi_command_default_delay(self):
        cmd = MIDICommand(type="pc", channel=1, value=1)
        assert cmd.delay_ms == 0

    def test_hx_stomp_preset_full(self):
        block = HXBlock(name="Amp", type="amp", model="US Double Nrm")
        cmd = MIDICommand(type="pc", channel=3, value=4)
        fs = FootswitchAssignment(switch="FS1", action="toggle_block", target="Delay")
        preset = HXStompPreset(
            id="clean-edge", pedal="hx-stomp", name="Clean Edge",
            preset_number=12, blocks=[block], midi_commands=[cmd],
            footswitch_assignments=[fs], tempo=118,
        )
        assert preset.preset_number == 12
        assert preset.tempo == 118
        assert preset.footswitch_assignments[0].switch == "FS1"

    def test_hx_stomp_preset_defaults(self):
        preset = HXStompPreset(id="test", pedal="hx-stomp", name="Test")
        assert preset.blocks == []
        assert preset.midi_commands == []


class TestSceneModel:
    def test_scene_minimal(self):
        scene = Scene(name="billy-clean", presets={"hx-stomp": "clean-edge"})
        assert scene.name == "billy-clean"

    def test_scene_full(self):
        scene = Scene(
            name="billy-clean", description="Billy clean tone", tempo=118,
            presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
            mc6_bank=1, mc6_switch="A", tags=["bluegrass"],
        )
        assert scene.tempo == 118
        assert scene.mc6_switch == "A"

    def test_scene_rejects_invalid_switch(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", presets={"hx-stomp": "x"}, mc6_switch="Z")


class TestSignalChainModel:
    def test_signal_chain_position_defaults(self):
        pos = SignalChainPosition(pedal_ref="tumnus", position=1)
        assert pos.loop == "front"
        assert pos.stereo is False

    def test_signal_chain_fx_loop(self):
        pos = SignalChainPosition(pedal_ref="wombtone", position=5, loop="fx_loop")
        assert pos.loop == "fx_loop"

    def test_signal_chain_stereo(self):
        pos = SignalChainPosition(pedal_ref="hx-stomp", position=4, stereo=True)
        assert pos.stereo is True


class TestRigConfig:
    def test_rig_config_minimal(self):
        config = RigConfig(name="Test", signal_chain=[])
        assert config.name == "Test"

    def test_rig_config_with_scenes(self):
        scene = Scene(name="test", presets={"hx-stomp": "x"})
        config = RigConfig(name="Test", signal_chain=[], scenes={"test": scene})
        assert config.scenes["test"].name == "test"
