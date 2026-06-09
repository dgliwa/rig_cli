from rig.models.preset import Preset


class DigitalPreset(Preset):
    pedal: str | None = None
    preset_number: int
    # TODO: 1.3 when parsing the cba device, we should have custom validation that the pedal type supports the param names?
    parameters: dict[str, float | str | bool] = {}
