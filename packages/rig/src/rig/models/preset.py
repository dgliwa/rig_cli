from pydantic import BaseModel


# TODO: 1.2 should move to the analog plugin
class AnalogPreset(BaseModel):
    id: str
    pedal: str | None = None
    name: str
    values: dict[str, float | str | bool]
    notes: str | None = None
    photo: str | None = None
    tags: list[str] = []


# TODO: 1.2 should move to the chasebliss plugin (and be named something else)
class DigitalPreset(BaseModel):
    id: str
    pedal: str | None = None
    name: str
    preset_number: int
    parameters: dict[str, float | str | bool] = {}
    notes: str | None = None
    tags: list[str] = []


# TODO: 1.2 should move to the hx plugin
class HXStompPreset(BaseModel):
    id: str
    name: str
    preset_number: int
    hlx_file: str
    notes: str | None = None
    tags: list[str] = []


# TODO: 1.2 should just have a barebones Preset class here that the others extend from
