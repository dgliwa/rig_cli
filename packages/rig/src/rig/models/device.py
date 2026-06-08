from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from rig.models.preset import Preset


# TODO: we inconsistently use Enums and Literals. Pick one (whichever is the better python convention)
class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"
    CONTROLLER = "controller"


class Device(BaseModel):
    id: str
    type: DeviceType
    config: Any = None
    presets: list[Preset] = Field(default_factory=list)
    image: str | None = None
    notes: str | None = None

    def _get_midi_channel(self) -> int | None:
        """Extract midi_channel from config regardless of whether it's a dict or model."""
        if self.config is None:
            return None
        if isinstance(self.config, dict):
            return self.config.get("midi_channel")
        return getattr(self.config, "midi_channel", None)

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        ch = self._get_midi_channel()
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
