from rig.models.preset import Preset


class AnalogPreset(Preset):
    pedal: str | None = None
    values: dict[str, float | str | bool]
    photo: str | None = None
