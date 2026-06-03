from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import ApplyContext, DeviceApplyResult, update_device_state
from rig.engine.plan import DeviceAction
from rig.interaction import prompt_analog

logger = logging.getLogger(__name__)
console = Console()


class AnalogApplier:
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext) -> DeviceApplyResult:
        if ctx.dry_run:
            logger.debug(
                "Dry-run: would prompt analog '%s' → '%s'",
                action.device,
                action.preset_name,
            )
            console.print(
                f"  [yellow]⚠[/yellow] {action.device}: would prompt to set '{action.preset_name}'"
            )
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

        res = prompt_analog(action.device, action.preset_name)
        if res == "quit":
            return DeviceApplyResult(
                device=action.device, status="error", preset=action.preset_name, error="quit"
            )
        if res == "confirm":
            update_device_state(ctx.state, action.device, last_preset=action.preset_name)
            return DeviceApplyResult(
                device=action.device, status="confirmed", preset=action.preset_name
            )
        # skip
        return DeviceApplyResult(device=action.device, status="skipped", preset=action.preset_name)
