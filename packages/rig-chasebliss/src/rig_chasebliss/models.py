from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CbaSetupAction(BaseModel):
    device: str
    midi_channel: int
    type: Literal["establish_channel", "build_preset", "register_scenes"]
    preset_id: str | None = None
    preset_name: str | None = None
    preset_number: int | None = None
    scene_refs: list[str] = []
    cc_params: list[dict[str, int]] = []
