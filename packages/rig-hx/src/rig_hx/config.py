from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HXStompConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["midi"] = "midi"
    midi_channel: int | None = None
