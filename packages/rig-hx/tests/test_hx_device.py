from __future__ import annotations

import pytest
from pydantic import ValidationError

from rig.models.preset import MidiPreset
from rig_hx.config import HXStompConfig
from rig_hx.device import HXStompDevice
from rig_hx.preset import HXStompPreset


def test_from_raw_yaml_modeler_type_returns_hxstomp_presets():
    device = HXStompDevice.from_raw_yaml(
        {
            "id": "hx",
            "name": "HX Stomp",
            "type": "modeler",
            "config": {"type": "midi"},
            "presets": [
                {"id": "clean", "name": "Clean", "preset_number": 1, "hlx_file": "clean.hlx"}
            ],
        }
    )
    assert len(device.presets) == 1
    assert isinstance(device.presets[0], HXStompPreset)


def test_from_raw_yaml_digital_type_returns_midi_presets():
    device = HXStompDevice.from_raw_yaml(
        {
            "id": "hx",
            "name": "HX Stomp",
            "type": "digital",
            "config": {"type": "midi"},
            "presets": [{"id": "lead", "name": "Lead", "preset_number": 2}],
        }
    )
    assert len(device.presets) == 1
    assert isinstance(device.presets[0], MidiPreset)


def test_from_raw_yaml_sets_midi_channel():
    device = HXStompDevice.from_raw_yaml(
        {"id": "hx", "config": {"type": "midi", "midi_channel": 5}}
    )
    assert device.config.midi_channel == 5


def test_from_raw_yaml_invalid_midi_channel_raises():
    with pytest.raises(ValidationError):
        HXStompDevice.from_raw_yaml({"id": "hx", "config": {"type": "midi", "midi_channel": "bad"}})


def test_config_is_hxstomp_config_instance():
    device = HXStompDevice.from_raw_yaml({"id": "hx", "config": {"type": "midi"}})
    assert isinstance(device.config, HXStompConfig)


# ---------------------------------------------------------------------------
# EditorProtocol skeleton tests
# ---------------------------------------------------------------------------


def _make_edit_ctx():
    """Build a minimal EditContext for testing."""
    from pathlib import Path

    from rig.engine.plugin import EditContext
    from rig.engine.ports import RichConfirmationIO
    from rig.models.rig import Rig

    return EditContext(
        config_path=Path("."),
        dry_run=False,
        confirmation_io=RichConfirmationIO(),
        rig=Rig(name="test", signal_chain=[], devices={}),
    )


def _make_hx_device():
    """Create an HXStompDevice with one preset."""
    return HXStompDevice.from_raw_yaml(
        {
            "id": "hx-stomp",
            "name": "HX Stomp",
            "type": "modeler",
            "config": {"type": "midi", "midi_channel": 1},
            "presets": [
                {
                    "id": "clean",
                    "name": "Clean Tone",
                    "preset_number": 1,
                    "hlx_file": "hlx/clean.hlx",
                }
            ],
        }
    )


def test_hx_stomp_device_satisfies_editor_protocol():
    from rig.engine.plugin import EditorProtocol

    device = _make_hx_device()
    assert isinstance(device, EditorProtocol)


def test_hx_stomp_device_edit_returns_preset_dict():
    device = _make_hx_device()
    ctx = _make_edit_ctx()
    result = device.edit("clean", ctx)
    assert isinstance(result, dict)
    assert result["id"] == "clean"
    assert result["preset_number"] == 1


def test_hx_stomp_device_edit_raises_for_unknown_preset():
    device = _make_hx_device()
    ctx = _make_edit_ctx()
    with pytest.raises(ValueError, match="not found"):
        device.edit("nonexistent", ctx)
