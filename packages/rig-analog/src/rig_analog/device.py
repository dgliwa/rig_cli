from __future__ import annotations

import logging
from typing import Any

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
