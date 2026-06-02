from __future__ import annotations

from rig.engine.appliers.analog import AnalogApplier
from rig.engine.appliers.base import DeviceApplier
from rig.engine.appliers.chase_bliss import ChaseBlissApplier
from rig.engine.appliers.mc6 import MC6Applier
from rig.engine.appliers.midi_device import MidiApplier

_SCENE_APPLIERS: dict[str, DeviceApplier] = {
    "manual": AnalogApplier(),
    "midi": MidiApplier(),
    "chase_bliss": ChaseBlissApplier(),
}

_cba_applier = ChaseBlissApplier()
_mc6_applier = MC6Applier()


def get_scene_applier(config_type: str) -> DeviceApplier:
    """Return the DeviceApplier for the given pedal config_type."""
    return _SCENE_APPLIERS.get(config_type, MidiApplier())


def get_cba_applier() -> ChaseBlissApplier:
    """Return the shared ChaseBlissApplier instance."""
    return _cba_applier


def get_mc6_applier() -> MC6Applier:
    """Return the shared MC6Applier instance."""
    return _mc6_applier
