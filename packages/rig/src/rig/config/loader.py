"""Rig config loader — reads a single rig.yaml and produces a Rig model.

The single-file schema (v2.0+):
  name: sample-rig
  description: ...
  scenes:
    lead:
      presets: {hx-stomp: lead, mood: preset-1}
      tempo: 120
  devices:
    - id: mood
      type: chase_bliss
      config: {type: chase_bliss, ...}
      presets:
        - id: preset-1
          name: Shimmer Delay
          preset_number: 1
          ...
    - id: mc6
      type: controller
      config:
        type: controller
        midi_channel: 1
        banks: [...]

Scenes are a top-level key in rig.yaml (not nested under any device config).
Device list order defines the signal chain. Device construction is dispatched
to plugins via entry points keyed on ``config.type``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pydantic
import yaml

from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError, ValidationError
from rig.engine.plugin_registry import get_registry
from rig.models.rig import Rig
from rig.models.scene import Scene

logger = logging.getLogger(__name__)


def _resolve(root: Path, *parts: str) -> Path:
    result = root.joinpath(*parts).resolve()
    logger.debug("Resolved path: %s", result)
    return result


def _read_yaml(path: Path):
    """Read a YAML file and return its contents as a dict."""
    logger.debug("Reading YAML file: %s", path)
    if not path.exists():
        logger.error("Missing file: %s", path)
        raise FileNotFoundError_(f"Missing file: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ParseError(f"Empty or blank YAML file: {path}")
        logger.debug("Loaded YAML from %s (%d bytes)", path, path.stat().st_size)
        return data
    except yaml.YAMLError as e:
        logger.error("Invalid YAML in %s: %s", path, e)
        raise ParseError(f"Invalid YAML in {path}: {e}")


def _parse_device(data: dict) -> Any:
    """Parse a raw device YAML dict into a plugin device instance.

    Dispatches to the model class registered for the config type, then
    delegates all parsing (config coercion, preset construction, etc.)
    to the plugin's own ``from_raw_yaml`` classmethod.

    Wraps pydantic.ValidationError in a clean rig.config.errors.ValidationError
    so callers see a ConfigError (not a raw Pydantic traceback). This is the
    enforcement point for extra="forbid" on device configs — a stale scenes:
    key under an MC6 controller config will be caught here.
    """
    config_data = data.get("config") or {}
    config_type = config_data.get("type") if isinstance(config_data, dict) else None
    model_class = get_registry().get_model(config_type)
    if model_class is None:
        raise ValidationError(
            f"Unknown device config type '{config_type}' — is the plugin registered?"
        )
    try:
        return model_class.from_raw_yaml(data)
    except pydantic.ValidationError as e:
        raise ValidationError(str(e)) from e


def _validate_references(rig: Rig):
    """Validate all cross-references in the rig configuration."""
    device_ids = set(rig.devices.keys())
    controller_id = rig.controller.id if rig.controller else None
    valid_chain_ids = device_ids | ({controller_id} if controller_id else set())

    known_presets: dict[str, set[str]] = {
        device_id: {p.id for p in device.presets} for device_id, device in rig.devices.items()
    }

    logger.debug("Validating signal chain references")
    for device_id in rig.signal_chain:
        if device_id not in valid_chain_ids:
            logger.error("Signal chain references unknown device '%s'", device_id)
            raise MissingReferenceError(f"Signal chain references unknown device '{device_id}'")

    logger.debug("Validating scene preset references")
    for scene_name, scene in rig.scenes.items():
        for device_id, preset_id in scene.presets.items():
            if device_id not in device_ids:
                logger.error("Scene '%s' references unknown device '%s'", scene_name, device_id)
                raise MissingReferenceError(
                    f"Scene '{scene_name}' references unknown device '{device_id}'"
                )
            if preset_id not in known_presets.get(device_id, set()):
                logger.error(
                    "Scene '%s': device '%s' has no preset '%s'", scene_name, device_id, preset_id
                )
                raise MissingReferenceError(
                    f"Scene '{scene_name}': device '{device_id}' has no preset '{preset_id}'"
                )

    logger.debug("All cross-references valid")


def load_rig(root_path: str) -> Rig:
    """Load a rig configuration from a single ``rig.yaml`` file.

    ``root_path`` may be:
    - A directory containing ``rig.yaml``
    - A direct path to ``rig.yaml``

    Returns a populated ``Rig`` model with plugin device instances.
    """
    root = Path(root_path).resolve()

    # Determine the YAML file path
    if root.is_dir():
        yaml_path = root / "rig.yaml"
    else:
        yaml_path = root

    logger.info("Loading rig config from: %s", yaml_path)
    data = _read_yaml(yaml_path)

    # Extract top-level rig info
    rig_name = data.get("name", "")
    rig_description = data.get("description")
    rig_midi_channel = data.get("midi_channel")

    # Parse top-level scenes: key — scenes are independent of any device config
    raw_scenes: dict[str, Any] = data.get("scenes") or {}
    scenes: dict[str, Scene] = {}
    for scene_name, scene_data in raw_scenes.items():
        if isinstance(scene_data, dict):
            scenes[scene_name] = Scene(
                name=scene_name,
                description=scene_data.get("description"),
                tempo=scene_data.get("tempo"),
                presets=scene_data.get("presets", {}),
                tags=scene_data.get("tags", []),
            )

    # Parse devices list — order defines signal chain
    device_list: list[dict] = data.get("devices", [])
    devices: dict[str, Any] = {}
    signal_chain: list[str] = []

    for device_entry in device_list:
        device = _parse_device(device_entry)
        devices[device.id] = device
        signal_chain.append(device.id)

    rig = Rig(
        name=rig_name,
        description=rig_description,
        midi_channel=rig_midi_channel,
        signal_chain=signal_chain,
        devices=devices,
        scenes=scenes,
    )

    _validate_references(rig)
    logger.info(
        "Rig '%s' loaded successfully (%d devices, %d scenes)",
        rig.name,
        len(rig.devices),
        len(rig.scenes),
    )
    return rig
