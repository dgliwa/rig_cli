import logging
from pathlib import Path

import yaml

from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError, ValidationError
from rig.models.controller import Controller, ControllerType, MC6Config
from rig.models.device import ChaseBlissConfig, Device, DeviceType
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition

logger = logging.getLogger(__name__)


def _resolve(root: Path, *parts: str) -> Path:
    result = root.joinpath(*parts).resolve()
    logger.debug("Resolved path: %s", result)
    return result


# TODO: If we pass pydantic model
def _read_yaml(path: Path):
    logger.debug("Reading YAML file: %s", path)
    if not path.exists():
        logger.error("Missing file: %s", path)
        raise FileNotFoundError_(f"Missing file: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        logger.debug("Loaded YAML from %s (%d bytes)", path, path.stat().st_size)
        return data
    except yaml.YAMLError as e:
        logger.error("Invalid YAML in %s: %s", path, e)
        raise ParseError(f"Invalid YAML in {path}: {e}")


def _parse_device(data: dict) -> Device:
    # TODO:
    return Device(**data)


def _parse_controller_legacy(pedal_data: dict, mc6_data: dict) -> Controller:
    """Build a Controller from the old pedals/mc6.yaml + mc6.yaml layout."""
    midi_channel = (pedal_data.get("config") or {}).get("midi_channel", 1)
    return Controller(
        id=pedal_data["id"],
        manufacturer=pedal_data.get("manufacturer", "Morningstar"),
        model=pedal_data.get("model", "MC6"),
        type=ControllerType.MC6,
        config=MC6Config(
            midi_channel=midi_channel,
            banks=mc6_data.get("banks", []),
        ),
    )


def _load_devices_dir(
    devices_dir: Path, mc6_data: dict
) -> tuple[
    dict[str, Device], Controller | None
]:  # TODO: Once we resolve the legacy stuff this can just return devices by id?
    """Load all device YAML files; route controller-typed entries to Controller."""
    devices: dict[str, Device] = {}
    controller: Controller | None = None
    logger.debug("Loading device definitions from: %s", devices_dir)
    for path in sorted(devices_dir.glob("*.yaml")):
        data = _read_yaml(path)
        if data.get("type") == "controller":
            # TODO: get rid of this legacy stuff?
            controller = _parse_controller_legacy(data, mc6_data)
            logger.debug("Loaded controller '%s'", controller.id)
        else:
            device = _parse_device(data)
            devices[device.id] = device
            logger.debug("Loaded device '%s' (%s %s)", device.id, device.manufacturer, device.model)
    logger.info("Loaded %d devices", len(devices))
    return devices, controller


# TODO: if we require presets be inline this is not necessary?
def _merge_presets(devices_dir: Path, devices: dict[str, Device]) -> dict[str, Device]:
    """Merge filesystem presets onto device objects (inline presets take priority)."""
    updated: dict[str, Device] = {}
    for device_id, device in devices.items():
        if device.presets:
            # Inline presets already present; no directory loading needed
            updated[device_id] = device
            logger.debug("Using %d inline presets for '%s'", len(device.presets), device_id)
            continue

        # TODO: Maybe everything underneath this is unnecessary? I think the inline presets is the way to go
        preset_dir = devices_dir / device_id / "presets"
        if not preset_dir.is_dir():
            updated[device_id] = device
            continue

        presets: list[AnalogPreset | DigitalPreset | HXStompPreset] = []
        # TODO: There's _gotta_ be a better way to parse this than big sets of conditionals
        for path in sorted(preset_dir.glob("*.yaml")):
            data = _read_yaml(path)
            if device.type == DeviceType.ANALOG:
                presets.append(AnalogPreset(**data))
            elif device.type == DeviceType.MODELER:
                presets.append(HXStompPreset(**data))
            else:
                presets.append(DigitalPreset(**data))
        # TODO: assert_never

        if presets:
            # TODO: why this?
            device = device.model_copy(update={"presets": presets})
            logger.debug("Loaded %d directory presets for '%s'", len(presets), device_id)
        updated[device_id] = device

    return updated


def _load_scenes(scenes_dir: Path) -> dict[str, Scene]:
    scenes: dict[str, Scene] = {}
    logger.debug("Loading scenes from: %s", scenes_dir)
    for path in sorted(scenes_dir.glob("*.yaml")):
        data = _read_yaml(path)
        scene = Scene(**data)
        scenes[scene.name] = scene
        logger.debug("Loaded scene '%s' with %d device(s)", scene.name, len(scene.presets))
    logger.info("Loaded %d scenes", len(scenes))
    return scenes


# TODO: This should in general leverage the abstractions to determine if the individual pieces are valid
def _validate_references(rig: Rig):
    device_ids = set(rig.devices.keys())
    controller_id = rig.controller.id if rig.controller else None
    # Signal chain may include the controller position
    valid_chain_ids = device_ids | ({controller_id} if controller_id else set())

    known_presets: dict[str, set[str]] = {
        device_id: {p.id for p in device.presets} for device_id, device in rig.devices.items()
    }

    logger.debug("Validating signal chain references")
    for pos in rig.signal_chain:
        if pos.device_ref not in valid_chain_ids:
            logger.error("Signal chain references unknown device '%s'", pos.device_ref)
            raise MissingReferenceError(
                f"Signal chain references unknown device '{pos.device_ref}'"
            )

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

    # TODO: for example, this instance based thing shouldn't happen - these should all conform to a protocol
    logger.debug("Validating CBA preset parameter names against device controls")
    for device_id, device in rig.devices.items():
        if not isinstance(device.config, ChaseBlissConfig):
            continue
        control_names = {c.name for c in device.config.controls}
        for preset in device.presets:
            if not isinstance(preset, DigitalPreset):
                continue
            unknown = set(preset.parameters) - control_names
            if unknown:
                logger.error(
                    "Preset '%s' on '%s' has unknown parameters: %s",
                    preset.id,
                    device_id,
                    unknown,
                )
                raise ValidationError(
                    f"Preset '{preset.id}' on '{device_id}' has unknown parameters: {unknown}. "
                    f"Known controls: {sorted(control_names)}"
                )

    logger.debug("All cross-references valid")


def load_rig(root_path: str) -> Rig:
    root = Path(root_path).resolve()
    logger.info("Loading rig config from: %s", root)

    rig_data = _read_yaml(_resolve(root, "rig.yaml"))
    signal_data = _read_yaml(_resolve(root, "signal-chain.yaml"))

    # Support both new (devices/) and legacy (pedals/) directory names
    # TODO: Get rid of the pedal resolution
    devices_dir = _resolve(root, "devices")
    if not devices_dir.is_dir():
        devices_dir = _resolve(root, "pedals")
    scenes_dir = _resolve(root, "scenes")

    chain = [SignalChainPosition(**pos) for pos in signal_data.get("chain", [])]

    # Load MC6 bank config from controller.yaml (new) or mc6.yaml (legacy)
    # TODO: The entire rig should be resolved from a single file for now
    controller_path = _resolve(root, "controller.yaml")
    mc6_path = _resolve(root, "mc6.yaml")

    # TODO: The controller _may_ be an mc6 or something else. This should be a more flexible domain modeling solution
    if controller_path.exists():
        mc6_data = _read_yaml(controller_path) or {}
        # controller.yaml holds the full Controller definition
        controller: Controller | None = Controller(**mc6_data) if mc6_data else None
        devices, _ = _load_devices_dir(devices_dir, {})
    else:
        mc6_data = _read_yaml(mc6_path) if mc6_path.exists() else {}
        devices, controller = _load_devices_dir(devices_dir, mc6_data)

    devices = _merge_presets(devices_dir, devices)
    scenes = _load_scenes(scenes_dir)

    # TODO: I think an overarching theme here is I don't like the implied yaml structure that rig-cli enforces.
    # I want it more terraform-like

    rig = Rig(
        name=rig_data.get("name", ""),
        description=rig_data.get("description"),
        midi_channel=rig_data.get("midi_channel"),
        signal_chain=chain,
        devices=devices,
        controller=controller,
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
