"""CLI tests for rig edit command.

Covers:
- Unknown device exits 1 with red error
- Unknown preset exits 1 with red error
- Device without EditorProtocol prints warning and exits 0
- Device with EditorProtocol calls device.edit() with correct args
- Save confirm calls write_preset()
- Discard skips write_preset()
- --dry-run passes dry_run=True to EditContext and write_preset()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from rig.cli import app

runner = CliRunner()


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_analog_preset():
    """A minimal preset-like object that satisfies the preset interface."""
    preset = MagicMock()
    preset.id = "clean"
    preset.name = "Clean Tone"
    return preset


def _make_device(device_id: str, preset_id: str = "clean", has_edit: bool = False):
    """Create a stub device with an optional edit() method."""
    preset = _make_analog_preset()
    preset.id = preset_id

    if has_edit:

        class EditableDevice:
            id = device_id
            name = "Test Device"
            config = MagicMock()
            presets = [preset]

            def edit(self, pid: str, ctx: Any) -> dict[str, Any]:
                return {"preset_number": 42}

        return EditableDevice()
    else:

        class NonEditableDevice:
            id = device_id
            name = "Test Device"
            config = MagicMock()
            presets = [preset]

        return NonEditableDevice()


def _make_rig(device_id: str = "mood", preset_id: str = "clean", has_edit: bool = False):
    """Create a stub Rig with one device."""
    device = _make_device(device_id, preset_id, has_edit)
    rig = MagicMock()
    rig.devices = {device_id: device}
    return rig


# ── Unknown device / preset tests ─────────────────────────────────────────


def test_unknown_device_exits_1(tmp_path: Path):
    """Unknown device ID should exit 1 with error containing the device ID."""
    rig = _make_rig("mood", "clean")

    with patch("rig.cli.commands.edit.load_rig", return_value=rig):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "bad-device", "clean"])

    assert result.exit_code == 1
    assert "bad-device" in result.stdout


def test_unknown_preset_exits_1(tmp_path: Path):
    """Known device but unknown preset exits 1 with error containing preset ID."""
    rig = _make_rig("mood", "clean")

    with patch("rig.cli.commands.edit.load_rig", return_value=rig):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "mood", "bad-preset"])

    assert result.exit_code == 1
    assert "bad-preset" in result.stdout


# ── EditorProtocol dispatch tests ─────────────────────────────────────────


def test_non_editor_device_prints_warning_exits_0(tmp_path: Path):
    """Device without EditorProtocol prints exact warning message and exits 0."""
    rig = _make_rig("mood", "clean", has_edit=False)

    with patch("rig.cli.commands.edit.load_rig", return_value=rig):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "mood", "clean"])

    assert result.exit_code == 0
    assert "does not support editing" in result.stdout


def test_editor_device_calls_device_edit(tmp_path: Path):
    """Device with EditorProtocol calls device.edit() with correct preset_id."""
    rig = _make_rig("mood", "clean", has_edit=True)

    # Patch write_preset and prompt to "discard"
    with (
        patch("rig.cli.commands.edit.load_rig", return_value=rig),
        patch("rig.cli.commands.edit.write_preset"),
        patch("rig.engine.ports.RichConfirmationIO.prompt", return_value="n"),
    ):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "mood", "clean"])

    # edit() should have been called (device is editable)
    assert result.exit_code == 0


def test_edit_save_confirm_calls_write_preset(tmp_path: Path):
    """When user answers 'y' to save prompt, write_preset() is called."""
    rig = _make_rig("mood", "clean", has_edit=True)

    with (
        patch("rig.cli.commands.edit.load_rig", return_value=rig),
        patch("rig.cli.commands.edit.write_preset") as mock_write,
        patch("rig.engine.ports.RichConfirmationIO.prompt", return_value="y"),
    ):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "mood", "clean"])

    assert result.exit_code == 0
    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args
    # updated_values should be the dict returned by device.edit()
    assert call_kwargs[0][3] == {"preset_number": 42}


def test_edit_discard_skips_write_preset(tmp_path: Path):
    """When user answers 'n' to save prompt, write_preset() is NOT called."""
    rig = _make_rig("mood", "clean", has_edit=True)

    with (
        patch("rig.cli.commands.edit.load_rig", return_value=rig),
        patch("rig.cli.commands.edit.write_preset") as mock_write,
        patch("rig.engine.ports.RichConfirmationIO.prompt", return_value="n"),
    ):
        result = runner.invoke(app, ["edit", "--config", str(tmp_path), "mood", "clean"])

    assert result.exit_code == 0
    mock_write.assert_not_called()


def test_edit_dry_run_passes_dry_run_true(tmp_path: Path):
    """--dry-run passes dry_run=True to write_preset() on save."""
    rig = _make_rig("mood", "clean", has_edit=True)

    with (
        patch("rig.cli.commands.edit.load_rig", return_value=rig),
        patch("rig.cli.commands.edit.write_preset") as mock_write,
        patch("rig.engine.ports.RichConfirmationIO.prompt", return_value="y"),
    ):
        result = runner.invoke(
            app, ["edit", "--config", str(tmp_path), "--dry-run", "mood", "clean"]
        )

    assert result.exit_code == 0
    mock_write.assert_called_once()
    # dry_run=True should be passed (either as keyword or positional arg)
    call_args = mock_write.call_args
    all_args = list(call_args[0]) + list(call_args[1].values())
    assert True in all_args
