from types import SimpleNamespace

from rig.engine.plugin import DeviceType
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig_analog.preset import AnalogPreset
from rig_chasebliss.preset import DigitalPreset
from rig_hx.preset import HXStompPreset
from tests.conftest import FakeDevice


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


def _make_controller_device() -> FakeDevice:
    """Helper: build a FakeDevice with DeviceType.CONTROLLER (no scenes — scenes belong on Rig)."""
    cfg = SimpleNamespace(type="controller", midi_channel=1, banks=[])
    return FakeDevice(id="mc6", type=DeviceType.CONTROLLER, config=cfg)


def _make_analog_device(device_id: str) -> FakeDevice:
    """Helper: build a minimal analog device."""
    return FakeDevice(id=device_id, type=DeviceType.ANALOG, config=None)


class TestRigConfig:
    def test_rig_config_minimal(self):
        config = Rig(name="Test", signal_chain=[])
        assert config.name == "Test"

    def test_rig_scenes_is_pydantic_field(self):
        assert "scenes" in Rig.model_fields

    def test_rig_scenes_constructor_accepts_scene_dict(self):
        scene = Scene(name="s", presets={"hx-stomp": "x"})
        rig = Rig(name="t", scenes={"s": scene})
        assert rig.scenes["s"].presets == {"hx-stomp": "x"}

    def test_rig_scenes_empty_by_default(self):
        rig = Rig(name="t")
        assert rig.scenes == {}

    def test_rig_controller_is_not_pydantic_field_but_scenes_is(self):
        """scenes is a real field; controller remains a property (not in model_fields)."""
        assert "controller" not in Rig.model_fields
        assert "scenes" in Rig.model_fields

    def test_rig_scenes_empty_when_no_controller_and_no_scenes_arg(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.scenes == {}

    def test_rig_scenes_via_constructor_not_controller_config(self):
        """Scenes come from Rig(scenes=...) constructor, not controller device config."""
        ctrl = _make_controller_device()
        scene = Scene(name="test", presets={"hx-stomp": "x"})
        rig = Rig(name="Test", signal_chain=[], devices={"mc6": ctrl}, scenes={"test": scene})
        assert rig.scenes["test"].name == "test"
        assert rig.scenes["test"].presets == {"hx-stomp": "x"}

    def test_rig_controller_returns_none_when_absent(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.controller is None

    def test_rig_controller_returns_controller_device(self):
        ctrl = _make_controller_device()
        rig = Rig(name="Test", signal_chain=[], devices={"mc6": ctrl})
        assert rig.controller is not None
        assert rig.controller.id == "mc6"
        assert rig.controller.type == DeviceType.CONTROLLER


class TestApplyOrder:
    def test_apply_order_empty_devices_returns_empty(self):
        rig = Rig(name="Test", signal_chain=[], devices={})
        assert rig.apply_order() == []

    def test_apply_order_no_controller_returns_devices_by_position(self):
        d1 = _make_analog_device("tumnus")
        d2 = _make_analog_device("brothers")
        rig = Rig(
            name="Test",
            signal_chain=["tumnus", "brothers"],
            devices={"tumnus": d1, "brothers": d2},
        )
        order = rig.apply_order()
        assert [d.id for d in order] == ["tumnus", "brothers"]

    def test_apply_order_controller_comes_last(self):
        d1 = _make_analog_device("tumnus")
        ctrl = _make_controller_device()
        rig = Rig(
            name="Test",
            signal_chain=["tumnus"],
            devices={"tumnus": d1, "mc6": ctrl},
        )
        order = rig.apply_order()
        assert [d.id for d in order] == ["tumnus", "mc6"]

    def test_apply_order_device_not_in_chain_after_chain_ordered(self):
        d1 = _make_analog_device("tumnus")
        d2 = _make_analog_device("extra")
        rig = Rig(
            name="Test",
            signal_chain=["tumnus"],
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
