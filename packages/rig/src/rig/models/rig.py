from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from rig.models.device import Device, DeviceType
from rig.models.scene import Scene


class Rig(BaseModel):
    # arbitrary_types_allowed so concrete Device plugin types (AnalogDevice, MidiDevice, etc.)
    # can be stored alongside the legacy Device model during the P3 migration.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    signal_chain: list[str] = []
    devices: dict[str, Any] = {}
    midi_channel: int | None = None

    @property
    def scenes(self) -> dict[str, Scene]:
        """Aggregate scenes from all controller devices.

        Scenes live in each controller's config; this property provides
        a unified view for consumers that iterate scenes.
        """
        aggregated: dict[str, Scene] = {}
        for device in self.devices.values():
            if device.type == DeviceType.CONTROLLER:
                cfg = device.config
                raw_scenes = (
                    cfg.get("scenes", {}) if isinstance(cfg, dict) else getattr(cfg, "scenes", {})
                )
                for name, data in raw_scenes.items():
                    if isinstance(data, dict):
                        aggregated[name] = Scene(
                            name=name,
                            description=data.get("description"),
                            presets=data.get("presets", {}),
                            tags=data.get("tags", []),
                        )
        return aggregated

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
