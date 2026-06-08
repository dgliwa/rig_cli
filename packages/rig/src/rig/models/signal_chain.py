from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


# TODO: 1.2 re-evaluate if this is what i want
class SignalChainPosition(BaseModel):
    device_ref: str = Field(validation_alias=AliasChoices("device", "pedal", "pedal_ref"))
    position: int
    loop: Literal["front", "fx_loop", "none"] = "front"
    stereo: bool = False

    model_config = {"populate_by_name": True}

    @property
    def pedal_ref(self) -> str:
        """Backward-compat alias for device_ref."""
        return self.device_ref
