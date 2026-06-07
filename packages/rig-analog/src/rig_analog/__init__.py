from rig.engine.plugin_registry import get_registry
from rig_analog.device import AnalogDevice


def register() -> None:
    registry = get_registry()
    registry.register("manual", AnalogDevice(id="__analog__", name="AnalogDevice", config=None))
    registry.register_model("manual", AnalogDevice)
