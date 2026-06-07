"""Device Protocol and apply-time context for the plugin architecture.

Device Protocol replaces DevicePlugin; concrete types implement this Protocol as Pydantic models.
Phase 4: Device Protocol, DeviceApplyContext, and PluginContext defined.
Concrete device types (AnalogDevice, MidiDevice, ChaseBlissDevice, MC6Device) registered in P2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from rig.engine.state import RigState

if TYPE_CHECKING:
    from rig.engine.plan.models import DeviceAction
    from rig.engine.ports import ConfirmationIO
    from rig.midi.adapter import MidiManager
    from rig.models.rig import Rig


@dataclass
class PluginContext:
    state: RigState
    rig: Rig
    dry_run: bool


@dataclass
class SetupContext:
    """Context passed to Device.setup() for one-time device initialization (MIDI connection, etc)."""

    state: RigState
    rig: Rig
    dry_run: bool
    confirmation_io: ConfirmationIO
    midi: MidiManager | None = None
    midi_connection_io: Any | None = None
    connected_devices: set[str] = field(default_factory=set)
    config_path: str | None = None


@dataclass
class SetupResult:
    cancelled: bool = False
    state_modified: bool = False


@dataclass
class DeviceApplyContext:
    action: DeviceAction
    state: RigState
    rig: Rig
    dry_run: bool
    confirmation_io: ConfirmationIO
    midi: MidiManager | None = None
    connected_devices: set[str] = field(default_factory=set)
    config_path: str | None = None


class Device(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def config(self) -> Any: ...

    def plan(self, ctx: PluginContext) -> object: ...

    def diff(self, ctx: PluginContext) -> object: ...

    def setup(self, ctx: SetupContext) -> SetupResult: ...

    def apply(self, ctx: DeviceApplyContext) -> object: ...
