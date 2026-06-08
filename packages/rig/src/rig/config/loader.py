"""Rig config loader — reads a single rig.yaml and produces a Rig model.

The new single-file schema (v1.2+):
  name: sample-rig
  description: ...
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
        scenes:
          lead:
            presets: {hx-stomp: lead, mood: preset-1}
        banks: [...]

Device list order defines the signal chain. Scenes live inside the controller
device's config. Device construction is dispatched to plugins via entry points
keyed on ``config.type``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError, ValidationError
from rig.engine.plugin_registry import get_registry
from rig.models.device import DeviceType
from rig.models.preset import Preset
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


def _parse_presets(device_type: str, preset_list: list[dict]) -> list[Preset]:
    """Parse raw preset dicts into the correct preset model type.

    Dispatches to the correct plugin's preset model based on device_type.
    """
    if not preset_list:
        return []
    if device_type == "analog":
        from rig_analog.preset import AnalogPreset

        return [AnalogPreset(**p) for p in preset_list]
    if device_type == "modeler":
        from rig_hx.preset import HXStompPreset

        return [HXStompPreset(**p) for p in preset_list]
    from rig_chasebliss.preset import DigitalPreset

    return [DigitalPreset(**p) for p in preset_list]


def _parse_device(data: dict) -> Any:
    """Parse a device entry dict into a concrete plugin device model.

    Dispatches to the plugin model class registered for ``config.type``
    via entry points. Presets are parsed into the correct model type
    based on ``device_type`` (analog→AnalogPreset, modeler→HXStompPreset,
    digital/other→DigitalPreset). Unknown config types raise
    ``ValidationError``.
    """
    config_data = data.get("config") or {}
    config_type = config_data.get("type") if isinstance(config_data, dict) else None
    model_class = get_registry().get_model(config_type)
    if model_class is None:
        raise ValidationError(
            f"Unknown device config type '{config_type}' — is the plugin registered?"
        )
    # Parse presets into proper model types before passing to plugin model
    device_type = data.get("type", "")
    raw_presets = data.get("presets", []) or []
    parsed_presets = _parse_presets(device_type, raw_presets)
    device_data = {
        **data,
        "presets": parsed_presets,
    }
    return model_class(**device_data)


def _extract_controller_scenes(device_raw: dict, device: Any) -> dict[str, Scene]:
    """Extract Scene objects from a controller device's config.

    Scenes are defined under ``config.scenes`` in the raw YAML data. Each scene
    has ``presets: {device_id: preset_id}`` and optional ``description``/``tags``.
    Controller-specific fields like ``bank``/``switch`` stay in the device config
    and are NOT put on the Scene model.
    """
    config_raw = device_raw.get("config", {})
    controller_scenes = config_raw.get("scenes", {})
    if not isinstance(controller_scenes, dict):
        return {}

    scenes: dict[str, Scene] = {}
    for scene_name, scene_data in controller_scenes.items():
        if not isinstance(scene_data, dict):
            continue
        scenes[scene_name] = Scene(
            name=scene_name,
            description=scene_data.get("description"),
            presets=scene_data.get("presets", {}),
            tags=scene_data.get("tags", []),
        )
    return scenes


def _get_composes(device: Any) -> list[str]:
    """Extract the list of composed device IDs from a controller device."""
    if isinstance(device.config, dict):
        return device.config.get("composes", [])
    return getattr(device.config, "composes", [])


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

    logger.debug("Validating controller composes references")
    for device in rig.devices.values():
        if device.type == DeviceType.CONTROLLER:
            composed_ids = _get_composes(device)
            for cid in composed_ids:
                if cid not in device_ids:
                    raise MissingReferenceError(
                        f"Controller '{device.id}' composes unknown device '{cid}'"
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

    # Parse devices list — order defines signal chain
    device_list: list[dict] = data.get("devices", [])
    devices: dict[str, Any] = {}
    signal_chain: list[str] = []
    scenes: dict[str, Scene] = {}

    for device_entry in device_list:
        device = _parse_device(device_entry)
        devices[device.id] = device
        signal_chain.append(device.id)

        # Extract scenes from controller devices
        if device.type == DeviceType.CONTROLLER:
            device_scenes = _extract_controller_scenes(device_entry, device)
            scenes.update(device_scenes)

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
