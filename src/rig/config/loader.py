import logging
from pathlib import Path

import yaml

from rig.models.pedal import PedalDefinition
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.models.rig import RigConfig
from rig.config.errors import FileNotFoundError_, ParseError, MissingReferenceError


logger = logging.getLogger(__name__)


def _resolve(root: Path, *parts: str) -> Path:
    result = root.joinpath(*parts).resolve()
    logger.debug("Resolved path: %s", result)
    return result


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


def _load_pedal_definitions(pedals_dir: Path) -> dict[str, PedalDefinition]:
    definitions: dict[str, PedalDefinition] = {}
    logger.debug("Loading pedal definitions from: %s", pedals_dir)
    for path in sorted(pedals_dir.glob("*.yaml")):
        data = _read_yaml(path)
        pedal = PedalDefinition(**data)
        definitions[pedal.id] = pedal
        logger.debug("Loaded pedal '%s' (%s %s)", pedal.id, pedal.manufacturer, pedal.model)
    logger.info("Loaded %d pedals", len(definitions))
    return definitions


def _load_presets(
    pedals_dir: Path, definitions: dict[str, PedalDefinition]
) -> tuple[dict[str, list[DigitalPreset]], dict[str, list[AnalogPreset]], dict[str, list[HXStompPreset]]]:
    digital: dict[str, list[DigitalPreset]] = {}
    analog: dict[str, list[AnalogPreset]] = {}
    hx: dict[str, list[HXStompPreset]] = {}

    for pedal_id in definitions:
        preset_dir = pedals_dir / pedal_id / "presets"
        if not preset_dir.is_dir():
            logger.debug("No presets directory for pedal '%s' at %s", pedal_id, preset_dir)
            continue
        logger.debug("Loading presets for pedal '%s' from: %s", pedal_id, preset_dir)
        count = 0
        for path in sorted(preset_dir.glob("*.yaml")):
            data = _read_yaml(path)
            pedal_type = definitions[pedal_id].type.value
            if pedal_type == "analog":
                p = AnalogPreset(**data)
                analog.setdefault(pedal_id, []).append(p)
            elif pedal_type == "modeler":
                p = HXStompPreset(**data)
                hx.setdefault(pedal_id, []).append(p)
            else:
                p = DigitalPreset(**data)
                digital.setdefault(pedal_id, []).append(p)
            count += 1
        logger.debug("Loaded %d presets for '%s'", count, pedal_id)
    base = sum(len(v) for v in digital.values())
    num_analog = sum(len(v) for v in analog.values())
    num_hx = sum(len(v) for v in hx.values())
    logger.info("Loaded %d digital, %d analog, %d HX presets", base, num_analog, num_hx)
    return digital, analog, hx


def _load_scenes(scenes_dir: Path) -> dict[str, Scene]:
    scenes: dict[str, Scene] = {}
    logger.debug("Loading scenes from: %s", scenes_dir)
    for path in sorted(scenes_dir.glob("*.yaml")):
        data = _read_yaml(path)
        scene = Scene(**data)
        scenes[scene.name] = scene
        logger.debug("Loaded scene '%s' with %d pedal(s)", scene.name, len(scene.presets))
    logger.info("Loaded %d scenes", len(scenes))
    return scenes


def _validate_references(
    config: RigConfig,
    pedal_ids: set[str],
    digital_presets: dict[str, list[DigitalPreset]],
    analog_presets: dict[str, list[AnalogPreset]],
    hx_presets: dict[str, list[HXStompPreset]],
):
    known_presets: dict[str, set[str]] = {}
    logger.debug("Building known preset index for %d pedals", len(pedal_ids))
    for pid in pedal_ids:
        known_presets[pid] = set()
        for p in digital_presets.get(pid, []):
            known_presets[pid].add(p.id)
        for p in analog_presets.get(pid, []):
            known_presets[pid].add(p.id)
        for p in hx_presets.get(pid, []):
            known_presets[pid].add(p.id)

    logger.debug("Validating signal chain references")
    for pos in config.signal_chain:
        if pos.pedal_ref not in pedal_ids:
            logger.error("Signal chain references unknown pedal '%s'", pos.pedal_ref)
            raise MissingReferenceError(
                f"Signal chain references unknown pedal '{pos.pedal_ref}'"
            )

    logger.debug("Validating scene preset references")
    for scene_name, scene in config.scenes.items():
        for pedal_id, preset_id in scene.presets.items():
            if pedal_id not in pedal_ids:
                logger.error("Scene '%s' references unknown pedal '%s'", scene_name, pedal_id)
                raise MissingReferenceError(
                    f"Scene '{scene_name}' references unknown pedal '{pedal_id}'"
                )
            if preset_id not in known_presets.get(pedal_id, set()):
                logger.error("Scene '%s': pedal '%s' has no preset '%s'", scene_name, pedal_id, preset_id)
                raise MissingReferenceError(
                    f"Scene '{scene_name}': pedal '{pedal_id}' has no preset '{preset_id}'"
                )
    logger.debug("All cross-references valid")


def load_rig(root_path: str) -> RigConfig:
    root = Path(root_path).resolve()
    logger.info("Loading rig config from: %s", root)

    rig_data = _read_yaml(_resolve(root, "rig.yaml"))
    signal_data = _read_yaml(_resolve(root, "signal-chain.yaml"))
    pedals_dir = _resolve(root, "pedals")
    scenes_dir = _resolve(root, "scenes")

    chain = [SignalChainPosition(**pos) for pos in signal_data.get("chain", [])]
    pedal_defs = _load_pedal_definitions(pedals_dir)
    digital, analog, hx = _load_presets(pedals_dir, pedal_defs)
    scenes = _load_scenes(scenes_dir)

    mc6_path = _resolve(root, "mc6.yaml")
    if mc6_path.exists():
        with open(mc6_path) as f:
            mc6_data = yaml.safe_load(f) or {}
    else:
        mc6_data = {}

    config = RigConfig(
        name=rig_data.get("name", ""),
        description=rig_data.get("description"),
        midi_channel=rig_data.get("midi_channel"),
        signal_chain=chain,
        pedals=pedal_defs,
        digital_presets=digital,
        analog_presets=analog,
        hx_presets=hx,
        scenes=scenes,
        mc6=mc6_data,
    )

    _validate_references(config, set(pedal_defs.keys()), digital, analog, hx)
    logger.info("Rig '%s' loaded successfully (%d pedals, %d scenes)",
                config.name, len(config.pedals), len(config.scenes))
    return config
