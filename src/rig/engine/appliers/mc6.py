from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import ApplyContext, update_device_state
from rig.engine.state import DeviceState
from rig.interaction.midi import prompt_midi_connect
from rig.midi.mc6 import SWITCH_INDEX, clear_preset_messages, update_preset_name, update_preset_pc

logger = logging.getLogger(__name__)
console = Console()


class MC6Applier:
    def apply_banks(self, banks: list[dict], ctx: ApplyContext) -> None:
        """Program MC6 banks via SysEx."""
        if not banks or ctx.midi is None:
            return

        mc6_port = ctx.state.devices.get("mc6", DeviceState()).midi_port

        if ctx.dry_run:
            for bank in banks:
                for switch_label, switch_data in bank.get("switches", {}).items():
                    scene_name = switch_data.get("scene", "")
                    console.print(
                        f"  [cyan]→[/cyan] Bank {bank['bank']} / {switch_label}: "
                        f"'{scene_name}'[dim] (dry-run)[/dim]"
                    )
            return

        res, port_name = prompt_midi_connect("mc6", 1, ctx.midi, mc6_port)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return
        if res != "confirm" or not port_name:
            return

        update_device_state(ctx.state, "mc6", midi_port=port_name)

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
                        ctx.midi.send_sysex("mc6", msg)
                    ctx.midi.send_sysex("mc6", update_preset_name(preset_idx, scene_name))

                    scene_obj = ctx.rig.scenes.get(scene_name) if ctx.rig else None
                    if scene_obj:
                        msg_slot = 0
                        for pedal_id, preset_id in scene_obj.presets.items():
                            pedal = ctx.rig.pedals.get(pedal_id)
                            if pedal is None or pedal.config.midi_channel is None:
                                continue
                            pc = pedal.get_scene_pc_command(preset_id)
                            if pc:
                                ctx.midi.send_sysex(
                                    "mc6",
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
