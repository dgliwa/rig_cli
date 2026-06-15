from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnalogConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["manual"] = "manual"
