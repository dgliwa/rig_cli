from __future__ import annotations

from rig.engine.plugin import SetupContext, SetupResult
from rig.engine.state import RigState
from rig_analog.config import AnalogConfig
from rig_analog.device import AnalogDevice


def _make_setup_ctx() -> SetupContext:
    from rig.engine.ports import RichConfirmationIO
    from rig.models.rig import Rig

    return SetupContext(
        state=RigState(),
        rig=Rig(name="test", signal_chain=[], devices={}),
        dry_run=True,
        confirmation_io=RichConfirmationIO(),
    )


class TestAnalogDevice:
    def test_setup_is_noop(self):
        device = AnalogDevice(id="reverb", name="BigSky", config=AnalogConfig())
        result = device.setup(_make_setup_ctx())
        assert result == SetupResult()

    def test_get_scene_pc_command_returns_none(self):
        device = AnalogDevice(id="reverb", name="BigSky", config=AnalogConfig())
        assert device.get_scene_pc_command("clean") is None

    def test_register_populates_registry(self):
        """AnalogDevice is discoverable via entry points (not register() callback)."""
        from rig.engine.plugin_registry import reload_registry

        registry = reload_registry()
        assert registry.get("manual") is not None
        assert registry.get_model("manual") is AnalogDevice


def test_from_raw_yaml_extra_config_fields_ignored(self=None):
    from rig_analog.config import AnalogConfig
    from rig_analog.device import AnalogDevice

    device = AnalogDevice.from_raw_yaml(
        {"id": "x", "config": {"type": "manual", "extra_field": "ignored"}}
    )
    assert isinstance(device.config, AnalogConfig)


def test_analog_device_config_is_analog_config_instance():
    from rig_analog.config import AnalogConfig
    from rig_analog.device import AnalogDevice

    device = AnalogDevice.from_raw_yaml({"id": "fuzz", "config": {"type": "manual"}})
    assert isinstance(device.config, AnalogConfig)


def test_analog_device_does_not_implement_editor_protocol():
    """AnalogDevice must NOT implement EditorProtocol in Phase 27 (D-09)."""
    from rig.engine.plugin import EditorProtocol
    from rig_analog.device import AnalogDevice

    device = AnalogDevice.from_raw_yaml({"id": "reverb", "config": {"type": "manual"}})
    assert not isinstance(device, EditorProtocol)
