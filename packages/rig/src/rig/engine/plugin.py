"""Device Protocol and apply-time context for the plugin architecture.

Device Protocol replaces DevicePlugin; concrete types implement this Protocol
as Pydantic models. Plugin authors create a Pydantic BaseModel subclass that
structurally satisfies the ``Device`` Protocol and register it via entry points.

Plugin Authoring Contract
-------------------------
A plugin must provide:

1. A Pydantic ``BaseModel`` subclass satisfying the ``Device`` Protocol
   (structural subtyping — no ABC inheritance required).
2. A ``pyproject.toml`` entry in ``[project.entry-points."rig.devices"]``
   mapping the config type key (e.g. ``chase_bliss``) to the Device class
   (e.g. ``rig_chasebliss.device:ChaseBlissDevice``).
3. The Device class is instantiated by core with ``id``, ``name``, and
   ``config`` from the rig YAML.

Required methods:

- **setup(ctx)** — one-time initialization. Connect MIDI ports, run device-
  specific setup phases (e.g. CBA 3-phase init). Return a ``SetupResult``.
  Called by the engine before scene apply.
- **apply(ctx)** — apply a single device action (send PC, prompt user, etc.).
  Return a ``DeviceApplyResult``.
- **get_scene_pc_command(preset_id)** — return a PC command dict for the
  given preset, or ``None`` if the device does not send PC messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel

from rig.engine.state import DeviceState, RigState

if TYPE_CHECKING:
    from rig.engine.plan.models import DeviceAction
    from rig.engine.ports import ConfirmationIO
    from rig.midi.adapter import MidiManager
    from rig.models.rig import Rig


class DeviceType(StrEnum):
    DIGITAL = "digital"
    ANALOG = "analog"
    MODELER = "modeler"
    CONTROLLER = "controller"


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


class DeviceApplyResult(BaseModel):
    """Result of applying one device action."""

    device: str
    status: Literal["confirmed", "skipped", "error"]
    preset: str | None = None
    error: str | None = None


def update_device_state(state: RigState, device: str, **fields) -> None:
    """Update a device's state fields in-place."""
    current = state.devices.get(device, DeviceState())
    state.devices[device] = current.model_copy(update=fields)


def mark_preset_saved(state: RigState, device: str, preset_id: str) -> None:
    """Mark one preset as saved through the single state-write path."""
    current = state.devices.get(device, DeviceState())
    updated = dict(current.presets_saved)
    updated[preset_id] = True
    update_device_state(state, device, presets_saved=updated)


class Preset(Protocol):
    """Minimal interface required by the engine from any preset type."""

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...


@runtime_checkable
class Device(Protocol):
    """Structural contract for device plugin classes.

    Plugin authors create a Pydantic ``BaseModel`` with these fields and
    methods. The class is registered via entry points — no import of core
    registration APIs needed.

    Example::

        from pydantic import BaseModel, ConfigDict, Field
        from rig.engine.plugin import (
            Device, DeviceApplyContext, DeviceApplyResult,
            Preset, SetupContext, SetupResult,
        )

        class MyDevice(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

            id: str
            name: str = ""
            config: Any
            presets: list[Preset] = Field(default_factory=list)

            def setup(self, ctx: SetupContext) -> SetupResult:
                return SetupResult()

            def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
                return None

            def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
                ...

    See ``rig-analog`` for a concrete reference implementation.
    """

    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def config(self) -> Any: ...

    @property
    def presets(self) -> list[Preset]: ...

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> Self: ...

    def setup(self, ctx: SetupContext) -> SetupResult: ...

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None: ...

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult: ...


@dataclass
class EditContext:
    """Context passed to EditorProtocol.edit() during preset editing.

    Uses string annotations for ConfirmationIO and Rig due to TYPE_CHECKING
    guard — from __future__ import annotations ensures they resolve correctly.
    """

    config_path: Path
    dry_run: bool
    confirmation_io: ConfirmationIO
    rig: Rig


@runtime_checkable
class EditorProtocol(Protocol):
    """Companion protocol for devices that support interactive preset editing.

    Implement alongside Device — do not add edit() to Device.
    """

    def edit(self, preset_id: str, ctx: EditContext) -> dict[str, Any]: ...
