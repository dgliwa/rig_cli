from typing import Literal
from pydantic import BaseModel


class AnalogPreset(BaseModel):
    id: str
    pedal: str
    name: str
    values: dict[str, float | str | bool]
    notes: str | None = None
    photo: str | None = None
    tags: list[str] = []


class DigitalPreset(BaseModel):
    id: str
    pedal: str
    name: str
    preset_number: int
    parameters: dict[str, float | str | bool] = {}
    notes: str | None = None
    tags: list[str] = []


class MIDICommand(BaseModel):
    type: Literal["pc", "cc", "sysex"]
    channel: int
    value: int | bytes
    cc_number: int | None = None
    label: str | None = None
    delay_ms: int = 0


class HXBlock(BaseModel):
    name: str
    type: str
    model: str
    enabled: bool = True
    settings: dict[str, float | str | bool] = {}


class FootswitchAssignment(BaseModel):
    switch: str
    action: str
    target: str | None = None


class HXStompPreset(BaseModel):
    id: str
    pedal: str
    name: str
    preset_number: int
    blocks: list[HXBlock] = []
    midi_commands: list[MIDICommand] = []
    footswitch_assignments: list[FootswitchAssignment] = []
    tempo: int | None = None
    notes: str | None = None
    tags: list[str] = []
