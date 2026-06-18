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


class _StubIO:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    def prompt(self, text: str) -> str:
        return next(self._responses, "done")

    def prompt_device(self, *args, **kwargs):
        return "skip"

    def prompt_mc6_navigate(self, *args, **kwargs):
        return "skip"


def _make_edit_ctx(responses: list[str] | None = None):
    from pathlib import Path

    from rig.engine.plugin import EditContext
    from rig.models.rig import Rig

    return EditContext(
        config_path=Path("."),
        dry_run=False,
        confirmation_io=_StubIO(responses or []),
        rig=Rig(name="test", signal_chain=[], devices={}),
    )


def _make_analog_device(values: dict | None = None):
    from rig_analog.device import AnalogDevice

    return AnalogDevice.from_raw_yaml(
        {
            "id": "reverb",
            "config": {"type": "manual"},
            "presets": [
                {"id": "clean", "name": "Clean", "values": values or {"drive": 5, "mix": 7}},
            ],
        }
    )


def test_analog_device_implements_editor_protocol():
    from rig.engine.plugin import EditorProtocol
    from rig_analog.device import AnalogDevice

    device = AnalogDevice.from_raw_yaml({"id": "reverb", "config": {"type": "manual"}})
    assert isinstance(device, EditorProtocol)


def test_analog_edit_returns_unchanged_on_done():
    device = _make_analog_device()
    ctx = _make_edit_ctx(responses=["done"])
    result = device.edit("clean", ctx)
    assert result == {"drive": 5, "mix": 7}


def test_analog_edit_valid_key_updates_dict():
    device = _make_analog_device()
    ctx = _make_edit_ctx(responses=["drive 8", "done"])
    result = device.edit("clean", ctx)
    assert result["drive"] == "8"


def test_analog_edit_unknown_key_is_rejected():
    device = _make_analog_device()
    ctx = _make_edit_ctx(responses=["bogus_key 5", "done"])
    result = device.edit("clean", ctx)
    assert "bogus_key" not in result


def test_analog_edit_raises_for_unknown_preset():
    import pytest

    device = _make_analog_device()
    ctx = _make_edit_ctx(responses=["done"])
    with pytest.raises(ValueError, match="not found"):
        device.edit("nonexistent", ctx)
