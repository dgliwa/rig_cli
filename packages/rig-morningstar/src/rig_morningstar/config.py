from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MC6Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["controller"] = "controller"
    banks: list[dict[str, Any]] = Field(default_factory=list)
