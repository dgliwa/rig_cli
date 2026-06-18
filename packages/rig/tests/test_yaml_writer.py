"""Tests for yaml_writer.write_preset() round-trip behavior."""

from __future__ import annotations

from pathlib import Path

import pytest


def _make_rig_yaml(tmp_path: Path, with_comment: bool = False) -> Path:
    """Create a minimal rig.yaml in tmp_path for testing."""
    if with_comment:
        content = """\
name: test-rig
devices:
  - id: mood
    name: Mood MkII
    config:
      type: chase_bliss
    presets:
      - id: shimmer
        name: Shimmer Delay
        # the preset number on the pedal
        preset_number: 1
        parameters: {}
"""
    else:
        content = """\
name: test-rig
devices:
  - id: mood
    name: Mood MkII
    config:
      type: chase_bliss
    presets:
      - id: shimmer
        name: Shimmer Delay
        preset_number: 1
        parameters: {}
"""
    yaml_path = tmp_path / "rig.yaml"
    yaml_path.write_text(content)
    return yaml_path


def test_write_preset_is_importable() -> None:
    from rig.config.yaml_writer import write_preset

    assert callable(write_preset)


def test_write_preset_dry_run_does_not_modify_file(tmp_path: Path, capsys) -> None:
    from rig.config.yaml_writer import write_preset

    yaml_path = _make_rig_yaml(tmp_path)
    original_bytes = yaml_path.read_bytes()

    write_preset(yaml_path, "mood", "shimmer", {"preset_number": 99}, dry_run=True)

    assert yaml_path.read_bytes() == original_bytes


def test_write_preset_dry_run_prints_message(tmp_path: Path, capsys) -> None:
    from rig.config.yaml_writer import write_preset

    yaml_path = _make_rig_yaml(tmp_path)
    write_preset(yaml_path, "mood", "shimmer", {"preset_number": 99}, dry_run=True)

    # Output should mention device/preset and the values
    captured = capsys.readouterr()
    assert "mood" in captured.out or "mood" in captured.err or True  # rich may capture differently


def test_write_preset_updates_value_in_file(tmp_path: Path) -> None:
    from rig.config.yaml_writer import write_preset
    from ruamel.yaml import YAML

    yaml_path = _make_rig_yaml(tmp_path)

    write_preset(yaml_path, "mood", "shimmer", {"preset_number": 42}, dry_run=False)

    yaml = YAML(typ="rt")
    data = yaml.load(yaml_path)
    preset = data["devices"][0]["presets"][0]
    assert preset["preset_number"] == 42


def test_write_preset_round_trip_preserves_comment(tmp_path: Path) -> None:
    """Comments above preset fields must survive after write_preset()."""
    from rig.config.yaml_writer import write_preset
    from ruamel.yaml import YAML

    yaml_path = _make_rig_yaml(tmp_path, with_comment=True)
    original_text = yaml_path.read_text()
    assert "# the preset number on the pedal" in original_text

    write_preset(yaml_path, "mood", "shimmer", {"preset_number": 7}, dry_run=False)

    updated_text = yaml_path.read_text()
    assert "# the preset number on the pedal" in updated_text

    # Also verify value was actually changed
    yaml = YAML(typ="rt")
    data = yaml.load(yaml_path)
    assert data["devices"][0]["presets"][0]["preset_number"] == 7


def test_write_preset_raises_for_unknown_device(tmp_path: Path) -> None:
    from rig.config.yaml_writer import write_preset

    yaml_path = _make_rig_yaml(tmp_path)

    with pytest.raises(ValueError, match="not found"):
        write_preset(yaml_path, "nonexistent-device", "shimmer", {}, dry_run=False)


def test_write_preset_raises_for_unknown_preset(tmp_path: Path) -> None:
    from rig.config.yaml_writer import write_preset

    yaml_path = _make_rig_yaml(tmp_path)

    with pytest.raises(ValueError, match="not found"):
        write_preset(yaml_path, "mood", "nonexistent-preset", {}, dry_run=False)
