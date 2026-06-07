from rig.engine.plugin_registry import get_registry
from rig_morningstar.device import MC6Device


def register() -> None:
    registry = get_registry()
    registry.register("controller", MC6Device(id="__mc6__", name="MC6Device", config=None))
    registry.register_model("controller", MC6Device)
