"""DevicePlugin Protocol and PluginContext for the plugin architecture.

Phase 3: Protocol and context defined; no appliers registered yet (Phase 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rig.engine.state import RigState

if TYPE_CHECKING:
    from rig.models.device import Device
    from rig.models.rig import Rig


@dataclass
class PluginContext:
    state: RigState
    rig: Rig
    dry_run: bool


class DevicePlugin(Protocol):
    def plan(self, device: Device, ctx: PluginContext) -> object: ...

    def diff(self, device: Device, ctx: PluginContext) -> object: ...

    def apply(self, device: Device, ctx: PluginContext) -> object: ...
