from typing import Literal

from pydantic import BaseModel


class Scene(BaseModel):
    name: str
    description: str | None = None
    tempo: int | None = None
    presets: dict[str, str]
    mc6_bank: int | None = None
    mc6_switch: Literal["A", "B", "C", "D", "E", "F"] | None = None
    tags: list[str] = []
