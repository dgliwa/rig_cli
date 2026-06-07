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

- **plan** / **diff** — currently raise ``NotImplementedError``; the plan
  command routes through ``rig.engine.plan.compute.compute_plan()`` and does
  not call these directly.
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
from typing import TYPE_CHECKING, Any, Protocol

from rig.engine.state import RigState

if TYPE_CHECKING:
    from rig.engine.appliers.base import DeviceApplyResult
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
    """Structural contract for device plugin classes.

    Plugin authors create a Pydantic ``BaseModel`` with these fields and
    methods. The class is registered via entry points — no import of core
    registration APIs needed.

    Example::

        from pydantic import BaseModel, ConfigDict, Field
        from rig.engine.plugin import (
            Device, DeviceApplyContext, DeviceApplyResult, PluginContext,
            SetupContext, SetupResult,
        )

        class MyDevice(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

            id: str
            name: str = ""
            config: Any
            presets: list[Any] = Field(default_factory=list)

            def plan(self, ctx: PluginContext) -> object:
                raise NotImplementedError

            def diff(self, ctx: PluginContext) -> object:
                raise NotImplementedError

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
    def presets(self) -> list[Any]: ...

    def plan(self, ctx: PluginContext) -> object: ...

    def diff(self, ctx: PluginContext) -> object: ...

    def setup(self, ctx: SetupContext) -> SetupResult: ...

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None: ...

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult: ...
