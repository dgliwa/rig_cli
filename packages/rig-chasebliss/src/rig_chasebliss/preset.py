from rig.models.preset import Preset


class DigitalPreset(Preset):
    pedal: str | None = None
    preset_number: int
    parameters: dict[str, float | str | bool] = {}
