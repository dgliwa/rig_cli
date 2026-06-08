from pydantic import BaseModel


class Preset(BaseModel):
    """Barebones preset base — plugin-specific types extend this."""

    id: str
    name: str = ""
    notes: str | None = None
    tags: list[str] = []
