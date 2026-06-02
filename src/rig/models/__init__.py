from rig.models.controller import Controller, ControllerType, MC6Config
from rig.models.device import (
    ChaseBlissConfig,
    Control,
    ControlType,
    Device,
    DeviceConfig,
    DeviceType,
    ManualConfig,
    MidiConfig,
    Preset,
)
from rig.models.preset import (
    AnalogPreset,
    DigitalPreset,
    HXStompPreset,
)
from rig.models.rig import Rig, RigConfig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition

# Backward-compat aliases
PedalConfig = DeviceConfig
PedalDefinition = Device
PedalType = DeviceType

__all__ = [
    # New names
    "Device",
    "DeviceConfig",
    "DeviceType",
    "Controller",
    "ControllerType",
    "MC6Config",
    "Rig",
    "Preset",
    # Config types
    "Control",
    "ControlType",
    "ManualConfig",
    "MidiConfig",
    "ChaseBlissConfig",
    # Preset types
    "AnalogPreset",
    "DigitalPreset",
    "HXStompPreset",
    # Other models
    "Scene",
    "SignalChainPosition",
    # Backward-compat aliases
    "PedalConfig",
    "PedalDefinition",
    "PedalType",
    "RigConfig",
]
