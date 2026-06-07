from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from rig.models.device import ControllerConfig, Device, DeviceType
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


class Rig(BaseModel):
    # arbitrary_types_allowed so concrete Device plugin types (AnalogDevice, MidiDevice, etc.)
    # can be stored alongside the legacy Device model during the P3 migration.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str | None = None
    signal_chain: list[SignalChainPosition]
    devices: dict[str, Any] = {}
    midi_channel: int | None = None

    # --- backward-compat properties used by code pending migration ---

    @property
    def pedals(self) -> dict[str, Device]:
        return self.devices

    @property
    def _controller_device(self) -> Device | None:
        """Return the first Device with type==CONTROLLER, or None."""
        for device in self.devices.values():
            if device.type == DeviceType.CONTROLLER:
                return device
        return None

    @property
    def controller(self) -> Device | None:
        """Compat property: returns the CONTROLLER device, or None."""
        return self._controller_device

    @property
    def scenes(self) -> dict[str, Scene]:
        """Compat property: returns scenes from ControllerConfig when a CONTROLLER device exists."""
        ctrl = self._controller_device
        if ctrl is not None and isinstance(ctrl.config, ControllerConfig):
            return ctrl.config.scenes
        return {}

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
        ctrl = self._controller_device
        if ctrl is not None and isinstance(ctrl.config, ControllerConfig):
            return {"banks": ctrl.config.banks}
        return {}

    def apply_order(self) -> list[Device]:
        """Return devices in apply order: signal-chain devices by position, off-chain devices, then controller last."""
        from rig.models.graph import DeviceGraph

        return DeviceGraph(self).apply_order()


# Backward-compat alias
RigConfig = Rig
