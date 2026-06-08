from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DeviceAction(BaseModel):
    device: str
    device_type: str
    status: Literal["configure", "verify", "analog"]
    preset_name: str = ""
    preset_number: int | None = None
    midi_channel: int | None = None
    instructions: list[str] = []
    before: str | None = None
    after: str | None = None


class ScenePlan(BaseModel):
    scene_name: str
    status: Literal["new", "changed", "unchanged"]
    device_actions: list[DeviceAction] = []


class Plan(BaseModel):
    status: Literal["clean", "changes_detected"]
    scenes: dict[str, ScenePlan] = {}
    missing_refs: list[str] = []
    unused_presets: list[str] = []
