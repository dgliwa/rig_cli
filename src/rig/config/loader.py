from pathlib import Path
import yaml

from rig.models.pedal import PedalDefinition
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.models.rig import RigConfig
from rig.config.errors import FileNotFoundError_, ParseError, MissingReferenceError


def _resolve(root: Path, *parts: str) -> Path:
    return root.joinpath(*parts).resolve()


def _read_yaml(path: Path):
    if not path.exists():
        raise FileNotFoundError_(f"Missing file: {path}")
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ParseError(f"Invalid YAML in {path}: {e}")


def _load_pedal_definitions(pedals_dir: Path) -> dict[str, PedalDefinition]:
    definitions: dict[str, PedalDefinition] = {}
    for path in sorted(pedals_dir.glob("*.yaml")):
        data = _read_yaml(path)
        pedal = PedalDefinition(**data)
        definitions[pedal.id] = pedal
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
            continue
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
    return digital, analog, hx


def _load_scenes(scenes_dir: Path) -> dict[str, Scene]:
    scenes: dict[str, Scene] = {}
    for path in sorted(scenes_dir.glob("*.yaml")):
        data = _read_yaml(path)
        scene = Scene(**data)
        scenes[scene.name] = scene
    return scenes


def _validate_references(
    config: RigConfig,
    pedal_ids: set[str],
    digital_presets: dict[str, list[DigitalPreset]],
    analog_presets: dict[str, list[AnalogPreset]],
    hx_presets: dict[str, list[HXStompPreset]],
):
    known_presets: dict[str, set[str]] = {}
    for pid in pedal_ids:
        known_presets[pid] = set()
        for p in digital_presets.get(pid, []):
            known_presets[pid].add(p.id)
        for p in analog_presets.get(pid, []):
            known_presets[pid].add(p.id)
        for p in hx_presets.get(pid, []):
            known_presets[pid].add(p.id)

    for pos in config.signal_chain:
        if pos.pedal_ref not in pedal_ids:
            raise MissingReferenceError(
                f"Signal chain references unknown pedal '{pos.pedal_ref}'"
            )

    for scene_name, scene in config.scenes.items():
        for pedal_id, preset_id in scene.presets.items():
            if pedal_id not in pedal_ids:
                raise MissingReferenceError(
                    f"Scene '{scene_name}' references unknown pedal '{pedal_id}'"
                )
            if preset_id not in known_presets.get(pedal_id, set()):
                raise MissingReferenceError(
                    f"Scene '{scene_name}': pedal '{pedal_id}' has no preset '{preset_id}'"
                )


def load_rig(root_path: str) -> RigConfig:
    root = Path(root_path).resolve()

    rig_data = _read_yaml(_resolve(root, "rig.yaml"))
    signal_data = _read_yaml(_resolve(root, "signal-chain.yaml"))
    pedals_dir = _resolve(root, "pedals")
    scenes_dir = _resolve(root, "scenes")

    chain = [SignalChainPosition(**pos) for pos in signal_data.get("chain", [])]
    pedal_defs = _load_pedal_definitions(pedals_dir)
    digital, analog, hx = _load_presets(pedals_dir, pedal_defs)
    scenes = _load_scenes(scenes_dir)

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
    )

    _validate_references(config, set(pedal_defs.keys()), digital, analog, hx)
    return config
