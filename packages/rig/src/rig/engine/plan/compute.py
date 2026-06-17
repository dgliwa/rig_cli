from __future__ import annotations

import logging
from typing import Literal

from rig.engine.plan.models import ActionStatus, DeviceAction, Plan, ScenePlan
from rig.engine.plugin import DeviceType
from rig.engine.state import DeviceState, RigState, read_state
from rig.models.graph import DeviceGraph
from rig.models.rig import Rig

logger = logging.getLogger(__name__)


def _get_preset_number(rig: Rig, pedal_id: str, preset_id: str) -> int | None:
    device = rig.devices.get(pedal_id)
    if device is None:
        return None
    for p in device.presets:
        if hasattr(p, "preset_number") and p.id == preset_id:
            return p.preset_number
    return None


def _detect_missing_refs(rig: Rig) -> list[str]:
    issues: list[str] = []
    for scene_name, scene in rig.scenes.items():
        for device_id, preset_id in scene.presets.items():
            if device_id not in rig.devices:
                issues.append(f"scene '{scene_name}' → device '{device_id}' not found")
            elif not any(p.id == preset_id for p in rig.devices[device_id].presets):
                issues.append(
                    f"scene '{scene_name}' → device '{device_id}' preset '{preset_id}' not found"
                )
    return sorted(issues)


def _detect_unused_presets(rig: Rig) -> list[str]:
    referenced: set[str] = {pid for scene in rig.scenes.values() for pid in scene.presets.values()}
    issues: list[str] = []
    for device in rig.devices.values():
        for preset in device.presets:
            # Analog presets are manually set — skip unused-preset detection
            if hasattr(preset, "values"):
                continue
            if preset.id not in referenced:
                issues.append(f"{device.id}: '{preset.id}' unused")
    return sorted(issues)


def compute_plan(rig: Rig, root_path: str | None = None) -> Plan:
    logger.debug("Computing plan for %d scenes", len(rig.scenes))
    actual = RigState()
    if root_path:
        actual = read_state(root_path)
        logger.debug("Read state for %d devices", len(actual.devices))

    scenes_plan: dict[str, ScenePlan] = {}
    any_changes = False

    graph = DeviceGraph(rig)
    ordered_devices = [d.id for d in graph.apply_order()]

    # TODO: not a fan of defining functions INSIDE functions
    def _action_sort_key(action: DeviceAction) -> int:
        try:
            return ordered_devices.index(action.device)
        except ValueError:
            return len(ordered_devices)

    for scene_name, scene in rig.scenes.items():
        logger.debug("Planning scene '%s' with %d pedal(s)", scene_name, len(scene.presets))
        device_actions: list[DeviceAction] = []
        scene_has_changes = False

        for pedal_id, preset_id in scene.presets.items():
            pedal = rig.devices.get(pedal_id)
            if pedal is None:
                logger.warning(
                    "Pedal '%s' referenced in scene '%s' not found", pedal_id, scene_name
                )
                continue

            actual_preset = actual.devices.get(pedal_id, DeviceState()).last_preset
            logger.debug(
                "  Device '%s': actual='%s' desired='%s'", pedal_id, actual_preset, preset_id
            )

            if pedal.type == DeviceType.ANALOG:
                device_actions.append(
                    DeviceAction(
                        device=pedal_id,
                        device_type=DeviceType.ANALOG,
                        status=ActionStatus.ANALOG,
                        preset_name=preset_id,
                        before=actual_preset,
                        after=preset_id,
                    )
                )
                if actual_preset != preset_id:
                    scene_has_changes = True
                    logger.debug("    → analog needs manual adjustment")
                continue

            preset_number = _get_preset_number(rig, pedal_id, preset_id)
            logger.debug("    → preset #%s", preset_number)

            needs_config = actual_preset != preset_id
            if needs_config:
                scene_has_changes = True
                logger.debug("    → needs configure")
            else:
                logger.debug("    → already correct")

            device_actions.append(
                DeviceAction(
                    device=pedal_id,
                    device_type=pedal.type,
                    status=ActionStatus.CONFIGURE if needs_config else ActionStatus.VERIFY,
                    preset_name=preset_id,
                    preset_number=preset_number,
                    midi_channel=getattr(pedal.config, "midi_channel", None),
                    before=actual_preset,
                    after=preset_id,
                )
            )

        device_actions.sort(key=_action_sort_key)

        scene_status: Literal["new", "changed", "unchanged"] = (
            "new"
            if scene_name not in actual.scenes
            else "changed"
            if scene_has_changes
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

    missing_refs = _detect_missing_refs(rig)
    unused_presets = _detect_unused_presets(rig)

    plan_status = "changes_detected" if any_changes else "clean"
    logger.info(
        "Plan computed: %s (%d scene(s) with changes)",
        plan_status,
        sum(1 for s in scenes_plan.values() if s.status != "unchanged"),
    )
    return Plan(
        status=plan_status,
        scenes=scenes_plan,
        missing_refs=missing_refs,
        unused_presets=unused_presets,
    )
