from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from rig.engine.state import RigState
from rig.midi.adapter import MidiManager

if TYPE_CHECKING:
    from rig.engine.plan import DeviceAction
    from rig.models.rig import Rig


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
