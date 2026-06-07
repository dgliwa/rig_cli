"""Chase Bliss Audio device implementation.

ChaseBlissDevice is a Pydantic BaseModel that implements the Device Protocol.
setup() handles MIDI port connection and the 3-phase CBA initialization
(establish_channel → build_preset → register_scenes). apply() sends PC messages
for scene switching (same as HXStompDevice/analog PC send behavior).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from rig.engine.appliers.base import (
    ApplyContext,
    DeviceApplyResult,
    update_device_state,
)
from rig.engine.plugin import DeviceApplyContext, PluginContext, SetupContext, SetupResult
from rig.engine.state import DeviceState
from rig.models.device import ChaseBlissConfig, DeviceType
from rig.models.preset import DigitalPreset, HXStompPreset

logger = logging.getLogger(__name__)
console = Console()


def _detect_cba_setup_for_device(device: Any, state: Any, rig: Any) -> list[Any]:
    """Detect which CBA setup actions are needed for this device.

    Checks state for channel establishment, saved presets, and scene registration.
    """
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


class ChaseBlissDevice(BaseModel):
    """Chase Bliss Audio pedal — PC-message-based with 3-phase MIDI setup.

    setup() handles MIDI port connection and runs the 3-phase initialization
    (establish MIDI channel, build presets via CC params, register scenes).
    apply() sends PC messages for scene switching, same as HXStompDevice.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    id: str
    name: str = ""
    config: Any
    type: DeviceType = DeviceType.DIGITAL
    presets: list[Any] = Field(default_factory=list)

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def setup(self, ctx: SetupContext) -> SetupResult:
        """Connect MIDI and run 3-phase CBA setup.

        1. Prompt user for MIDI port selection
        2. Detect required setup actions (channel, presets, registration)
        3. Execute actions via ChaseBlissApplier
        """
        if not isinstance(self.config, ChaseBlissConfig):
            return SetupResult()

        ch = self.config.midi_channel or 1
        state_modified = False

        # Step 1: MIDI connection
        if not ctx.dry_run and ctx.midi is not None:
            from rig.interaction.midi import prompt_midi_connect

            cached_port = ctx.state.devices.get(self.id, DeviceState()).midi_port
            res, port_name = prompt_midi_connect(self.id, ch, ctx.midi, cached_port)

            if res == "quit":
                return SetupResult(cancelled=True)
            if res == "confirm" and port_name:
                update_device_state(ctx.state, self.id, midi_port=port_name)
                ctx.connected_devices.add(self.id)
                state_modified = True
        else:
            ctx.connected_devices.add(self.id)

        # Step 2: 3-phase CBA setup
        if ctx.rig is None:
            return SetupResult(state_modified=state_modified)

        actions = _detect_cba_setup_for_device(self, ctx.state, ctx.rig)
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

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        """Return a PC command dict for the given preset_id, or None."""
        ch = self.config.midi_channel if self.config is not None else None
        if ch is None:
            return None
        for preset in self.presets:
            if (
                preset.id == preset_id
                and isinstance(preset, (DigitalPreset, HXStompPreset))
                and preset.preset_number is not None
            ):
                return {
                    "type": "pc",
                    "channel": ch,
                    "value": preset.preset_number,
                    "label": f"{self.id}: {preset_id}",
                }
        return None

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        """Send PC message and prompt user for confirmation.

        CBA scene switching is just a PC message — same behavior as HXStompDevice.
        """
        action = ctx.action
        midi_connected = action.device in ctx.connected_devices

        if ctx.dry_run:
            logger.debug(
                "Dry-run: would send PC#%s on ch %s to %s",
                action.preset_number,
                action.midi_channel,
                action.device,
            )
            console.print(
                f"  [dim]→ PC#{action.preset_number} ch {action.midi_channel} "
                f"→ {action.device} '{action.preset_name}'[/dim]"
            )
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

        def _try_send_pc() -> bool:
            if (
                midi_connected
                and action.preset_number is not None
                and action.midi_channel is not None
                and ctx.midi is not None
            ):
                try:
                    ctx.midi.send_program_change(
                        action.device, action.preset_number, action.midi_channel
                    )
                    return True
                except Exception as e:
                    logger.error("Failed PC send to %s: %s", action.device, e)
            return False

        _try_send_pc()

        while True:
            result = ctx.confirmation_io.prompt_device(
                action.device,
                action.preset_name,
                action.preset_number,
                action.midi_channel,
                midi_connected,
            )
            if result == "confirm":
                update_device_state(ctx.state, action.device, last_preset=action.preset_name)
                return DeviceApplyResult(
                    device=action.device,
                    status="confirmed",
                    preset=action.preset_name,
                )
            if result == "retry":
                _try_send_pc()
                continue
            if result == "skip":
                return DeviceApplyResult(
                    device=action.device,
                    status="skipped",
                    preset=action.preset_name,
                )
            return DeviceApplyResult(
                device=action.device,
                status="error",
                preset=action.preset_name,
                error="quit",
            )
