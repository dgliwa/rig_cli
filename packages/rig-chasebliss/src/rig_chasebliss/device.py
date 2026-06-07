"""Chase Bliss Audio device implementation and setup helper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rig.engine.appliers.base import ApplyContext, DeviceApplyResult, update_device_state
from rig.engine.plugin import SetupContext, SetupResult
from rig.engine.state import DeviceState
from rig.models.device import ChaseBlissConfig
from rig.models.preset import DigitalPreset

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _detect_cba_setup_for_device(device: Any, state: Any, rig: Any) -> list[Any]:
    """Single-device version of detect_cba_setup from core plan/compute.py."""
    from rig.engine.plan.models import CbaSetupAction

    actions: list[CbaSetupAction] = []
    if not isinstance(device.config, ChaseBlissConfig):
        return actions

    ch = device.config.midi_channel or 1
    ds = state.devices.get(device.id, DeviceState())

    if not ds.channel_established:
        actions.append(CbaSetupAction(device=device.id, midi_channel=ch, type="establish_channel"))

    for preset in [p for p in device.presets if isinstance(p, DigitalPreset)]:
        if not ds.presets_saved.get(preset.id):
            actions.append(
                CbaSetupAction(
                    device=device.id,
                    midi_channel=ch,
                    type="build_preset",
                    preset_id=preset.id,
                    preset_name=preset.name,
                    preset_number=preset.preset_number,
                    cc_params=device.config.get_cc_params(preset.parameters),
                )
            )

    if not ds.registration_done:
        scene_refs = [sn for sn, s in rig.scenes.items() if device.id in s.presets]
        if scene_refs:
            actions.append(
                CbaSetupAction(
                    device=device.id,
                    midi_channel=ch,
                    type="register_scenes",
                    scene_refs=scene_refs,
                )
            )

    return actions


def cba_setup(device: Any, ctx: SetupContext) -> SetupResult:
    """Real setup() implementation for ChaseBlissDevice. Called via lazy import from core."""
    if not isinstance(device.config, ChaseBlissConfig):
        return SetupResult()

    ch = device.config.midi_channel or 1
    state_modified = False

    # Step 1: MIDI connection (only when a MidiManager is available)
    if not ctx.dry_run and ctx.midi is not None:
        cached_port = ctx.state.devices.get(device.id, DeviceState()).midi_port
        if ctx.midi_connection_io is not None:
            res, port_name = ctx.midi_connection_io.prompt_connect(
                device.id, ch, ctx.midi, cached_port
            )
        else:
            from rig.interaction.midi import prompt_midi_connect

            res, port_name = prompt_midi_connect(device.id, ch, ctx.midi, cached_port)

        if res == "quit":
            return SetupResult(cancelled=True)
        if res == "confirm" and port_name:
            update_device_state(ctx.state, device.id, midi_port=port_name)
            ctx.connected_devices.add(device.id)
            state_modified = True
    else:
        ctx.connected_devices.add(device.id)

    # Step 2: 3-phase CBA setup
    if ctx.rig is None:
        return SetupResult(state_modified=state_modified)

    actions = _detect_cba_setup_for_device(device, ctx.state, ctx.rig)
    if not actions:
        return SetupResult(state_modified=state_modified)

    from rig_chasebliss.applier import ChaseBlissApplier

    applier = ChaseBlissApplier()
    apply_ctx = ApplyContext(
        state=ctx.state,
        rig=ctx.rig,
        dry_run=ctx.dry_run,
        confirmation_io=ctx.confirmation_io,
        midi=ctx.midi,
        connected_devices=ctx.connected_devices,
        config_path=ctx.config_path,
    )
    results = applier.apply_setup(actions, apply_ctx)
    if results is None:
        return SetupResult(cancelled=True)
    if any(r.status == "confirmed" for r in results):
        state_modified = True

    return SetupResult(state_modified=state_modified)
