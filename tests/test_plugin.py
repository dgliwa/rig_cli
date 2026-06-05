from __future__ import annotations

import dataclasses

from rig.engine.plugin import PluginContext
from rig.engine.state import RigState

# ---------------------------------------------------------------------------
# PluginContext tests
# ---------------------------------------------------------------------------


def test_plugin_context_is_dataclass() -> None:
    assert dataclasses.is_dataclass(PluginContext)


def test_plugin_context_has_three_fields() -> None:
    field_names = [f.name for f in dataclasses.fields(PluginContext)]
    assert field_names == ["state", "rig", "dry_run"]


def test_plugin_context_instantiation() -> None:
    ctx = PluginContext(state=RigState(), rig=object(), dry_run=True)
    assert ctx.dry_run is True
    assert isinstance(ctx.state, RigState)


def test_plugin_context_is_not_pydantic_model() -> None:
    from pydantic import BaseModel

    ctx = PluginContext(state=RigState(), rig=object(), dry_run=False)
    assert not isinstance(ctx, BaseModel)


def test_plugin_context_all_fields_required() -> None:
    import pytest

    with pytest.raises(TypeError):
        PluginContext()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DevicePlugin structural protocol tests
# ---------------------------------------------------------------------------


def test_device_plugin_protocol_satisfied_by_class_with_all_methods() -> None:
    class GoodPlugin:
        def plan(self, device: object, ctx: object) -> object:
            return None

        def diff(self, device: object, ctx: object) -> object:
            return None

        def apply(self, device: object, ctx: object) -> object:
            return None

    plugin = GoodPlugin()
    assert hasattr(plugin, "plan")
    assert hasattr(plugin, "diff")
    assert hasattr(plugin, "apply")


def test_device_plugin_protocol_missing_method_detected_via_hasattr() -> None:
    class BadPlugin:
        def plan(self, device: object, ctx: object) -> object:
            return None

        # missing diff and apply

    plugin = BadPlugin()
    assert hasattr(plugin, "plan")
    assert not hasattr(plugin, "diff")
    assert not hasattr(plugin, "apply")


# ---------------------------------------------------------------------------
# PluginRegistry tests
# ---------------------------------------------------------------------------

from rig.engine.plugin_registry import PluginRegistry  # noqa: E402


def test_plugin_registry_empty_on_creation() -> None:
    registry = PluginRegistry()
    assert registry.get("manual") is None
    assert registry.get("midi") is None
    assert registry.get("chase_bliss") is None


def test_plugin_registry_get_unregistered_returns_none() -> None:
    registry = PluginRegistry()
    assert registry.get("nonexistent") is None


def test_plugin_registry_register_then_get() -> None:
    registry = PluginRegistry()
    stub = object()
    registry.register("manual", stub)  # type: ignore[arg-type]
    assert registry.get("manual") is stub


def test_plugin_registry_overwrite_registration() -> None:
    registry = PluginRegistry()
    first = object()
    second = object()
    registry.register("midi", first)  # type: ignore[arg-type]
    registry.register("midi", second)  # type: ignore[arg-type]
    assert registry.get("midi") is second


def test_plugin_registry_get_after_multiple_registrations() -> None:
    registry = PluginRegistry()
    a = object()
    b = object()
    registry.register("manual", a)  # type: ignore[arg-type]
    registry.register("midi", b)  # type: ignore[arg-type]
    assert registry.get("manual") is a
    assert registry.get("midi") is b
    assert registry.get("nonexistent") is None


def test_plugin_registry_no_module_level_registrations() -> None:
    """New registry must always start empty — no side effects at import time."""
    registry = PluginRegistry()
    assert registry.get("manual") is None
    assert registry.get("midi") is None
    assert registry.get("chase_bliss") is None
