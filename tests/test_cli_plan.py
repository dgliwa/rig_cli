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
