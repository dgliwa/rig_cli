from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from rig.engine.plugin import Device, DeviceType
from rig.models.scene import Scene


class Rig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    signal_chain: list[str] = []
    devices: dict[str, Device] = {}
    midi_channel: int | None = None
    scenes: dict[str, Scene] = {}

    @property
    def controller(self) -> Device | None:
        """Return the CONTROLLER device, or None."""
        for device in self.devices.values():
            if device.type == DeviceType.CONTROLLER:
                return device
        return None

    def apply_order(self) -> list[Device]:
        """Return devices in apply order: signal-chain devices by position, off-chain devices, then controller last."""
        from rig.models.graph import DeviceGraph

        return DeviceGraph(self).apply_order()


# Backward-compat alias
RigConfig = Rig
