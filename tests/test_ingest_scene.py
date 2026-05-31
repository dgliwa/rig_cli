import yaml
from pathlib import Path
import pytest

from rig.ingest.scene import (
    create_scene,
    add_device_to_scene,
    set_device_in_scene,
    IngestError,
)


def _make_rig_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a minimal rig repo directory tree for testing."""
    root = tmp_path / "rig"
    pedals_dir = root / "pedals"
    scenes_dir = root / "scenes"
    pedals_dir.mkdir(parents=True)
    scenes_dir.mkdir()
    return root, pedals_dir, scenes_dir


def _add_pedal(pedals_dir: Path, pedal_id: str):
    (pedals_dir / f"{pedal_id}.yaml").write_text(
        f"id: {pedal_id}\nmanufacturer: Test\nmodel: Foo\ntype: digital\nmidi_channel: 1\n"
    )


def _add_preset(pedals_dir: Path, pedal_id: str, preset_id: str):
    preset_dir = pedals_dir / pedal_id / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    (preset_dir / f"{preset_id}.yaml").write_text(
        f"id: {preset_id}\npedal: {pedal_id}\nname: '{preset_id}'\npreset_number: 1\n"
    )


class TestCreateScene:
    def test_create_writes_scene_file(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")

        created = create_scene(str(root), "billy-clean", "hx-stomp", "clean-edge")
        assert created == scenes_dir / "billy-clean.yaml"
        assert created.exists()

        with open(created) as f:
            data = yaml.safe_load(f)
        assert data["name"] == "billy-clean"
        assert data["presets"] == {"hx-stomp": "clean-edge"}

    def test_create_with_description(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")

        created = create_scene(str(root), "test", "hx-stomp", "clean-edge", description="My scene")
        with open(created) as f:
            data = yaml.safe_load(f)
        assert data["description"] == "My scene"

    def test_create_validates_pedal_exists(self, tmp_path):
        root, _, _ = _make_rig_repo(tmp_path)
        with pytest.raises(IngestError, match="Pedal.*not found"):
            create_scene(str(root), "test", "nonexistent", "preset")

    def test_create_validates_preset_exists(self, tmp_path):
        root, pedals_dir, _ = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        with pytest.raises(IngestError, match="Preset.*not found"):
            create_scene(str(root), "test", "hx-stomp", "nonexistent")

    def test_create_fails_if_scene_exists(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        (scenes_dir / "test.yaml").write_text("name: test\npresets: {}\n")
        with pytest.raises(IngestError, match="already exists"):
            create_scene(str(root), "test", "hx-stomp", "clean-edge")

    def test_create_fails_if_pedals_dir_missing(self, tmp_path):
        root = tmp_path / "rig"
        root.mkdir()
        with pytest.raises(IngestError, match="Pedals directory not found"):
            create_scene(str(root), "test", "hx-stomp", "clean-edge")

    def test_create_fails_if_scenes_dir_missing(self, tmp_path):
        root = tmp_path / "rig"
        pedals_dir = root / "pedals"
        pedals_dir.mkdir(parents=True)
        with pytest.raises(IngestError, match="Scenes directory not found"):
            create_scene(str(root), "test", "hx-stomp", "clean-edge")


class TestAddDevice:
    def test_add_device_to_scene(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        _add_pedal(pedals_dir, "brothers")
        _add_preset(pedals_dir, "brothers", "low-gain")

        # Create initial scene
        create_scene(str(root), "test", "hx-stomp", "clean-edge")
        # Add second pedal
        result = add_device_to_scene(str(root), "test", "brothers", "low-gain")
        assert result == scenes_dir / "test.yaml"

        with open(result) as f:
            data = yaml.safe_load(f)
        assert data["presets"] == {"hx-stomp": "clean-edge", "brothers": "low-gain"}

    def test_add_validates_scene_exists(self, tmp_path):
        root, pedals_dir, _ = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        with pytest.raises(IngestError, match="not found"):
            add_device_to_scene(str(root), "nonexistent", "hx-stomp", "clean-edge")

    def test_add_validates_pedal_exists(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        (scenes_dir / "test.yaml").write_text("name: test\npresets: {}\n")
        with pytest.raises(IngestError, match="Pedal.*not found"):
            add_device_to_scene(str(root), "test", "nonexistent", "preset")

    def test_add_validates_preset_exists(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        (scenes_dir / "test.yaml").write_text("name: test\npresets: {}\n")
        with pytest.raises(IngestError, match="Preset.*not found"):
            add_device_to_scene(str(root), "test", "hx-stomp", "nonexistent")

    def test_add_fails_if_device_already_present(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        (scenes_dir / "test.yaml").write_text(
            "name: test\npresets:\n  hx-stomp: clean-edge\n"
        )
        with pytest.raises(IngestError, match="already in scene"):
            add_device_to_scene(str(root), "test", "hx-stomp", "clean-edge")


class TestSetDevice:
    def test_set_device_in_scene(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        _add_preset(pedals_dir, "hx-stomp", "crunch")
        (scenes_dir / "test.yaml").write_text(
            "name: test\npresets:\n  hx-stomp: clean-edge\n"
        )

        result = set_device_in_scene(str(root), "test", "hx-stomp", "crunch")
        with open(result) as f:
            data = yaml.safe_load(f)
        assert data["presets"]["hx-stomp"] == "crunch"

    def test_set_validates_scene_exists(self, tmp_path):
        root, pedals_dir, _ = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        with pytest.raises(IngestError, match="not found"):
            set_device_in_scene(str(root), "nonexistent", "hx-stomp", "clean-edge")

    def test_set_fails_if_device_not_in_scene(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "brothers")
        _add_preset(pedals_dir, "brothers", "low-gain")
        (scenes_dir / "test.yaml").write_text("name: test\npresets: {}\n")
        with pytest.raises(IngestError, match="not in scene"):
            set_device_in_scene(str(root), "test", "brothers", "low-gain")

    def test_set_preserves_other_keys(self, tmp_path):
        root, pedals_dir, scenes_dir = _make_rig_repo(tmp_path)
        _add_pedal(pedals_dir, "hx-stomp")
        _add_preset(pedals_dir, "hx-stomp", "clean-edge")
        _add_preset(pedals_dir, "hx-stomp", "crunch")
        _add_pedal(pedals_dir, "brothers")
        _add_preset(pedals_dir, "brothers", "low-gain")
        (scenes_dir / "test.yaml").write_text(
            "name: test\ndescription: old\ntempo: 120\ntags: [a, b]\npresets:\n  hx-stomp: clean-edge\n  brothers: low-gain\n"
        )

        set_device_in_scene(str(root), "test", "hx-stomp", "crunch")
        with open(scenes_dir / "test.yaml") as f:
            data = yaml.safe_load(f)
        assert data["description"] == "old"
        assert data["tempo"] == 120
        assert data["tags"] == ["a", "b"]
        assert data["presets"]["hx-stomp"] == "crunch"
        assert data["presets"]["brothers"] == "low-gain"
