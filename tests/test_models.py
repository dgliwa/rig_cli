import pytest
from pydantic import ValidationError

from rig.models.controller import ControllerType
from rig.models.device import (
    Control,
    ControlType,
    Device,
    DeviceType,
    ManualConfig,
)
from rig.models.preset import (
    AnalogPreset,
    DigitalPreset,
    HXStompPreset,
)
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


class TestPedalModels:
    def test_pedal_definition_round_trips(self):
        device = Device(
            id="tumnus",
            manufacturer="Wampler",
            model="Tumnus",
            type=DeviceType.ANALOG,
            config=ManualConfig(
                controls=[Control(name="Gain", type=ControlType.KNOB, min=0, max=10)]
            ),
        )
        assert device.id == "tumnus"
        assert device.config.controls[0].name == "Gain"

    def test_device_type_enum_values(self):
        assert DeviceType.DIGITAL.value == "digital"
        assert DeviceType.ANALOG.value == "analog"
        assert DeviceType.MODELER.value == "modeler"

    def test_controller_type_enum_values(self):
        assert ControllerType.MC6.value == "mc6"

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
            id="edge-of-breakup",
            pedal="tumnus",
            name="Edge of Breakup",
            values={"Gain": 3.5, "Level": 7.0, "Treble": 5.5},
        )
        assert preset.values["Gain"] == 3.5

    def test_analog_preset_with_tags(self):
        preset = AnalogPreset(
            id="test",
            pedal="tumnus",
            name="Test",
            values={"Gain": 5.0},
            tags=["rhythm", "cleanish"],
        )
        assert "rhythm" in preset.tags

    def test_digital_preset_minimal(self):
        preset = DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
        assert preset.preset_number == 4

    def test_digital_preset_with_parameters(self):
        preset = DigitalPreset(
            id="lead",
            pedal="brothers",
            name="Lead",
            preset_number=7,
            parameters={"Gain": 8, "Tone": 5},
        )
        assert preset.parameters["Gain"] == 8

    def test_hx_stomp_preset_full(self):
        preset = HXStompPreset(
            id="clean-edge",
            name="Clean Edge",
            preset_number=12,
            hlx_file="hlx/clean-edge.hlx",
        )
        assert preset.preset_number == 12
        assert preset.hlx_file == "hlx/clean-edge.hlx"

    def test_hx_stomp_preset_with_tags(self):
        preset = HXStompPreset(
            id="test",
            name="Test",
            preset_number=1,
            hlx_file="hlx/test.hlx",
            tags=["clean", "bright"],
        )
        assert "clean" in preset.tags


class TestSceneModel:
    def test_scene_minimal(self):
        scene = Scene(name="billy-clean", presets={"hx-stomp": "clean-edge"})
        assert scene.name == "billy-clean"

    def test_scene_full(self):
        scene = Scene(
            name="billy-clean",
            description="Billy clean tone",
            tempo=118,
            presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
            mc6_bank=1,
            mc6_switch="A",
            tags=["bluegrass"],
        )
        assert scene.tempo == 118
        assert scene.mc6_switch == "A"

    def test_scene_rejects_invalid_switch(self):
        with pytest.raises(ValidationError):
            Scene(name="bad", presets={"hx-stomp": "x"}, mc6_switch="Z")


class TestSignalChainModel:
    def test_signal_chain_position_defaults(self):
        pos = SignalChainPosition(device_ref="tumnus", position=1)
        assert pos.loop == "front"
        assert pos.stereo is False

    def test_signal_chain_fx_loop(self):
        pos = SignalChainPosition(device_ref="wombtone", position=5, loop="fx_loop")
        assert pos.loop == "fx_loop"

    def test_signal_chain_stereo(self):
        pos = SignalChainPosition(device_ref="hx-stomp", position=4, stereo=True)
        assert pos.stereo is True

    def test_signal_chain_pedal_ref_compat(self):
        # Ensure legacy pedal_ref attribute still accessible for backward compat
        pos = SignalChainPosition(device_ref="tumnus", position=1)
        assert pos.pedal_ref == "tumnus"


class TestRigConfig:
    def test_rig_config_minimal(self):
        config = Rig(name="Test", signal_chain=[])
        assert config.name == "Test"

    def test_rig_config_with_scenes(self):
        scene = Scene(name="test", presets={"hx-stomp": "x"})
        config = Rig(name="Test", signal_chain=[], scenes={"test": scene})
        assert config.scenes["test"].name == "test"
