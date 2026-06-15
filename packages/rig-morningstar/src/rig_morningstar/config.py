from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MC6Config(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["controller"] = "controller"
    scenes: dict[str, Any] = Field(default_factory=dict)
    banks: list[dict[str, Any]] = Field(default_factory=list)
