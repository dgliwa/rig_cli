"""I/O port Protocols and production adapters for the apply engine.

Defines the structural contracts (ConfirmationIO, StateWriter)
that allow the engine and appliers to be tested without MIDI hardware or
patching builtins.input.
"""

from __future__ import annotations

import logging
from typing import Literal, Protocol

from rig.engine.state import RigState, read_state, write_state

logger = logging.getLogger(__name__)

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


class ConfirmationIO(Protocol):
    """Protocol for human-confirmation prompts used by the apply engine."""

    def prompt_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool,
    ) -> _ConfirmResult: ...

    def prompt_mc6_navigate(self, bank_num: int) -> _ConfirmResult: ...

    def prompt(self, text: str) -> str: ...


class StateWriter(Protocol):
    """Protocol for reading and writing rig state."""

    def read(self, root: str) -> RigState: ...

    def write(self, root: str, state: RigState) -> None: ...


class RichConfirmationIO:
    """Production adapter: delegates to Rich-powered interaction.* functions."""

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

    def prompt_mc6_navigate(self, bank_num: int) -> _ConfirmResult:
        input(f"  Navigate the MC6 to Bank {bank_num}, then press Enter...")
        return "confirm"

    def prompt(self, text: str) -> str:
        return input(text).strip().lower()


class FileStateWriter:
    """Production adapter: delegates to engine.state read/write functions."""

    def read(self, root: str) -> RigState:
        return read_state(root)

    def write(self, root: str, state: RigState) -> None:
        write_state(root, state)
