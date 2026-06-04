"""I/O port Protocols and production adapters for the apply engine.

Defines the structural contracts (ConfirmationIO, StateWriter, MidiConnectionIO)
that allow the engine and appliers to be tested without MIDI hardware or
patching builtins.input.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Protocol

from rig.engine.state import RigState, read_state, write_state
from rig.interaction.analog import prompt_analog
from rig.interaction.cba import prompt_cba_build_preset, prompt_cba_channel, prompt_cba_register
from rig.interaction.midi import prompt_midi_connect

if TYPE_CHECKING:
    from rig.midi.adapter import MidiManager

logger = logging.getLogger(__name__)

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


class ConfirmationIO(Protocol):
    """Protocol for all human-confirmation prompts used by the apply engine."""

    def prompt_analog(self, device: str, preset_name: str) -> _ConfirmResult: ...

    def prompt_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool,
    ) -> _ConfirmResult: ...

    def prompt_cba_channel(
        self, device: str, midi_channel: int, midi_sent: bool
    ) -> _ConfirmResult: ...

    def prompt_cba_preset(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int,
    ) -> _ConfirmResult: ...

    def prompt_cba_register(self, device: str, scene_refs: list[str]) -> _ConfirmResult: ...


class StateWriter(Protocol):
    """Protocol for reading and writing rig state."""

    def read(self, root: str) -> RigState: ...

    def write(self, root: str, state: RigState) -> None: ...


class MidiConnectionIO(Protocol):
    """Protocol for prompting the user to connect a MIDI device."""

    def prompt_connect(
        self,
        device: str,
        midi_channel: int,
        midi: MidiManager,
        device_port: str | None,
    ) -> tuple[_ConfirmResult, str | None]: ...


class RichConfirmationIO:
    """Production adapter: delegates to Rich-powered interaction.* functions."""

    def prompt_analog(self, device: str, preset_name: str) -> _ConfirmResult:
        return prompt_analog(device, preset_name)

    def prompt_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool,
    ) -> _ConfirmResult:
        from rig.interaction.midi import prompt_device

        return prompt_device(device, preset_name, preset_number, midi_channel, midi_connected)

    def prompt_cba_channel(self, device: str, midi_channel: int, midi_sent: bool) -> _ConfirmResult:
        return prompt_cba_channel(device, midi_channel, midi_sent)

    def prompt_cba_preset(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int,
    ) -> _ConfirmResult:
        return prompt_cba_build_preset(device, preset_name, preset_number, midi_channel)

    def prompt_cba_register(self, device: str, scene_refs: list[str]) -> _ConfirmResult:
        return prompt_cba_register(device, scene_refs)


class FileStateWriter:
    """Production adapter: delegates to engine.state read/write functions."""

    def read(self, root: str) -> RigState:
        return read_state(root)

    def write(self, root: str, state: RigState) -> None:
        write_state(root, state)


class InteractiveMidiConnectionIO:
    """Production adapter: delegates to interaction.midi.prompt_midi_connect."""

    def prompt_connect(
        self,
        device: str,
        midi_channel: int,
        midi: MidiManager,
        device_port: str | None,
    ) -> tuple[_ConfirmResult, str | None]:
        return prompt_midi_connect(device, midi_channel, midi, device_port)
