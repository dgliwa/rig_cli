"""YAML write-back for rig config using ruamel.yaml round-trip mode.

Preserves hand-authored comments and field ordering when updating preset values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_preset(
    config_path: Path,
    device_id: str,
    preset_id: str,
    updated_values: dict[str, Any],
    dry_run: bool,
) -> None:
    """Write updated preset values back to rig.yaml using round-trip mode.

    Uses ruamel.yaml to preserve YAML comments and field ordering.
    Raises ValueError if device_id or preset_id is not found.
    On dry_run=True, prints what would change and skips the file write.
    """
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    data = yaml.load(config_path)

    # Find the device
    device_dict = None
    for device in data.get("devices", []):
        if device.get("id") == device_id:
            device_dict = device
            break

    if device_dict is None:
        raise ValueError(f"Device '{device_id}' not found in {config_path}")

    # Find the preset
    preset_dict = None
    for preset in device_dict.get("presets", []):
        if preset.get("id") == preset_id:
            preset_dict = preset
            break

    if preset_dict is None:
        raise ValueError(f"Preset '{preset_id}' not found on device '{device_id}'")

    if dry_run:
        from rich.console import Console

        console = Console()
        console.print(f"[dim]Would write: {device_id}/{preset_id} with {updated_values}[/dim]")
        return

    # Route each key: into parameters if it lives there, otherwise top-level
    params = preset_dict.get("parameters") or {}
    for key, value in updated_values.items():
        if key in params:
            preset_dict["parameters"][key] = value
        else:
            preset_dict[key] = value

    with config_path.open("w") as f:
        yaml.dump(data, f)
