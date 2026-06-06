"""PluginRegistry — maps device config type strings to Device implementations and model classes.

Phase 3: Registry scaffold created.
Phase 4: register_model/get_model added for loader-driven dispatch; Device instances registered in P2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rig.engine.plugin import Device


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Device] = {}
        self._model_classes: dict[str, type] = {}

    def register(self, config_type: str, plugin: Device) -> None:
        self._plugins[config_type] = plugin

    def get(self, config_type: str) -> Device | None:
        return self._plugins.get(config_type)

    def register_model(self, config_type: str, model_class: type) -> None:
        self._model_classes[config_type] = model_class

    def get_model(self, config_type: str) -> type | None:
        return self._model_classes.get(config_type)


def get_registry() -> PluginRegistry:
    """Return the default PluginRegistry instance with all four device types registered."""
    from rig.engine.devices import default_registry  # lazy to avoid circular import

    return default_registry
