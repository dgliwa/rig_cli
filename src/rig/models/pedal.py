from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from rig.models.rig import RigConfig


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

    def get_cc_params(self, parameters: dict[str, Any]) -> list[dict[str, int]]:
        return []


class ManualConfig(PedalConfig):
    """Pedal with no MIDI — knobs and switches set by hand."""

    type: Literal["manual"] = "manual"
    controls: list[Control] = []


class MidiConfig(PedalConfig):
    """Pedal controlled via MIDI."""

    type: Literal["midi"] = "midi"
    midi_channel: int  # required override
    midi_device_id: int | None = None
    controls: list[Control] = []

    def get_cc_params(self, parameters: dict[str, Any]) -> list[dict[str, int]]:
        by_name = {c.name: c for c in self.controls if c.midi_cc is not None}
        return [
            {"cc": by_name[k].midi_cc, "value": int(v)}
            for k, v in parameters.items()
            if k in by_name
        ]


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

    def get_scene_pc_command(self, preset_id: str, rig: RigConfig) -> dict[str, Any] | None:
        ch = self.config.midi_channel
        if ch is None:
            return None
        for hp in rig.hx_presets.get(self.id, []):
            if hp.id == preset_id and hp.preset_number is not None:
                return {
                    "type": "pc",
                    "channel": ch,
                    "value": hp.preset_number,
                    "label": f"{self.id}: {preset_id}",
                }
        for dp in rig.digital_presets.get(self.id, []):
            if dp.id == preset_id and dp.preset_number is not None:
                return {
                    "type": "pc",
                    "channel": ch,
                    "value": dp.preset_number,
                    "label": f"{self.id}: {preset_id}",
                }
        return None
