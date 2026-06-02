# Re-exports for backward compatibility — prefer rig.models.device for new code.
from rig.models.device import (  # noqa: F401
    ChaseBlissConfig,
    Control,
    ControlType,
    ManualConfig,
    MidiConfig,
)
from rig.models.device import (
    Device as PedalDefinition,
)
from rig.models.device import (
    DeviceConfig as PedalConfig,
)
from rig.models.device import (
    DeviceType as PedalType,
)

__all__ = [
    "ChaseBlissConfig",
    "Control",
    "ControlType",
    "ManualConfig",
    "MidiConfig",
    "PedalConfig",
    "PedalDefinition",
    "PedalType",
]
