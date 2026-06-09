from pydantic import BaseModel


class Preset(BaseModel):
    """Barebones preset base — plugin-specific types extend this."""

    id: str
    name: str = ""
    notes: str | None = None
    tags: list[str] = []


class MidiPreset(Preset):
    """Generic MIDI device preset — a preset number sent as a PC message."""

    preset_number: int
