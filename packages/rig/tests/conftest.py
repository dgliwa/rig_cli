from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rig.engine.plugin import (
    DeviceApplyContext,
    DeviceApplyResult,
    DeviceType,
    SetupContext,
    SetupResult,
)


@dataclass
class FakeDevice:
    """Minimal Protocol-satisfying Device for use in tests.

    Implements the Device Protocol structurally — id, name, type, config,
    presets plus stub setup(), get_scene_pc_command(), and apply() methods.
    """

    id: str
    type: DeviceType
    config: Any = None
    presets: list = field(default_factory=list)
    name: str = ""

    def setup(self, ctx: SetupContext) -> SetupResult:
        return SetupResult()

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        return None

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        return DeviceApplyResult(device=self.id, status="skipped", preset="")

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> FakeDevice:
        return cls(id=data["id"], type=DeviceType(data.get("type", "analog")))
