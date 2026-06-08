from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rig.config.errors import ConfigError
from rig.models.device import Device, DeviceType

if TYPE_CHECKING:
    from rig.models.rig import Rig

logger = logging.getLogger(__name__)


class CycleError(ConfigError):
    """Signal chain contains a cycle."""


class DeviceGraph:
    def __init__(self, rig: Rig) -> None:
        self._rig = rig

    def apply_order(self) -> list[Device]:
        """Return devices in apply order: signal-chain devices by position, off-chain devices, then controller last."""
        if not self._rig.devices:
            return []

        self._detect_cycles()

        ctrl = None
        for device in self._rig.devices.values():
            if device.type == DeviceType.CONTROLLER:
                ctrl = device
                break

        chain_positions: dict[str, int] = {
            device_id: i for i, device_id in enumerate(self._rig.signal_chain)
        }

        in_chain: list[Device] = []
        off_chain: list[Device] = []

        for device in self._rig.devices.values():
            if ctrl is not None and device.id == ctrl.id:
                continue
            if device.id in chain_positions:
                in_chain.append(device)
            else:
                off_chain.append(device)

        in_chain.sort(key=lambda d: chain_positions[d.id])

        result = in_chain + off_chain
        if ctrl is not None:
            result.append(ctrl)
        return result

    def _detect_cycles(self) -> None:
        seen: set[str] = set()
        for device_id in self._rig.signal_chain:
            if device_id in seen:
                raise CycleError(f"Device '{device_id}' appears multiple times in signal chain")
            seen.add(device_id)
