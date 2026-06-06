"""Concrete Device plugin types for the rig plugin architecture.

Phase 4 P2: AnalogDevice, MidiDevice, ChaseBlissDevice, and MC6Device implement
the Device Protocol as Pydantic BaseModel subclasses.  Each type carries its own
id/name/config and delegates apply() to the logic previously in the applier classes.

plan() and diff() raise NotImplementedError — Phase 5 fills these in.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict
from rich.console import Console

from rig.engine.appliers.base import DeviceApplyResult, update_device_state
from rig.engine.plugin import DeviceApplyContext, PluginContext
from rig.engine.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# AnalogDevice
# ---------------------------------------------------------------------------


class AnalogDevice(BaseModel):
    """Manual (analog) device — knobs and switches set by hand.

    apply() replicates AnalogApplier.apply_scene logic; plan/diff deferred to Phase 5.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    config: Any

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        action = ctx.action

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

        res = ctx.confirmation_io.prompt_analog(action.device, action.preset_name)
        if res == "quit":
            return DeviceApplyResult(
                device=action.device, status="error", preset=action.preset_name, error="quit"
            )
        if res == "confirm":
            update_device_state(ctx.state, action.device, last_preset=action.preset_name)
            return DeviceApplyResult(
                device=action.device, status="confirmed", preset=action.preset_name
            )
        return DeviceApplyResult(device=action.device, status="skipped", preset=action.preset_name)


# ---------------------------------------------------------------------------
# MidiDevice
# ---------------------------------------------------------------------------


class MidiDevice(BaseModel):
    """MIDI-controlled device — sends PC messages.

    apply() replicates MidiApplier.apply_scene logic; plan/diff deferred to Phase 5.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    config: Any

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
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


# ---------------------------------------------------------------------------
# ChaseBlissDevice
# ---------------------------------------------------------------------------


class ChaseBlissDevice(BaseModel):
    """Chase Bliss Audio device — scene apply is a plain PC message (delegates to MidiDevice logic).

    3-phase CBA setup (establish_channel / build_preset / register_scenes) remains in
    ChaseBlissApplier for now; Phase 4 only migrates scene-level apply.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    config: Any

    # Shared MidiDevice apply logic — CBA scene switching is just a PC message.
    _midi_device: MidiDevice = MidiDevice(id="", name="", config=None)

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        return self._midi_device.apply(ctx)


# ---------------------------------------------------------------------------
# MC6Device
# ---------------------------------------------------------------------------


class MC6Device(BaseModel):
    """Morningstar MC6 MIDI controller device.

    apply() replicates MC6Applier.apply_banks logic inline; plan/diff deferred to Phase 5.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    config: Any
    banks: list[dict] = []

    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        from rig.engine.state import DeviceState
        from rig.midi.mc6 import (  # noqa: PLC0415
            SWITCH_INDEX,
            clear_preset_messages,
            update_preset_name,
            update_preset_pc,
        )

        device_id = ctx.action.device

        if not self.banks or ctx.midi is None:
            return DeviceApplyResult(device=device_id, status="skipped")

        mc6_port = ctx.state.devices.get("mc6", DeviceState()).midi_port

        if ctx.dry_run:
            for bank in self.banks:
                for switch_label, switch_data in bank.get("switches", {}).items():
                    scene_name = switch_data.get("scene", "")
                    console.print(
                        f"  [cyan]→[/cyan] Bank {bank['bank']} / {switch_label}: "
                        f"'{scene_name}'[dim] (dry-run)[/dim]"
                    )
            return DeviceApplyResult(device=device_id, status="skipped")

        from rig.interaction.midi import prompt_midi_connect

        res, port_name = prompt_midi_connect("mc6", 1, ctx.midi, mc6_port)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return DeviceApplyResult(device=device_id, status="error", error="quit")
        if res != "confirm" or not port_name:
            return DeviceApplyResult(device=device_id, status="skipped")

        update_device_state(ctx.state, "mc6", midi_port=port_name)

        for bank in self.banks:
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

                    rig = ctx.rig
                    scene_obj = (
                        rig.scenes.get(scene_name) if rig and hasattr(rig, "scenes") else None
                    )
                    if scene_obj:
                        msg_slot = 0
                        for pedal_id, preset_id in scene_obj.presets.items():
                            pedal = rig.pedals.get(pedal_id)
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

        return DeviceApplyResult(device=device_id, status="confirmed")


# ---------------------------------------------------------------------------
# Default PluginRegistry instance
# ---------------------------------------------------------------------------

default_registry = PluginRegistry()

# Register plugin instances (for registry.get())
default_registry.register("manual", AnalogDevice(id="__analog__", name="AnalogDevice", config=None))
default_registry.register("midi", MidiDevice(id="__midi__", name="MidiDevice", config=None))
default_registry.register(
    "chase_bliss", ChaseBlissDevice(id="__cba__", name="ChaseBlissDevice", config=None)
)
default_registry.register("controller", MC6Device(id="__mc6__", name="MC6Device", config=None))

# Register model classes (for registry.get_model() — used by loader in P3)
default_registry.register_model("manual", AnalogDevice)
default_registry.register_model("midi", MidiDevice)
default_registry.register_model("chase_bliss", ChaseBlissDevice)
default_registry.register_model("controller", MC6Device)
