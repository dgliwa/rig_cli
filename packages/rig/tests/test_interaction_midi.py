from __future__ import annotations

import io

from rich.console import Console

import rig.interaction.midi as midi_interaction


def _capture_prompt_device_output(
    monkeypatch, device, preset_name, preset_number, midi_channel, midi_connected=False
):
    """Run prompt_device with 'confirm' input and capture console output."""
    output = io.StringIO()
    test_console = Console(file=output, highlight=False, markup=False)
    monkeypatch.setattr(midi_interaction, "console", test_console)
    monkeypatch.setattr("builtins.input", lambda _: "c")
    midi_interaction.prompt_device(
        device=device,
        preset_name=preset_name,
        preset_number=preset_number,
        midi_channel=midi_channel,
        midi_connected=midi_connected,
    )
    return output.getvalue()


def test_prompt_device_prints_manual_set_message_when_midi_channel_is_none(monkeypatch):
    output = _capture_prompt_device_output(
        monkeypatch,
        device="Mood MKII",
        preset_name="ambient",
        preset_number=None,
        midi_channel=None,
    )
    assert "Set Mood MKII manually (knobs/switches)" in output
