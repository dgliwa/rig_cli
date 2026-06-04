from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import ApplyContext, DeviceApplyResult, update_device_state
from rig.engine.plan import DeviceAction
from rig.interaction.midi import prompt_device

logger = logging.getLogger(__name__)
console = Console()


class MidiApplier:
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext) -> DeviceApplyResult:
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
            result = prompt_device(
                action.device,
                action.preset_name,
                action.preset_number,
                action.midi_channel,
                midi_connected=midi_connected,
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
            # quit
            return DeviceApplyResult(
                device=action.device,
                status="error",
                preset=action.preset_name,
                error="quit",
            )
