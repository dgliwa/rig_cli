from rig.engine.plugin_registry import get_registry


def register() -> None:
    """Register ChaseBlissDevice with the core plugin registry."""
    from rig.engine.devices import ChaseBlissDevice

    registry = get_registry()
    registry.register("chase_bliss", ChaseBlissDevice(id="__cba__", name="ChaseBlissDevice", config=None))
    registry.register_model("chase_bliss", ChaseBlissDevice)
