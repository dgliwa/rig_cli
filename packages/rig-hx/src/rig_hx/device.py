"""HX Stomp device implementation — PC-message-based modeler device."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from rig.engine.appliers.base import DeviceApplyResult, update_device_state
from rig.engine.plugin import DeviceApplyContext, DeviceType, SetupContext, SetupResult
from rig.engine.state import DeviceState
from rig.models.preset import MidiPreset
from rig_hx.config import HXStompConfig
from rig_hx.preset import HXStompPreset

logger = logging.getLogger(__name__)
console = Console()


class HXStompDevice(BaseModel):
    """Line 6 HX Stomp — PC-message-based modeler.

    Applies presets by sending a Program Change message on the configured MIDI
    channel. Named HXStompDevice rather than a generic MidiDevice to leave room
    for future HX-specific functionality (SysEx preset management, block-level
    configuration, etc.).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    id: str
    name: str = ""
    config: HXStompConfig
    type: DeviceType = DeviceType.MODELER
    presets: list[HXStompPreset | MidiPreset] = Field(default_factory=list)

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> HXStompDevice:
        config = HXStompConfig(**(data.get("config") or {}))
        raw_presets = data.get("presets") or []
        if data.get("type") == DeviceType.MODELER:
            presets: list[HXStompPreset | MidiPreset] = [HXStompPreset(**p) for p in raw_presets]
            device_type = DeviceType.MODELER
        else:
            presets = [MidiPreset(**p) for p in raw_presets]
            device_type = DeviceType.DIGITAL
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type=device_type,
            config=config,
            presets=presets,
        )

    def setup(self, ctx: SetupContext) -> SetupResult:
        """Connect MIDI to the HX Stomp before apply uses it."""
        if ctx.dry_run or ctx.midi is None:
            ctx.connected_devices.add(self.id)
            return SetupResult()

        ch = self.config.midi_channel or 1
        from rig.interaction.midi import prompt_midi_connect

        cached_port = ctx.state.devices.get(self.id, DeviceState()).midi_port
        res, port_name = prompt_midi_connect(self.id, ch, ctx.midi, cached_port)
        if res == "quit":
            return SetupResult(cancelled=True)
        if res == "confirm" and port_name:
            update_device_state(ctx.state, self.id, midi_port=port_name)
            ctx.connected_devices.add(self.id)
            return SetupResult(state_modified=True)
        return SetupResult()

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        """Return a PC command dict for the given preset_id, or None if not applicable."""
        ch = self.config.midi_channel
        if ch is None:
            return None
        for preset in self.presets:
            if (
                preset.id == preset_id
                and hasattr(preset, "preset_number")
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
        """Send PC message to HX Stomp and prompt user for confirmation."""
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
