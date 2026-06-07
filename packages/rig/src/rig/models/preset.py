from pydantic import BaseModel


class AnalogPreset(BaseModel):
    id: str
    pedal: str | None = None
    name: str
    values: dict[str, float | str | bool]
    notes: str | None = None
    photo: str | None = None
    tags: list[str] = []


class DigitalPreset(BaseModel):
    id: str
    pedal: str | None = None
    name: str
    preset_number: int
    parameters: dict[str, float | str | bool] = {}
    notes: str | None = None
    tags: list[str] = []


class HXStompPreset(BaseModel):
    id: str
    name: str
    preset_number: int
    hlx_file: str
    notes: str | None = None
    tags: list[str] = []
