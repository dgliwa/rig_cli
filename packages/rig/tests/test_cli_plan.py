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


def _write_analog_rig_with_params(root: Path) -> None:
    """Write an analog rig where the preset has named parameter values."""
    (root / "rig.yaml").write_text(
        """\
name: analog-params-rig
devices:
  - id: tumnus
    name: Tumnus
    type: analog
    config:
      type: manual
    presets:
      - id: crunch
        name: Crunch
        values:
          gain: 8.0
          tone: 7.0
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            tumnus: crunch
"""
    )


def _write_cba_rig_with_params(root: Path) -> None:
    """Write a Chase Bliss rig where the preset has named CC parameters."""
    (root / "rig.yaml").write_text(
        """\
name: cba-params-rig
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
        parameters:
          level: 0.8
          reverb: 0.3
      - id: high-gain
        name: High Gain
        preset_number: 5
        parameters:
          level: 0.9
          reverb: 0.3
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            brothers: high-gain
"""
    )


class TestParamDiffRendering:
    """PLAN-32: param_diff lines appear under ANALOG and CONFIGURE actions."""

    def test_analog_param_diff_lines_shown_when_no_prior_state(self, tmp_path: Path) -> None:
        """Analog action with no prior state shows '?' as before value."""
        _write_analog_rig_with_params(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "gain" in result.output, "Expected 'gain' in param_diff output"
        assert "?" in result.output, "Expected '?' for unknown before value"
        assert "8.0" in result.output, "Expected after value '8.0' in param_diff output"

    def test_analog_param_diff_shows_changed_params_only(self, tmp_path: Path) -> None:
        """Switching analog presets: only changed params appear; unchanged params omitted."""
        (tmp_path / "rig.yaml").write_text(
            """\
name: analog-two-preset-rig
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
          tone: 3.0
      - id: crunch
        name: Crunch
        values:
          gain: 8.0
          tone: 3.0
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        main:
          presets:
            tumnus: crunch
"""
        )
        state_path = tmp_path / ".rig" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})
        )
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "gain" in result.output, "Expected 'gain' param diff in output"
        assert "5.0" in result.output, "Expected before value 5.0 in output"
        assert "8.0" in result.output, "Expected after value 8.0 in output"
        # tone unchanged — must not appear as a diff line
        assert result.output.count("tone") == 0, "Unchanged param 'tone' should not appear"

    def test_verify_action_has_no_param_diff_lines(self, tmp_path: Path) -> None:
        """VERIFY actions must never show param_diff lines."""
        _write_analog_rig_with_params(tmp_path)
        state_path = tmp_path / ".rig" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"devices": {"tumnus": {"last_preset": "crunch"}}, "scenes": {"main": {}}})
        )
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--show-unchanged"])
        # The action is VERIFY — no param_diff lines should appear
        assert "gain" not in result.output, "VERIFY action must not render param_diff lines"

    def test_digital_param_diff_lines_shown_when_changed(self, tmp_path: Path) -> None:
        """Chase Bliss preset change with one changed parameter shows that param diff."""
        _write_cba_rig_with_params(tmp_path)
        state_path = tmp_path / ".rig" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"devices": {"brothers": {"last_preset": "low-gain"}}, "scenes": {}})
        )
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "level" in result.output, "Expected 'level' in param_diff output"
        assert "0.8" in result.output, "Expected before value 0.8"
        assert "0.9" in result.output, "Expected after value 0.9"
        # reverb unchanged — must not appear
        assert "reverb" not in result.output, "Unchanged param 'reverb' should not appear"

    def test_hx_stomp_configure_has_no_param_diff(self, tmp_path: Path) -> None:
        """HX Stomp presets have no parameters; configure action shows no param_diff lines."""
        _write_minimal_digital_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        # Only '~' marker should appear; no indented param lines
        assert "~" in result.output, "Expected '~' for configure action"
        # No param name sub-lines expected — just assert no '→' in param context
        lines = [line for line in result.output.splitlines() if "→" in line]
        assert len(lines) == 0, f"HX Stomp should produce no param diff lines, got: {lines}"


class TestPlanJsonParamDiff:
    """PLAN-32: --format json includes param_diff field on every DeviceAction."""

    def test_json_output_includes_param_diff_field(self, tmp_path: Path) -> None:
        """param_diff key present on every device_action in JSON output."""
        _write_minimal_digital_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code in (0, 2), f"Unexpected exit code: {result.exit_code}"
        data = json.loads(result.output)
        for scene in data["scenes"].values():
            for action in scene["device_actions"]:
                assert "param_diff" in action, (
                    f"DeviceAction for '{action['device']}' missing 'param_diff' key in JSON output"
                )

    def test_json_param_diff_populated_for_analog_action(self, tmp_path: Path) -> None:
        """Analog action with parameters yields populated param_diff list in JSON."""
        _write_analog_rig_with_params(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--format", "json"])
        data = json.loads(result.output)
        scene = data["scenes"]["main"]
        tumnus_action = next(a for a in scene["device_actions"] if a["device"] == "tumnus")
        assert tumnus_action["status"] == "analog"
        assert len(tumnus_action["param_diff"]) == 2
        diff_names = {d["name"] for d in tumnus_action["param_diff"]}
        assert "gain" in diff_names
        assert "tone" in diff_names
        gain_diff = next(d for d in tumnus_action["param_diff"] if d["name"] == "gain")
        assert gain_diff["before"] is None
        assert gain_diff["after"] == 8.0

    def test_json_param_diff_empty_for_verify_action(self, tmp_path: Path) -> None:
        """VERIFY actions always have empty param_diff in JSON output."""
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--format", "json"])
        data = json.loads(result.output)
        for scene in data["scenes"].values():
            for action in scene["device_actions"]:
                if action["status"] == "verify":
                    assert action["param_diff"] == [], (
                        f"VERIFY action for '{action['device']}' must have empty param_diff"
                    )

    def test_json_param_diff_empty_for_hx_stomp(self, tmp_path: Path) -> None:
        """HX Stomp configure actions always have empty param_diff in JSON output."""
        _write_minimal_digital_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--format", "json"])
        data = json.loads(result.output)
        scene = data["scenes"]["main"]
        hx_action = next(a for a in scene["device_actions"] if a["device"] == "hx-stomp")
        assert hx_action["param_diff"] == []
