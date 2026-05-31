import logging
from typing import Any, Literal

from pydantic import BaseModel

from rig.models.rig import RigConfig
from rig.models.preset import HXBlock
from rig.engine.state import read_state


logger = logging.getLogger(__name__)


class BlockDiff(BaseModel):
    name: str
    status: Literal["added", "removed", "changed", "unchanged"]
    detail: str = ""


class DeviceAction(BaseModel):
    device: str
    device_type: str
    status: Literal["configure", "verify", "analog", "no_change"]
    preset_name: str = ""
    preset_number: int | None = None
    midi_channel: int | None = None
    instructions: list[str] = []
    block_diffs: list[BlockDiff] = []


class ScenePlan(BaseModel):
    scene_name: str
    status: Literal["new", "changed", "unchanged"]
    device_actions: list[DeviceAction] = []


class Plan(BaseModel):
    status: Literal["clean", "changes_detected"]
    scenes: dict[str, ScenePlan] = {}


def _hx_preset_number(rig: RigConfig, hx_preset_id: str) -> int | None:
    for presets in rig.hx_presets.values():
        for p in presets:
            if p.id == hx_preset_id:
                return p.preset_number
    return None


def _get_preset_number(rig: RigConfig, pedal_id: str, preset_id: str) -> int | None:
    for presets in rig.digital_presets.get(pedal_id, []):
        if presets.id == preset_id:
            return presets.preset_number
    return None


def _diff_blocks(desired_blocks: list[HXBlock], actual_preset_state: dict) -> list[BlockDiff]:
    diffs: list[BlockDiff] = []
    actual_names = set(actual_preset_state.get("block_names", []))
    desired_names = {b.name for b in desired_blocks}

    for block in desired_blocks:
        if block.name not in actual_names:
            diffs.append(BlockDiff(name=block.name, status="added"))
        else:
            diffs.append(BlockDiff(name=block.name, status="unchanged"))

    for name in actual_names:
        if name not in desired_names:
            diffs.append(BlockDiff(name=name, status="removed"))

    return diffs


def compute_plan(rig: RigConfig, root_path: str | None = None) -> Plan:
    logger.debug("Computing plan for %d scenes", len(rig.scenes))
    actual = {}
    if root_path:
        actual = read_state(root_path)
        logger.debug("Read state for %d devices", len(actual.get("devices", {})))

    scenes_plan: dict[str, ScenePlan] = {}
    any_changes = False

    for scene_name, scene in rig.scenes.items():
        logger.debug("Planning scene '%s' with %d pedal(s)", scene_name, len(scene.presets))
        device_actions: list[DeviceAction] = []
        scene_has_changes = False

        for pedal_id, preset_id in scene.presets.items():
            pedal = rig.pedals.get(pedal_id)
            if pedal is None:
                logger.warning("Pedal '%s' referenced in scene '%s' not found", pedal_id, scene_name)
                continue

            actual_preset = actual.get("devices", {}).get(pedal_id, {}).get("last_preset")
            logger.debug("  Device '%s': actual='%s' desired='%s'", pedal_id, actual_preset, preset_id)

            if pedal.type.value == "analog":
                device_actions.append(DeviceAction(
                    device=pedal_id,
                    device_type="analog",
                    status="analog",
                    preset_name=preset_id,
                ))
                if actual_preset != preset_id:
                    scene_has_changes = True
                    logger.debug("    → analog needs manual adjustment")
                continue

            is_hx = pedal.type.value == "modeler"
            preset_number = None
            block_diffs: list[BlockDiff] = []

            if is_hx:
                for hp in rig.hx_presets.get(pedal_id, []):
                    if hp.id == preset_id:
                        preset_number = hp.preset_number
                        block_diffs = _diff_blocks(hp.blocks, actual.get("devices", {}).get(pedal_id, {}))
                        break
                logger.debug("    → HX preset #%s with %d block diff(s)", preset_number, len(block_diffs))
            else:
                preset_number = _get_preset_number(rig, pedal_id, preset_id)
                logger.debug("    → digital preset #%s", preset_number)

            needs_config = actual_preset != preset_id
            if needs_config:
                scene_has_changes = True
                logger.debug("    → needs configure")
            else:
                logger.debug("    → already correct")

            device_actions.append(DeviceAction(
                device=pedal_id,
                device_type=pedal.type.value,
                status="configure" if needs_config else "verify",
                preset_name=preset_id,
                preset_number=preset_number,
                midi_channel=pedal.midi_channel,
                block_diffs=block_diffs,
            ))

        scene_status: Literal["new", "changed", "unchanged"] = (
            "new" if scene_name not in actual.get("scenes", {})
            else "changed" if scene_has_changes
            else "unchanged"
        )
        logger.debug("  Scene status: %s", scene_status)
        if scene_status != "unchanged":
            any_changes = True

        scenes_plan[scene_name] = ScenePlan(
            scene_name=scene_name,
            status=scene_status,
            device_actions=device_actions,
        )

    plan_status = "changes_detected" if any_changes else "clean"
    logger.info("Plan computed: %s (%d scene(s) with changes)", plan_status, sum(1 for s in scenes_plan.values() if s.status != "unchanged"))
    return Plan(
        status=plan_status,
        scenes=scenes_plan,
    )
