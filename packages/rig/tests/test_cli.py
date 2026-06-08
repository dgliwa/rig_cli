"""CLI-level tests using typer.testing.CliRunner.

These test the actual CLI commands end-to-end with a minimal rig config.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rig.cli import app

runner = CliRunner()


# ── Helpers ───────────────────────────────────────────────────────────────


def _write_minimal_rig(root: Path) -> None:
    """Create a minimal valid rig config under *root*."""
    (root / "rig.yaml").write_text(
        """\
name: test-rig
description: A minimal test rig
midi_channel: 1
devices:
  - id: tumnus
    name: Tumnus
    type: analog
    config:
      type: manual
    presets: []
"""
    )


# ── Validate ──────────────────────────────────────────────────────────────


class TestValidate:
    def test_validate_valid_config(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(tmp_path)])
        assert result.exit_code == 0
        assert "pedals" in result.stdout
        assert "scenes" in result.stdout

    def test_validate_missing_config(self, tmp_path: Path):
        result = runner.invoke(app, ["validate", "--config", str(tmp_path)])
        assert result.exit_code == 1
        assert "rig.yaml" in result.stdout or "error" in result.stdout.lower()

    def test_validate_json_output(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "valid"
        assert data["pedals"] == 1
        assert data["scenes"] == 0

    def test_validate_json_error(self, tmp_path: Path):
        result = runner.invoke(app, ["validate", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["status"] == "error"
        assert "error" in data


# ── Status ────────────────────────────────────────────────────────────────


class TestStatus:
    def test_status_text(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["status", "--config", str(tmp_path)])
        assert result.exit_code == 0
        assert "test-rig" in result.stdout
        assert "tumnus" in result.stdout

    def test_status_json(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["status", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "test-rig"
        assert "tumnus" in data["pedals"]

    def test_status_error(self, tmp_path: Path):
        result = runner.invoke(app, ["status", "--config", str(tmp_path)])
        assert result.exit_code == 1


# ── Plan ──────────────────────────────────────────────────────────────────


class TestPlan:
    def test_plan_text(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path)])
        assert result.exit_code == 0
        # Either clean state or no scenes message
        assert "No scenes" in result.stdout or "clean" in result.stdout.lower()

    def test_plan_json(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert data["status"] in ("clean", "changes_detected")
        assert "scenes" in data

    def test_plan_verbose(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "-v"])
        assert result.exit_code == 0


# ── Diff ──────────────────────────────────────────────────────────────────


class TestDiff:
    def test_diff_text(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["diff", "--config", str(tmp_path)])
        assert result.exit_code == 0

    def test_diff_json(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["diff", "--config", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "scenes" in data


# ── Generate MC6 ─────────────────────────────────────────────────────────


class TestGenerateMC6:
    def test_generate_mc6_no_config(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["generate", "mc6", "--config", str(tmp_path)])
        assert result.exit_code == 0
        assert "no mc6 configuration found" in result.stdout.lower()


# ── Output format option ────────────────────────────────────────────────


class TestFormatOption:
    """Verify that --format/-f works on all supported commands."""

    def test_validate_short_format_flag(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["validate", "--config", str(tmp_path), "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "valid"

    def test_plan_short_format_flag(self, tmp_path: Path):
        _write_minimal_rig(tmp_path)
        result = runner.invoke(app, ["plan", "--config", str(tmp_path), "-f", "json"])
        assert result.exit_code == 0
        json.loads(result.stdout)
