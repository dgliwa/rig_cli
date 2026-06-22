"""CLI smoke tests for the plan command.

These tests use typer.testing.CliRunner and a minimal in-memory rig config
written to tmp_path. They assert exit codes and key output strings without
testing every rendering detail.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rig.cli import app

runner = CliRunner()


def _write_minimal_digital_rig(root: Path) -> None:
    """Write a minimal rig with one digital device, one controller, and one scene.

    Uses the new single-file rig.yaml schema (Phase 10).
    """
    (root / "rig.yaml").write_text(
        """\
name: test-rig
devices:
  - id: hx-stomp
    name: HX Stomp XL
    type: modeler
    config:
      type: midi
      midi_channel: 1
    presets:
      - id: clean
        name: Clean
        preset_number: 1
        hlx_file: hlx/clean.hlx
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            hx-stomp: clean
"""
    )


def _write_state_matching_rig(root: Path) -> None:
    """Write a state.json that matches the minimal rig so the plan is clean."""
    state_dir = root / ".rig"
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "devices": {"hx-stomp": {"last_preset": "clean"}},
                "scenes": {"main": {}},
            }
        )
    )


class TestPlanExitCodes:
    def test_plan_exits_0_when_clean(self, tmp_path: Path) -> None:
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert result.exit_code == 0

    def test_plan_exits_2_when_changes_detected(self, tmp_path: Path) -> None:
        _write_minimal_digital_rig(tmp_path)
        # No state.json → all scenes are new → changes_detected
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert result.exit_code == 2


class TestPlanColdStart:
    def test_plan_cold_start_warning(self, tmp_path: Path) -> None:
        _write_minimal_digital_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "Cold start" in result.output


class TestPlanSummaryLine:
    def test_plan_summary_line_present_when_clean(self, tmp_path: Path) -> None:
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "Plan:" in result.output
        assert "No changes" in result.output


def _write_cba_rig(root: Path) -> None:
    """Write a minimal rig with one Chase Bliss device (no prior state).

    Uses the new single-file rig.yaml schema (Phase 10).
    """
    (root / "rig.yaml").write_text(
        """\
name: cba-test-rig
devices:
  - id: brothers
    name: Brothers
    type: digital
    config:
      type: chase_bliss
      midi_channel: 3
    presets:
      - id: low-gain
        name: Low Gain
        preset_number: 4
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            brothers: low-gain
"""
    )


class TestPlanVisualMarkers:
    """D-08 / PLAN-03: CLI output uses correct visual markers per action type."""

    def test_configure_action_uses_tilde_marker(self, tmp_path: Path) -> None:
        """configure actions display ~ marker."""
        _write_minimal_digital_rig(tmp_path)
        # No state → scene is "new" → device_action status is "configure"
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "~" in result.output, "Expected '~' marker for configure action"

    def test_verify_action_uses_checkmark_marker(self, tmp_path: Path) -> None:
        """verify actions display ✓ marker."""
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--show-unchanged"])
        assert "✓" in result.output, "Expected '✓' marker for verify action"

    def test_analog_action_uses_warning_marker(self, tmp_path: Path) -> None:
        """analog (manual) actions display ⚠ marker."""
        _write_analog_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "⚠" in result.output, "Expected '⚠' marker for analog action"

    def test_analog_verify_action_uses_checkmark_marker(self, tmp_path: Path) -> None:
        """STATE-01: analog device already at correct preset displays ✓, not ⚠."""
        _write_analog_rig(tmp_path)
        import json

        state_path = tmp_path / ".rig" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        # Mark the scene as applied and the device as already at the right preset
        state_path.write_text(
            json.dumps({"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {"main": {}}})
        )
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--show-unchanged"])
        assert "✓" in result.output, (
            "Expected '✓' marker for analog device already at correct preset"
        )
        assert "⚠" not in result.output, (
            "Expected no '⚠' marker for analog device already at correct preset"
        )


def _write_analog_rig(root: Path) -> None:
    """Write a minimal rig with one analog (manual) device.

    Uses the new single-file rig.yaml schema (Phase 10).
    """
    (root / "rig.yaml").write_text(
        """\
name: analog-test-rig
devices:
  - id: tumnus
    name: Tumnus
    type: analog
    config:
      type: manual
    presets:
      - id: edge
        name: Edge of Breakup
        values:
          gain: 5.0
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            tumnus: edge
"""
    )


class TestShowUnchanged:
    """PLAN-08: --show-unchanged flag controls visibility of unchanged scenes."""

    def test_unchanged_scene_hidden_without_flag(self, tmp_path: Path) -> None:
        """Without --show-unchanged, unchanged scenes do not appear in output."""
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        # The "main" scene should NOT appear since it is unchanged and flag is absent
        assert "main (unchanged)" not in result.output

    def test_unchanged_scene_visible_with_flag(self, tmp_path: Path) -> None:
        """With --show-unchanged, unchanged scenes appear in output."""
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--show-unchanged"])
        assert "main" in result.output
        assert "unchanged" in result.output


class TestSceneFilter:
    """PLAN-09: --scene <name> filter shows only that scene."""

    def _write_two_scene_rig(self, root: Path) -> None:
        """Write a rig with two scenes: main and alt.

        Uses the new single-file rig.yaml schema (Phase 10).
        """
        (root / "rig.yaml").write_text(
            """\
name: two-scene-rig
devices:
  - id: hx-stomp
    name: HX Stomp XL
    type: modeler
    config:
      type: midi
      midi_channel: 1
    presets:
      - id: clean
        name: Clean
        preset_number: 1
        hlx_file: hlx/clean.hlx
      - id: drive
        name: Drive
        preset_number: 2
        hlx_file: hlx/drive.hlx
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            hx-stomp: clean
        alt:
          presets:
            hx-stomp: drive
"""
        )

    def test_scene_filter_shows_only_named_scene(self, tmp_path: Path) -> None:
        """--scene main shows the main scene and omits alt."""
        self._write_two_scene_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--scene", "main"])
        assert "main" in result.output
        assert "alt" not in result.output

    def test_scene_filter_omits_other_scenes(self, tmp_path: Path) -> None:
        """Without --scene, both scenes appear in output."""
        self._write_two_scene_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "main" in result.output
        assert "alt" in result.output
