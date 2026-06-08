from __future__ import annotations

import logging
from typing import Literal

from rig.engine.plan.models import CbaSetupAction, DeviceAction, Plan, ScenePlan
from rig.engine.state import DeviceState, RigState, read_state
from rig.models.graph import DeviceGraph
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.rig import Rig

logger = logging.getLogger(__name__)


def _get_preset_number(rig: Rig, pedal_id: str, preset_id: str) -> int | None:
    device = rig.devices.get(pedal_id)
    if device is None:
        return None
    for p in device.presets:
        if isinstance(p, DigitalPreset) and p.id == preset_id:
            return p.preset_number
    return None


def detect_cba_setup(rig: Rig, state: RigState) -> list[CbaSetupAction]:
    """Detect CBA setup actions needed based on current state."""
    actions: list[CbaSetupAction] = []

    from rig.models.device import ChaseBlissConfig

    for pedal_id, pedal in rig.devices.items():
        if not isinstance(pedal.config, ChaseBlissConfig):
            continue

        ch = pedal.config.midi_channel or 1
        ds = state.devices.get(pedal_id, DeviceState())

        # Phase 1: Channel establishment
        if not ds.channel_established:
            actions.append(
                CbaSetupAction(
                    device=pedal_id,
                    midi_channel=ch,
                    type="establish_channel",
                )
            )
        # Phase 2: Preset building
        presets_saved = ds.presets_saved
        for preset in [p for p in pedal.presets if isinstance(p, DigitalPreset)]:
            if not presets_saved.get(preset.id):
                actions.append(
                    CbaSetupAction(
                        device=pedal_id,
                        midi_channel=ch,
                        type="build_preset",
                        preset_id=preset.id,
                        preset_name=preset.name,
                        preset_number=preset.preset_number,
                        cc_params=pedal.config.get_cc_params(preset.parameters),
                    )
                )

        # Phase 3: Scene registration (only if channel + presets done, but not yet registered)
        if not ds.registration_done:
            scene_refs = [sn for sn, s in rig.scenes.items() if pedal_id in s.presets]
            if scene_refs:
                actions.append(
                    CbaSetupAction(
                        device=pedal_id,
                        midi_channel=ch,
                        type="register_scenes",
                        scene_refs=scene_refs,
                    )
                )

    return actions


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
            # TODO: 1.2?? i don't want to have this here.
            if isinstance(preset, AnalogPreset):
                continue
            if preset.id not in referenced:
                issues.append(f"{device.id}: '{preset.id}' unused")
    return sorted(issues)


# TODO: 1.2 issue #13 - the device should be in charge of generating its device action
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

            if pedal.type.value == "analog":
                device_actions.append(
                    DeviceAction(
                        device=pedal_id,
                        device_type="analog",
                        status="analog",
                        preset_name=preset_id,
                        before=actual_preset,
                        after=preset_id,
                    )
                )
                if actual_preset != preset_id:
                    scene_has_changes = True
                    logger.debug("    → analog needs manual adjustment")
                continue

            is_hx = pedal.type.value == "modeler"
            preset_number = None

            if is_hx:
                for hp in [p for p in pedal.presets if isinstance(p, HXStompPreset)]:
                    if hp.id == preset_id:
                        preset_number = hp.preset_number
                        break
                logger.debug("    → HX preset #%s", preset_number)
            else:
                preset_number = _get_preset_number(rig, pedal_id, preset_id)
                logger.debug("    → digital preset #%s", preset_number)

            needs_config = actual_preset != preset_id
            if needs_config:
                scene_has_changes = True
                logger.debug("    → needs configure")
            else:
                logger.debug("    → already correct")

            device_actions.append(
                DeviceAction(
                    device=pedal_id,
                    device_type=pedal.type.value,
                    status="configure" if needs_config else "verify",
                    preset_name=preset_id,
                    preset_number=preset_number,
                    midi_channel=pedal.config.midi_channel,
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

    # TODO: 1.2 this is an example of something that should be in the cb plugin
    cba_setup = detect_cba_setup(rig, actual)
    if cba_setup:
        any_changes = True
        logger.debug("CBA setup actions: %d", len(cba_setup))

    plan_status = "changes_detected" if any_changes else "clean"
    logger.info(
        "Plan computed: %s (%d scene(s) with changes, %d CBA action(s))",
        plan_status,
        sum(1 for s in scenes_plan.values() if s.status != "unchanged"),
        len(cba_setup),
    )
    return Plan(
        status=plan_status,
        scenes=scenes_plan,
        cba_setup=cba_setup,
        missing_refs=missing_refs,
        unused_presets=unused_presets,
    )
