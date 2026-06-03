from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel

from rig.engine.state import DeviceState, RigState
from rig.midi.adapter import MidiManager

if TYPE_CHECKING:
    from rig.engine.plan import DeviceAction
    from rig.models.rig import Rig


class DeviceApplyResult(BaseModel):
    """Result of applying one device action."""

    device: str
    status: Literal["confirmed", "skipped", "error"]
    preset: str | None = None
    error: str | None = None


@dataclass
class ApplyContext:
    dry_run: bool
    midi: MidiManager | None = None
    connected_devices: set[str] = field(default_factory=set)
    state: RigState = field(default_factory=RigState)
    config_path: str | None = None
    rig: Rig | None = None


class DeviceApplier(Protocol):
    def apply_scene(self, action: DeviceAction, ctx: ApplyContext): ...


def update_device_state(state: RigState, device: str, **fields) -> None:
    """Update a device's state fields in-place."""
    current = state.devices.get(device, DeviceState())
    state.devices[device] = current.model_copy(update=fields)
