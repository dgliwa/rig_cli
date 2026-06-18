from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rig.engine.plugin import EditContext

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from rig.engine.plugin import (
    DeviceApplyContext,
    DeviceApplyResult,
    DeviceType,
    SetupContext,
    SetupResult,
    update_device_state,
)
from rig_analog.config import AnalogConfig
from rig_analog.preset import AnalogPreset

logger = logging.getLogger(__name__)
console = Console()


class AnalogDevice(BaseModel):
    """Manual (analog) device — knobs and switches set by hand."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    id: str
    name: str = ""
    config: AnalogConfig
    type: DeviceType = DeviceType.ANALOG
    presets: list[AnalogPreset] = Field(default_factory=list)

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> AnalogDevice:
        config = AnalogConfig(**(data.get("config") or {}))
        presets = [AnalogPreset(**p) for p in (data.get("presets") or [])]
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type=DeviceType.ANALOG,
            config=config,
            presets=presets,
        )

    def setup(self, ctx: SetupContext) -> SetupResult:
        return SetupResult()

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        return None

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

        while True:
            res = ctx.confirmation_io.prompt_device(
                action.device, action.preset_name, None, None, False
            )
            if res == "quit":
                return DeviceApplyResult(
                    device=action.device, status="error", preset=action.preset_name, error="quit"
                )
            if res == "confirm":
                update_device_state(ctx.state, action.device, last_preset=action.preset_name)
                return DeviceApplyResult(
                    device=action.device, status="confirmed", preset=action.preset_name
                )
            if res == "retry":
                continue
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

    def edit(self, preset_id: str, ctx: EditContext) -> dict[str, Any]:
        """Analog editor loop — no MIDI; user sets knobs manually."""
        preset = next((p for p in self.presets if p.id == preset_id), None)
        if preset is None:
            raise ValueError(f"Preset '{preset_id}' not found on device '{self.id}'")

        console.print(
            f"Editing [bold]{self.id}/{preset_id}[/bold] — type '<key> <value>' or 'done' to finish"
        )
        for key, value in preset.values.items():
            console.print(f"  {key}: {value}")

        updated: dict[str, Any] = dict(preset.values)

        while True:
            raw = ctx.confirmation_io.prompt("> ")
            if not raw or raw == "done":
                break
            parts = raw.split(None, 1)
            if len(parts) != 2:
                console.print("  [red]Usage: <key> <value>[/red]")
                continue
            key, value = parts[0], parts[1]
            if key not in preset.values:
                valid = ", ".join(preset.values.keys())
                console.print(f"  [red]Unknown key '{key}'. Valid keys: {valid}[/red]")
                continue
            updated[key] = value

        return updated
