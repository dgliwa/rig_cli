"""CLI-level tests for rig apply --device / --preset flags.

Covers:
- D-04: --scene conflicts with --device/--preset
- D-05: --preset requires --device (reversed: --device alone is now valid)
- D-06: unknown device/preset IDs exit 1 before any MIDI port opens
- Routing: --device + --preset routes to apply_device_preset(); --device alone routes to apply_plan
  with device_filter; no flags routes to apply_plan()
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from rig.cli import app

runner = CliRunner()


# ── Helpers ────────────────────────────────────────────────────────────────


def _write_minimal_rig(root: Path) -> None:
    """Create a minimal valid rig config with one device and one preset."""
    (root / "rig.yaml").write_text(
        """\
name: test-rig
description: A minimal test rig
midi_channel: 1
devices:
  - id: klon
    name: Klon
    type: analog
    config:
      type: manual
    presets:
      - id: clean
        name: Clean Tone
        values: {}
"""
    )


# ── Flag validation tests ─────────────────────────────────────────────────


class TestDevicePresetFlagValidation:
    def test_device_without_preset_routes_to_apply_plan(self, tmp_path: Path):
        """--device without --preset is now valid and routes to apply_plan with device_filter."""
        _write_minimal_rig(tmp_path)
        mock_apply_plan = MagicMock(return_value=MagicMock(status="completed"))
        mock_compute_plan = MagicMock(return_value=MagicMock(status="clean"))
        with (
            patch("rig.cli.commands.apply.apply_plan", mock_apply_plan),
            patch("rig.cli.commands.apply.compute_plan", mock_compute_plan),
            patch("rig.midi.adapter.MidiManager.disconnect_all"),
        ):
            result = runner.invoke(app, ["apply", "--config", str(tmp_path), "--device", "klon"])
        assert result.exit_code == 0
        mock_apply_plan.assert_called_once()
        call_kwargs = mock_apply_plan.call_args.kwargs
        assert call_kwargs.get("device_filter") == "klon"

    def test_preset_without_device_exits_1(self, tmp_path: Path):
        """--preset without --device should exit 1 with a clear error."""
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["apply", "--config", str(tmp_path), "--preset", "clean"])
        assert result.exit_code == 1
        assert "--preset requires --device" in result.stdout

    def test_scene_and_device_conflict_exits_1(self, tmp_path: Path):
        """--scene combined with --device/--preset should exit 1 with a clear error."""
        _write_minimal_rig(tmp_path)
        result = runner.invoke(
            app,
            [
                "apply",
                "--config",
                str(tmp_path),
                "--scene",
                "live",
                "--device",
                "klon",
                "--preset",
                "clean",
            ],
        )
        assert result.exit_code == 1
        assert "--scene cannot be combined with --device/--preset" in result.stdout

    def test_unknown_device_exits_1(self, tmp_path: Path):
        """Unknown device ID should exit 1 with 'not found in rig config' message."""
        _write_minimal_rig(tmp_path)
        result = runner.invoke(
            app,
            ["apply", "--config", str(tmp_path), "--device", "nonexistent", "--preset", "clean"],
        )
        assert result.exit_code == 1
        assert "not found in rig config" in result.stdout

    def test_unknown_preset_exits_1(self, tmp_path: Path):
        """Known device but unknown preset ID should exit 1 with 'not found on device' message."""
        _write_minimal_rig(tmp_path)
        result = runner.invoke(
            app,
            ["apply", "--config", str(tmp_path), "--device", "klon", "--preset", "nonexistent"],
        )
        assert result.exit_code == 1
        assert "not found on device" in result.stdout


# ── Routing tests ─────────────────────────────────────────────────────────


class TestApplyRouting:
    def test_no_flags_uses_existing_apply_plan_path(self, tmp_path: Path):
        """Without --device/--preset, compute_plan + apply_plan should be called."""
        _write_minimal_rig(tmp_path)
        mock_apply_plan = MagicMock(return_value=MagicMock(status="completed"))
        mock_compute_plan = MagicMock(return_value=MagicMock(status="clean"))

        with (
            patch("rig.cli.commands.apply.apply_plan", mock_apply_plan),
            patch("rig.cli.commands.apply.compute_plan", mock_compute_plan),
            patch("rig.midi.adapter.MidiManager.disconnect_all"),
        ):
            result = runner.invoke(app, ["apply", "--config", str(tmp_path), "--dry-run"])

        assert result.exit_code == 0
        mock_compute_plan.assert_called_once()
        mock_apply_plan.assert_called_once()

    def test_device_preset_flags_route_to_apply_device_preset(self, tmp_path: Path):
        """With --device and --preset, apply_device_preset is called; apply_plan is NOT called."""
        _write_minimal_rig(tmp_path)
        mock_apply_device_preset = MagicMock(
            return_value=MagicMock(status="confirmed", device="klon", preset="clean")
        )
        mock_apply_plan = MagicMock()

        with (
            patch("rig.engine.apply.apply_device_preset", mock_apply_device_preset),
            patch("rig.cli.commands.apply.apply_plan", mock_apply_plan),
            patch("rig.midi.adapter.MidiManager.disconnect_all"),
        ):
            result = runner.invoke(
                app,
                [
                    "apply",
                    "--config",
                    str(tmp_path),
                    "--device",
                    "klon",
                    "--preset",
                    "clean",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        mock_apply_plan.assert_not_called()
        mock_apply_device_preset.assert_called_once()


# ── Device-only routing tests ─────────────────────────────────────────────


class TestDeviceOnlyApply:
    def test_device_without_preset_routes_to_apply_plan_with_filter(self, tmp_path: Path):
        """--device without --preset calls apply_plan with device_filter, not apply_device_preset."""
        _write_minimal_rig(tmp_path)
        mock_apply_plan = MagicMock(return_value=MagicMock(status="completed"))
        mock_compute_plan = MagicMock(return_value=MagicMock(status="clean"))
        mock_apply_device_preset = MagicMock()
        with (
            patch("rig.cli.commands.apply.apply_plan", mock_apply_plan),
            patch("rig.cli.commands.apply.compute_plan", mock_compute_plan),
            patch("rig.engine.apply.apply_device_preset", mock_apply_device_preset),
            patch("rig.midi.adapter.MidiManager.disconnect_all"),
        ):
            result = runner.invoke(app, ["apply", "--config", str(tmp_path), "--device", "klon"])
        assert result.exit_code == 0
        mock_apply_device_preset.assert_not_called()
        mock_apply_plan.assert_called_once()
        call_kwargs = mock_apply_plan.call_args.kwargs
        assert call_kwargs.get("device_filter") == "klon"

    def test_device_only_unknown_device_exits_1(self, tmp_path: Path):
        """--device without --preset with an unknown device ID exits 1."""
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["apply", "--config", str(tmp_path), "--device", "nonexistent"])
        assert result.exit_code == 1
        assert "not found in rig config" in result.stdout
