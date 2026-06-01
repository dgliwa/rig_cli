from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PedalType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    CONTROLLER = "controller"
    MODELER = "modeler"


class ControlType(StrEnum):
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
    value: str | float | int | None = None
    midi_cc: int | None = None
    expression_assignable: bool = False


class PedalConfig(BaseModel):
    """Base for pedal configuration types. Discriminated by the ``type`` field."""

    type: str
    midi_channel: int | None = None


class ManualConfig(PedalConfig):
    """Pedal with no MIDI — knobs and switches set by hand."""

    type: Literal["manual"] = "manual"
    controls: list[Control] = []


class MidiConfig(PedalConfig):
    """Pedal controlled via MIDI."""

    type: Literal["midi"] = "midi"
    midi_channel: int  # required override
    midi_device_id: int | None = None


class ChaseBlissConfig(MidiConfig):
    """Chase Bliss Audio pedal — MIDI with power-on channel learn."""

    type: Literal["chase_bliss"] = "chase_bliss"


class PedalDefinition(BaseModel):
    id: str
    manufacturer: str
    model: str
    type: PedalType
    config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]
    image: str | None = None
    notes: str | None = None
