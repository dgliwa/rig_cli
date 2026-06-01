from __future__ import annotations

from pathlib import Path

import yaml


class IngestError(Exception):
    """Raised when ingest validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_rig_paths(root: str) -> tuple[Path, Path, Path]:
    root_path = Path(root).resolve()
    pedals_dir = root_path / "pedals"
    scenes_dir = root_path / "scenes"
    if not pedals_dir.is_dir():
        raise IngestError(f"Pedals directory not found: {pedals_dir}")
    if not scenes_dir.is_dir():
        raise IngestError(f"Scenes directory not found: {scenes_dir}")
    return root_path, pedals_dir, scenes_dir


def _validate_pedal_preset_exists(pedals_dir: Path, pedal_id: str, preset_id: str) -> None:
    pedal_file = pedals_dir / f"{pedal_id}.yaml"
    if not pedal_file.exists():
        raise IngestError(f"Pedal '{pedal_id}' not found at pedals/{pedal_id}.yaml")

    preset_file = pedals_dir / pedal_id / "presets" / f"{preset_id}.yaml"
    if not preset_file.exists():
        raise IngestError(
            f"Preset '{preset_id}' not found for pedal '{pedal_id}' "
            f"(expected at pedals/{pedal_id}/presets/{preset_id}.yaml)"
        )


def _load_scene_yaml(scene_path: Path) -> dict:
    with open(scene_path) as f:
        data = yaml.safe_load(f) or {}
    return data


def _write_scene_yaml(scene_path: Path, data: dict) -> None:
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scene_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_scene(
    root: str,
    name: str,
    pedal_id: str,
    preset_id: str,
    description: str | None = None,
) -> Path:
    """Create a new scene YAML file with a single device-preset mapping.

    Validates that the pedal and preset exist before writing.
    Raises IngestError for any validation failure.
    """
    _, pedals_dir, scenes_dir = _resolve_rig_paths(root)
    scene_path = scenes_dir / f"{name}.yaml"

    if scene_path.exists():
        raise IngestError(f"Scene '{name}' already exists at scenes/{name}.yaml")

    _validate_pedal_preset_exists(pedals_dir, pedal_id, preset_id)

    data: dict = {
        "name": name,
        "presets": {pedal_id: preset_id},
    }
    if description:
        data["description"] = description

    _write_scene_yaml(scene_path, data)
    return scene_path


def add_device_to_scene(
    root: str,
    name: str,
    pedal_id: str,
    preset_id: str,
) -> Path:
    """Add a device-preset mapping to an existing scene.

    Validates the scene exists, pedal/preset exist, and the pedal is
    not already in the scene.
    Raises IngestError for any validation failure.
    """
    _, pedals_dir, scenes_dir = _resolve_rig_paths(root)
    scene_path = scenes_dir / f"{name}.yaml"

    if not scene_path.exists():
        raise IngestError(f"Scene '{name}' not found at scenes/{name}.yaml")

    _validate_pedal_preset_exists(pedals_dir, pedal_id, preset_id)

    data = _load_scene_yaml(scene_path)
    presets: dict = data.setdefault("presets", {})

    if pedal_id in presets:
        raise IngestError(
            f"Device '{pedal_id}' is already in scene '{name}' "
            f"(use 'ingest scene set' to overwrite)"
        )

    presets[pedal_id] = preset_id
    _write_scene_yaml(scene_path, data)
    return scene_path


def set_device_in_scene(
    root: str,
    name: str,
    pedal_id: str,
    preset_id: str,
) -> Path:
    """Overwrite a device's preset reference in an existing scene.

    Validates the scene exists, pedal/preset exist, and the pedal is
    already present in the scene.
    Raises IngestError for any validation failure.
    """
    _, pedals_dir, scenes_dir = _resolve_rig_paths(root)
    scene_path = scenes_dir / f"{name}.yaml"

    if not scene_path.exists():
        raise IngestError(f"Scene '{name}' not found at scenes/{name}.yaml")

    _validate_pedal_preset_exists(pedals_dir, pedal_id, preset_id)

    data = _load_scene_yaml(scene_path)
    presets: dict = data.get("presets", {})

    if pedal_id not in presets:
        raise IngestError(
            f"Device '{pedal_id}' is not in scene '{name}' (use 'ingest scene add' to add it)"
        )

    presets[pedal_id] = preset_id
    _write_scene_yaml(scene_path, data)
    return scene_path
