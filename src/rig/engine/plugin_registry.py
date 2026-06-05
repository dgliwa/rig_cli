"""PluginRegistry — maps device config type strings to DevicePlugin implementations.

Phase 3: Registry is wirable but empty. Appliers are registered in Phase 4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rig.engine.plugin import DevicePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DevicePlugin] = {}

    def register(self, config_type: str, plugin: DevicePlugin) -> None:
        self._plugins[config_type] = plugin

    def get(self, config_type: str) -> DevicePlugin | None:
        return self._plugins.get(config_type)
