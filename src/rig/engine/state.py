"""State persistence for rig apply — tracks what has been configured on each device."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DeviceState(BaseModel):
    """Per-device state known to have been applied."""

    last_preset: str | None = None
    midi_port: str | None = None
    channel_established: bool = False
    midi_channel: int | None = None
    presets_saved: dict[str, bool] = {}
    registration_done: bool = False
    block_names: list[str] = []


class RigState(BaseModel):
    """Last-known applied state of the rig."""

    devices: dict[str, DeviceState] = {}
    scenes: dict[str, dict[str, Any]] = {}


def read_state(root: str) -> RigState:
    """Load state from .rig/state.json under *root*.

    Returns an empty ``RigState`` when no state file exists.
    """
    path = Path(root) / ".rig" / "state.json"
    if not path.exists():
        logger.debug("No state file at %s", path)
        return RigState()
    logger.debug("Reading state from %s", path)
    with open(path) as f:
        data = json.load(f)
    state = RigState.model_validate(data)
    logger.debug(
        "Loaded state: %d device(s), %d scene(s)",
        len(state.devices),
        len(state.scenes),
    )
    return state


def write_state(root: str, state: RigState) -> None:
    """Persist *state* to .rig/state.json under *root*."""
    path = Path(root) / ".rig" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "Writing state to %s (%d devices, %d scenes)",
        path,
        len(state.devices),
        len(state.scenes),
    )
    with open(path, "w") as f:
        json.dump(state.model_dump(exclude_none=True), f, indent=2)
