from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from rig.engine.appliers.base import DeviceApplyResult, update_device_state
from rig.engine.plugin import DeviceApplyContext, PluginContext, SetupContext, SetupResult
from rig.engine.state import DeviceState
from rig.models.device import DeviceType

logger = logging.getLogger(__name__)
console = Console()


class MC6Device(BaseModel):
    """Morningstar MC6 MIDI controller device."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    id: str
    name: str = ""
    config: Any
    type: DeviceType = DeviceType.CONTROLLER
    presets: list[Any] = Field(default_factory=list)

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def setup(self, ctx: SetupContext) -> SetupResult:
        """Connect MIDI to MC6 before the apply phase uses it."""
        if ctx.dry_run:
            ctx.connected_devices.add(self.id)
            return SetupResult()

        from rig.interaction.midi import prompt_midi_connect

        mc6_port = ctx.state.devices.get(self.id, DeviceState()).midi_port
        res, port_name = prompt_midi_connect(self.id, 1, ctx.midi, mc6_port)
        if res == "quit":
            return SetupResult(cancelled=True)
        if res == "confirm" and port_name:
            update_device_state(ctx.state, self.id, midi_port=port_name)
            ctx.connected_devices.add(self.id)
            return SetupResult(state_modified=True)
        return SetupResult()

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        """MC6 is a controller — it programs other devices, not a target itself."""
        return None

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        from rig_morningstar.sysex import (
            SWITCH_INDEX,
            clear_preset_messages,
            update_preset_name,
            update_preset_pc,
        )

        device_id = ctx.action.device

        banks = (
            self.config.get("banks", [])
            if isinstance(self.config, dict)
            else getattr(self.config, "banks", [])
        )
        if not banks or ctx.midi is None:
            return DeviceApplyResult(device=device_id, status="skipped")

        if ctx.dry_run:
            for bank in banks:
                for switch_label, switch_data in bank.get("switches", {}).items():
                    scene_name = switch_data.get("scene", "")
                    console.print(
                        f"  [cyan]→[/cyan] Bank {bank['bank']} / {switch_label}: "
                        f"'{scene_name}'[dim] (dry-run)[/dim]"
                    )
            return DeviceApplyResult(device=device_id, status="skipped")

        if device_id not in ctx.connected_devices:
            return DeviceApplyResult(device=device_id, status="skipped")

        for bank in banks:
            bank_num = bank["bank"]
            ctx.confirmation_io.prompt_mc6_navigate(bank_num)

            for switch_label, switch_data in bank.get("switches", {}).items():
                scene_name = switch_data.get("scene", "")
                preset_idx = SWITCH_INDEX.get(switch_label)
                if preset_idx is None:
                    logger.warning("Unknown MC6 switch label '%s'", switch_label)
                    continue

                try:
                    for msg in clear_preset_messages(preset_idx):
                        ctx.midi.send_sysex(self.id, msg)
                    ctx.midi.send_sysex(self.id, update_preset_name(preset_idx, scene_name))

                    rig = ctx.rig
                    scene_obj = (
                        rig.scenes.get(scene_name) if rig and hasattr(rig, "scenes") else None
                    )
                    if scene_obj:
                        msg_slot = 0
                        for pedal_id, preset_id in scene_obj.presets.items():
                            pedal = rig.devices.get(pedal_id)
                            if pedal is None or pedal.config.midi_channel is None:
                                continue
                            pc = pedal.get_scene_pc_command(preset_id)
                            if pc:
                                ctx.midi.send_sysex(
                                    self.id,
                                    update_preset_pc(
                                        preset_idx,
                                        msg_slot,
                                        pc["value"],
                                        pc["channel"],
                                    ),
                                )
                                msg_slot += 1

                    console.print(
                        f"  [green]✓[/green] Switch {switch_label}: '{scene_name}' programmed"
                    )
                except Exception as e:
                    logger.error("MC6 SysEx failed for switch %s: %s", switch_label, e)
                    console.print(f"  [red]✗[/red] Switch {switch_label}: {e}")

        return DeviceApplyResult(device=device_id, status="confirmed")
