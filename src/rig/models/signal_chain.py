from typing import Literal

from pydantic import BaseModel, Field


class SignalChainPosition(BaseModel):
    pedal_ref: str = Field(alias="pedal")
    position: int
    loop: Literal["front", "fx_loop", "none"] = "front"
    stereo: bool = False

    model_config = {"populate_by_name": True}
