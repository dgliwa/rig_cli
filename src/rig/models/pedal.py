from enum import Enum
from pydantic import BaseModel


class PedalType(str, Enum):
    DIGITAL = "digital"
    ANALOG = "analog"
    CONTROLLER = "controller"
    MODELER = "modeler"


class ControlType(str, Enum):
    KNOB = "knob"
    SWITCH = "switch"
    TOGGLE = "toggle"
    DIPSWITCH = "dipswitch"


class Control(BaseModel):
    name: str
    type: ControlType
    min: float | None = None
    max: float | None = None
    positions: list[str] | None = None
    midi_cc: int | None = None
    expression_assignable: bool = False


class PedalDefinition(BaseModel):
    id: str
    manufacturer: str
    model: str
    type: PedalType
    controls: list[Control] = []
    midi_channel: int | None = None
    midi_device_id: int | None = None
    image: str | None = None
    notes: str | None = None
