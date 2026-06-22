from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from rig.engine.plugin import DeviceType


class ActionStatus(StrEnum):
    CONFIGURE = "configure"
    VERIFY = "verify"
    ANALOG = "analog"


class ParamDiff(BaseModel):
    name: str
    before: float | str | bool | None
    after: float | str | bool


class DeviceAction(BaseModel):
    device: str
    device_type: DeviceType
    status: ActionStatus
    preset_name: str = ""
    preset_number: int | None = None
    midi_channel: int | None = None
    instructions: list[str] = []
    before: str | None = None
    after: str | None = None
    param_diff: list[ParamDiff] = []


class ScenePlan(BaseModel):
    scene_name: str
    status: Literal["new", "changed", "unchanged"]
    device_actions: list[DeviceAction] = []


class Plan(BaseModel):
    status: Literal["clean", "changes_detected"]
    scenes: dict[str, ScenePlan] = {}
    missing_refs: list[str] = []
    unused_presets: list[str] = []
