from typing import Literal
from pydantic import BaseModel


class SignalChainPosition(BaseModel):
    pedal_ref: str
    position: int
    loop: Literal["front", "fx_loop", "none"] = "front"
    stereo: bool = False
