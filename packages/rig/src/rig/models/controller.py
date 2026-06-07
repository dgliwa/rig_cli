from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

from rig.models.device import ControllerConfig as ControllerConfig


class ControllerType(StrEnum):
    MC6 = "mc6"


class MC6Config(BaseModel):
    """Configuration for a Morningstar MC6 controller."""

    type: Literal["mc6"] = "mc6"
    midi_channel: int = 1
    banks: list[dict[str, Any]] = []


class Controller(BaseModel):
    """A MIDI controller that routes scenes to button presses."""

    id: str
    manufacturer: str
    model: str
    type: ControllerType
    config: MC6Config
