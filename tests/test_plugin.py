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
