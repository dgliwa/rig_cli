import pytest
from pydantic import ValidationError

from rig.models.device import (
    Control,
    ControllerConfig,
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


class TestControllerConfig:
    def test_device_type_controller_value(self):
        assert DeviceType.CONTROLLER == "controller"

    def test_controller_config_defaults(self):
        cfg = ControllerConfig()
        assert cfg.type == "controller"
        assert cfg.banks == []
        assert cfg.scenes == {}

    def test_device_with_controller_type_constructs(self):
        device = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config={"type": "controller", "midi_channel": 1, "banks": [], "scenes": {}},
        )
        assert device.type == DeviceType.CONTROLLER
        assert isinstance(device.config, ControllerConfig)

    def test_controller_config_round_trips_via_discriminated_union(self):
        device = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config=ControllerConfig(midi_channel=1, banks=[], scenes={}),
        )
        dumped = device.model_dump()
        restored = Device(**dumped)
        assert restored.type == DeviceType.CONTROLLER
        assert isinstance(restored.config, ControllerConfig)


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

    def test_invalid_control_rejected(self):
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
            tags=["bluegrass"],
        )
        assert scene.tempo == 118


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


def _make_controller_device(scenes: dict | None = None) -> Device:
    """Helper: build a Device with DeviceType.CONTROLLER and ControllerConfig."""
    return Device(
        id="mc6",
        manufacturer="Morningstar",
        model="MC6",
        type=DeviceType.CONTROLLER,
        config=ControllerConfig(midi_channel=1, banks=[], scenes=scenes or {}),
    )


def _make_analog_device(device_id: str) -> Device:
    """Helper: build a minimal analog device."""
    return Device(
        id=device_id,
        manufacturer="Wampler",
        model="Tumnus",
        type=DeviceType.ANALOG,
        config=ManualConfig(controls=[]),
    )


class TestRigConfig:
    def test_rig_config_minimal(self):
        config = Rig(name="Test", signal_chain=[])
        assert config.name == "Test"

    def test_rig_scenes_returns_empty_when_no_controller(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.scenes == {}

    def test_rig_scenes_returns_controller_config_scenes(self):
        scene = Scene(name="test", presets={"hx-stomp": "x"})
        ctrl = _make_controller_device()
        rig = Rig(name="Test", signal_chain=[], devices={"mc6": ctrl}, scenes={"test": scene})
        assert rig.scenes["test"].name == "test"

    def test_rig_controller_returns_none_when_absent(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.controller is None

    def test_rig_controller_returns_controller_device(self):
        ctrl = _make_controller_device()
        rig = Rig(name="Test", signal_chain=[], devices={"mc6": ctrl})
        assert rig.controller is not None
        assert rig.controller.id == "mc6"
        assert rig.controller.type == DeviceType.CONTROLLER

    def test_rig_controller_and_scenes_are_not_pydantic_fields(self):
        assert "controller" not in Rig.model_fields
        assert "scenes" in Rig.model_fields


class TestApplyOrder:
    def test_apply_order_empty_devices_returns_empty(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.apply_order() == []

    def test_apply_order_no_controller_returns_devices_by_position(self):
        d1 = _make_analog_device("tumnus")
        d2 = _make_analog_device("brothers")
        rig = Rig(
            name="Test",
            signal_chain=[
                SignalChainPosition(device_ref="brothers", position=2),
                SignalChainPosition(device_ref="tumnus", position=1),
            ],
            devices={"tumnus": d1, "brothers": d2},
        )
        order = rig.apply_order()
        assert [d.id for d in order] == ["tumnus", "brothers"]

    def test_apply_order_controller_comes_last(self):
        d1 = _make_analog_device("tumnus")
        ctrl = _make_controller_device()
        rig = Rig(
            name="Test",
            signal_chain=[
                SignalChainPosition(device_ref="tumnus", position=1),
            ],
            devices={"tumnus": d1, "mc6": ctrl},
        )
        order = rig.apply_order()
        assert [d.id for d in order] == ["tumnus", "mc6"]

    def test_apply_order_device_not_in_chain_after_chain_ordered(self):
        d1 = _make_analog_device("tumnus")
        d2 = _make_analog_device("extra")
        rig = Rig(
            name="Test",
            signal_chain=[
                SignalChainPosition(device_ref="tumnus", position=1),
            ],
            devices={"tumnus": d1, "extra": d2},
        )
        order = rig.apply_order()
        assert order[0].id == "tumnus"
        assert order[1].id == "extra"

    def test_apply_order_only_controller_returns_controller(self):
        ctrl = _make_controller_device()
        rig = Rig(name="Test", signal_chain=[], devices={"mc6": ctrl})
        order = rig.apply_order()
        assert len(order) == 1
        assert order[0].id == "mc6"
