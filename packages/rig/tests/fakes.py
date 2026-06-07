"""In-memory test doubles for I/O Protocols defined in rig.engine.ports.

These fakes implement the ConfirmationIO and StateWriter
Protocols with deterministic, in-memory behavior — no MIDI hardware and no
patching builtins.input required.
"""

from __future__ import annotations

from collections import deque

from rig.engine.state import RigState

_VALID = frozenset({"confirm", "retry", "skip", "quit"})


class InMemoryPromptAdapter:
    """Fake ConfirmationIO that returns configured responses.

    All five prompt methods return ``default`` unless a ``side_effect`` list
    is provided, in which case they pop from the front in order and fall back
    to ``default`` when exhausted.

    Only full-word _ConfirmResult values are valid:
    ``"confirm"``, ``"retry"``, ``"skip"``, ``"quit"``.
    """

    def __init__(
        self,
        default: str = "confirm",
        side_effect: list[str] | None = None,
    ) -> None:
        assert default in _VALID, f"Invalid default {default!r}; must be one of {_VALID}"
        if side_effect is not None:
            for v in side_effect:
                assert v in _VALID, f"Invalid side_effect value {v!r}; must be one of {_VALID}"
        self.default = default
        self._queue: deque[str] = deque(side_effect) if side_effect else deque()

    def _next(self) -> str:
        return self._queue.popleft() if self._queue else self.default

    def prompt_analog(self, device: str, preset_name: str) -> str:
        return self._next()

    def prompt_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool,
    ) -> str:
        return self._next()

    def prompt_cba_channel(self, device: str, midi_channel: int, midi_sent: bool) -> str:
        return self._next()

    def prompt_cba_preset(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int,
    ) -> str:
        return self._next()

    def prompt_cba_register(self, device: str, scene_refs: list[str]) -> str:
        return self._next()

    def prompt_mc6_navigate(self, bank_num: int) -> str:
        return self._next()


class InMemoryStateAdapter:
    """Fake StateWriter that stores RigState in memory only."""

    def __init__(self) -> None:
        self._state: RigState = RigState()

    @property
    def state(self) -> RigState:
        """Current in-memory state (lets tests assert without calling read)."""
        return self._state

    def read(self, root: str) -> RigState:
        return self._state

    def write(self, root: str, state: RigState) -> None:
        self._state = state
