from pydantic import BaseModel
from rig.models.pedal import PedalDefinition
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


class RigConfig(BaseModel):
    name: str
    description: str | None = None
    signal_chain: list[SignalChainPosition]
    pedals: dict[str, PedalDefinition] = {}
    digital_presets: dict[str, list[DigitalPreset]] = {}
    analog_presets: dict[str, list[AnalogPreset]] = {}
    hx_presets: dict[str, list[HXStompPreset]] = {}
    scenes: dict[str, Scene] = {}
    midi_channel: int | None = None
