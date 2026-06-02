from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset

if TYPE_CHECKING:
    pass


class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
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


class DeviceConfig(BaseModel):
    """Base for device configuration strategies. Discriminated by ``type``."""

    type: str
    midi_channel: int | None = None

    def get_cc_params(self, parameters: dict[str, Any]) -> list[dict[str, int]]:
        return []


class ManualConfig(DeviceConfig):
    """Device with no MIDI — knobs and switches set by hand."""

    type: Literal["manual"] = "manual"
    controls: list[Control] = []


class MidiConfig(DeviceConfig):
    """Device controlled via MIDI."""

    type: Literal["midi"] = "midi"
    midi_channel: int
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


Preset = AnalogPreset | DigitalPreset | HXStompPreset


class Device(BaseModel):
    id: str
    manufacturer: str
    model: str
    type: DeviceType
    config: Annotated[ManualConfig | MidiConfig | ChaseBlissConfig, Field(discriminator="type")]
    presets: list[AnalogPreset | DigitalPreset | HXStompPreset] = Field(default_factory=list)
    image: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _populate_cba_controls(self) -> Device:
        if isinstance(self.config, ChaseBlissConfig) and not self.config.controls:
            from rig.catalog.chase_bliss import get_controls

            controls = get_controls(self.manufacturer, self.model)
            if controls:
                object.__setattr__(
                    self, "config", self.config.model_copy(update={"controls": controls})
                )
        return self

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        ch = self.config.midi_channel
        if ch is None:
            return None
        for preset in self.presets:
            if (
                preset.id == preset_id
                and isinstance(preset, (DigitalPreset, HXStompPreset))
                and preset.preset_number is not None
            ):
                return {
                    "type": "pc",
                    "channel": ch,
                    "value": preset.preset_number,
                    "label": f"{self.id}: {preset_id}",
                }
        return None
