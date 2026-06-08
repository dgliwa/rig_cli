from pydantic import BaseModel


class Scene(BaseModel):
    name: str
    description: str | None = None
    tempo: int | None = None
    presets: dict[str, str]
    tags: list[str] = []
