from __future__ import annotations

from rig.engine.plugin import SetupContext, SetupResult
from rig.engine.state import RigState
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
        device = AnalogDevice(id="reverb", name="BigSky", config=None)
        result = device.setup(_make_setup_ctx())
        assert result == SetupResult()

    def test_get_scene_pc_command_returns_none(self):
        device = AnalogDevice(id="reverb", name="BigSky", config=None)
        assert device.get_scene_pc_command("clean") is None

    def test_register_populates_registry(self):
        """AnalogDevice is discoverable via entry points (not register() callback)."""
        from rig.engine.plugin_registry import reload_registry

        registry = reload_registry()
        assert registry.get("manual") is not None
        assert registry.get_model("manual") is AnalogDevice
