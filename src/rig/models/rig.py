from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from rig.models.controller import Controller
from rig.models.device import Device
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


class Rig(BaseModel):
    name: str
    description: str | None = None
    signal_chain: list[SignalChainPosition]
    devices: dict[str, Device] = {}
    controller: Controller | None = None
    scenes: dict[str, Scene] = {}
    midi_channel: int | None = None

    # --- backward-compat properties used by code pending migration ---

    @property
    def pedals(self) -> dict[str, Device]:
        return self.devices

    @property
    def digital_presets(self) -> dict[str, list[DigitalPreset]]:
        return {
            k: [p for p in v.presets if isinstance(p, DigitalPreset)]
            for k, v in self.devices.items()
        }

    @property
    def hx_presets(self) -> dict[str, list[HXStompPreset]]:
        return {
            k: [p for p in v.presets if isinstance(p, HXStompPreset)]
            for k, v in self.devices.items()
        }

    @property
    def analog_presets(self) -> dict[str, list[AnalogPreset]]:
        return {
            k: [p for p in v.presets if isinstance(p, AnalogPreset)]
            for k, v in self.devices.items()
        }

    @property
    def mc6(self) -> dict[str, Any]:
        if self.controller:
            return {"banks": self.controller.config.banks}
        return {}


# Backward-compat alias
RigConfig = Rig
