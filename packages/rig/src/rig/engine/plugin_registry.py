"""PluginRegistry — maps device config type strings to Device implementations.

Discovery via importlib.metadata.entry_points(group='rig.devices') at startup.
Legacy register()/get()/register_model()/get_model() interface preserved for
test compatibility. Entry point is the single production registration path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rig.engine.plugin import Device

logger = logging.getLogger(__name__)


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


_registry: PluginRegistry | None = None


def _discover() -> PluginRegistry:
    """Discover device plugins via entry points and return a populated PluginRegistry.

    Each entry point in the ``rig.devices`` group must point to a Device Pydantic
    model class. The class is loaded and registered under the entry point's name as
    both the plugin instance (lazy-instantiated with placeholder args) and the model
    class for loader dispatch.

    Failures to load a plugin produce a log warning but do not crash.
    If no entry points are found (zero plugins installed), the registry is empty.
    """
    import importlib.metadata as m

    registry = PluginRegistry()

    eps = m.entry_points(group="rig.devices")
    for ep in eps:
        try:
            model_class = ep.load()
            if not isinstance(model_class, type):
                logger.warning(
                    "Entry point '%s' does not resolve to a class (got %s)",
                    ep.name,
                    type(model_class).__name__,
                )
                continue
            # Register the model class for loader dispatch
            registry.register_model(ep.name, model_class)
            # Create a lazy placeholder instance for plugin dispatch via model_construct
            # to bypass Pydantic validators — placeholder is never used for production data.
            placeholder = model_class.model_construct(
                id=f"__{ep.name}__",
                name=str(ep.name),
                config=None,
                presets=[],
            )
            registry.register(ep.name, placeholder)
            logger.debug("Registered device plugin '%s' → %s", ep.name, model_class.__name__)
        except Exception as exc:
            logger.warning("Failed to load device plugin '%s': %s", ep.name, exc)

    return registry


def get_registry() -> PluginRegistry:
    """Return the shared PluginRegistry singleton.

    Lazily discovered from entry points on first call.
    """
    global _registry
    if _registry is None:
        _registry = _discover()
    return _registry


def reload_registry() -> PluginRegistry:
    """Force re-discovery and return a fresh registry. Used in tests."""
    global _registry
    _registry = _discover()
    return _registry
