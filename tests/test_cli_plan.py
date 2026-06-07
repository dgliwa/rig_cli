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
    """Write a minimal rig with one digital device, one controller, and one scene under *root*.

    Scenes must be wired through a CONTROLLER device's ControllerConfig for
    Rig.scenes to resolve — matching the loader's domain model.
    """
    devices = root / "devices"
    devices.mkdir(parents=True)

    # HX Stomp (modeler) device
    (devices / "hx-stomp.yaml").write_text(
        """\
id: hx-stomp
name: HX Stomp XL
manufacturer: Line 6
model: HX Stomp XL
type: modeler
config:
  type: midi
  midi_channel: 1
"""
    )

    presets_dir = devices / "hx-stomp" / "presets"
    presets_dir.mkdir(parents=True)
    (presets_dir / "clean.yaml").write_text(
        """\
id: clean
name: Clean
preset_number: 1
hlx_file: hlx/clean.hlx
"""
    )

    # MC6 controller device — scenes are wired through it
    (devices / "mc6.yaml").write_text(
        """\
id: mc6
name: MC6
manufacturer: Morningstar
model: MC6
type: controller
config:
  type: controller
  midi_channel: 1
"""
    )

    scenes_dir = root / "scenes"
    scenes_dir.mkdir(parents=True)
    (scenes_dir / "main.yaml").write_text(
        """\
name: main
presets:
  hx-stomp: clean
"""
    )

    (root / "rig.yaml").write_text(
        """\
name: test-rig
"""
    )
    (root / "signal-chain.yaml").write_text(
        """\
chain:
  - device: hx-stomp
    position: 1
    loop: front
    stereo: false
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

    def test_cba_setup_actions_shown_in_setup_actions_section(self, tmp_path: Path) -> None:
        """D-09: A CBA device in fresh state produces Setup Actions section in output."""
        _write_cba_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "Setup Actions" in result.output

    def test_cba_plan_summary_reflects_nonzero_count(self, tmp_path: Path) -> None:
        """D-09: Summary line is non-zero when CBA setup actions exist."""
        _write_cba_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        # The plan has CBA setup actions → output must show a nonzero total in summary
        assert "Plan:" in result.output
        # CBA setup should drive the plan to show some count (configure or setup actions)
        # The summary line must NOT read "0 to configure" when CBA setup actions exist
        import re

        configure_match = re.search(r"Plan: (\d+) to configure", result.output)
        if configure_match:
            count = int(configure_match.group(1))
            assert count > 0, (
                "Summary line shows '0 to configure' but CBA setup actions exist — "
                "CBA setup actions are not reflected in the summary count."
            )


def _write_cba_rig(root: Path) -> None:
    """Write a minimal rig with one Chase Bliss device (no prior state) under *root*."""
    devices = root / "devices"
    devices.mkdir(parents=True)

    (devices / "brothers.yaml").write_text(
        """\
id: brothers
name: Brothers
manufacturer: Chase Bliss Audio
model: Brothers
type: digital
config:
  type: chase_bliss
  midi_channel: 3
"""
    )

    presets_dir = devices / "brothers" / "presets"
    presets_dir.mkdir(parents=True)
    (presets_dir / "low-gain.yaml").write_text(
        """\
id: low-gain
name: Low Gain
pedal: brothers
preset_number: 4
"""
    )

    (devices / "mc6.yaml").write_text(
        """\
id: mc6
name: MC6
manufacturer: Morningstar
model: MC6
type: controller
config:
  type: controller
  midi_channel: 1
"""
    )

    scenes_dir = root / "scenes"
    scenes_dir.mkdir(parents=True)
    (scenes_dir / "main.yaml").write_text(
        """\
name: main
presets:
  brothers: low-gain
"""
    )

    (root / "rig.yaml").write_text("name: cba-test-rig\n")
    (root / "signal-chain.yaml").write_text("chain: []\n")


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

    def test_cba_setup_action_uses_tilde_marker(self, tmp_path: Path) -> None:
        """CBA setup actions display ~ marker."""
        _write_cba_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert "Setup Actions" in result.output
        assert "~" in result.output, "Expected '~' marker for CBA setup action"


def _write_analog_rig(root: Path) -> None:
    """Write a minimal rig with one analog (manual) device under *root*."""
    devices = root / "devices"
    devices.mkdir(parents=True)

    (devices / "tumnus.yaml").write_text(
        """\
id: tumnus
name: Tumnus
manufacturer: Wampler
model: Tumnus
type: analog
config:
  type: manual
"""
    )

    presets_dir = devices / "tumnus" / "presets"
    presets_dir.mkdir(parents=True)
    (presets_dir / "edge.yaml").write_text(
        """\
id: edge
name: Edge of Breakup
pedal: tumnus
values:
  gain: 5.0
"""
    )

    (devices / "mc6.yaml").write_text(
        """\
id: mc6
name: MC6
manufacturer: Morningstar
model: MC6
type: controller
config:
  type: controller
  midi_channel: 1
"""
    )

    scenes_dir = root / "scenes"
    scenes_dir.mkdir(parents=True)
    (scenes_dir / "main.yaml").write_text(
        """\
name: main
presets:
  tumnus: edge
"""
    )

    (root / "rig.yaml").write_text("name: analog-test-rig\n")
    (root / "signal-chain.yaml").write_text("chain: []\n")


class TestShowUnchanged:
    """PLAN-08: --show-unchanged flag controls visibility of unchanged scenes."""

    def test_unchanged_scene_hidden_without_flag(self, tmp_path: Path) -> None:
        """Without --show-unchanged, unchanged scenes do not appear in output."""
        _write_minimal_digital_rig(tmp_path)
        _write_state_matching_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        # The "main" scene should NOT appear since it is unchanged and flag is absent
        # The scene section header may appear, but the scene name should not
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
        """Write a rig with two scenes: main and alt."""
        devices = root / "devices"
        devices.mkdir(parents=True)

        (devices / "hx-stomp.yaml").write_text(
            """\
id: hx-stomp
name: HX Stomp XL
manufacturer: Line 6
model: HX Stomp XL
type: modeler
config:
  type: midi
  midi_channel: 1
"""
        )

        presets_dir = devices / "hx-stomp" / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "clean.yaml").write_text(
            """\
id: clean
name: Clean
preset_number: 1
hlx_file: hlx/clean.hlx
"""
        )
        (presets_dir / "drive.yaml").write_text(
            """\
id: drive
name: Drive
preset_number: 2
hlx_file: hlx/drive.hlx
"""
        )

        (devices / "mc6.yaml").write_text(
            """\
id: mc6
name: MC6
manufacturer: Morningstar
model: MC6
type: controller
config:
  type: controller
  midi_channel: 1
"""
        )

        scenes_dir = root / "scenes"
        scenes_dir.mkdir(parents=True)
        (scenes_dir / "main.yaml").write_text(
            """\
name: main
presets:
  hx-stomp: clean
"""
        )
        (scenes_dir / "alt.yaml").write_text(
            """\
name: alt
presets:
  hx-stomp: drive
"""
        )

        (root / "rig.yaml").write_text("name: two-scene-rig\n")
        (root / "signal-chain.yaml").write_text(
            """\
chain:
  - device: hx-stomp
    position: 1
    loop: front
    stereo: false
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
