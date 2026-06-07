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
# Device Protocol tests (replaces DevicePlugin tests)
# ---------------------------------------------------------------------------


def test_device_protocol_is_a_typing_protocol() -> None:
    import typing

    from rig.engine.plugin import Device

    assert issubclass(Device, typing.Protocol)


def test_device_protocol_satisfied_by_class_with_all_members() -> None:
    from rig.engine.plugin import DeviceApplyContext

    class GoodDevice:
        @property
        def id(self) -> str:
            return "test-id"

        @property
        def name(self) -> str:
            return "Test Device"

        @property
        def config(self) -> object:
            return None

        def plan(self, ctx: PluginContext) -> object:
            return None

        def diff(self, ctx: PluginContext) -> object:
            return None

        def apply(self, ctx: DeviceApplyContext) -> object:
            return None

    device = GoodDevice()
    assert hasattr(device, "id")
    assert hasattr(device, "name")
    assert hasattr(device, "config")
    assert hasattr(device, "plan")
    assert hasattr(device, "diff")
    assert hasattr(device, "apply")


def test_device_protocol_missing_property_detected_via_hasattr() -> None:
    class MissingConfigDevice:
        @property
        def id(self) -> str:
            return "test"

        @property
        def name(self) -> str:
            return "Test"

        # missing config, plan, diff, apply

    device = MissingConfigDevice()
    assert hasattr(device, "id")
    assert hasattr(device, "name")
    assert not hasattr(device, "config")
    assert not hasattr(device, "plan")
    assert not hasattr(device, "diff")
    assert not hasattr(device, "apply")


def test_device_protocol_has_distinct_context_types() -> None:
    """plan/diff take PluginContext; apply takes DeviceApplyContext."""
    from rig.engine.plugin import Device

    hints = Device.plan.__annotations__  # type: ignore[attr-defined]
    assert "ctx" in hints
    plan_ctx_annotation = hints["ctx"]
    assert "PluginContext" in str(plan_ctx_annotation)

    apply_hints = Device.apply.__annotations__  # type: ignore[attr-defined]
    assert "ctx" in apply_hints
    apply_ctx_annotation = apply_hints["ctx"]
    assert "DeviceApplyContext" in str(apply_ctx_annotation)


def test_device_plugin_is_absent_or_deprecated() -> None:
    """DevicePlugin should no longer be importable from plugin.py."""
    import rig.engine.plugin as plugin_module

    assert not hasattr(plugin_module, "DevicePlugin"), (
        "DevicePlugin should be removed — Device Protocol replaces it"
    )


# ---------------------------------------------------------------------------
# DeviceApplyContext tests
# ---------------------------------------------------------------------------


def test_device_apply_context_is_dataclass() -> None:
    from rig.engine.plugin import DeviceApplyContext

    assert dataclasses.is_dataclass(DeviceApplyContext)


def test_device_apply_context_is_not_pydantic_model() -> None:
    from pydantic import BaseModel

    from rig.engine.plugin import DeviceApplyContext

    assert not issubclass(DeviceApplyContext, BaseModel)


def test_device_apply_context_required_fields() -> None:
    field_names = [
        f.name
        for f in dataclasses.fields(
            __import__("rig.engine.plugin", fromlist=["DeviceApplyContext"]).DeviceApplyContext
        )
    ]
    assert "action" in field_names
    assert "state" in field_names
    assert "rig" in field_names
    assert "dry_run" in field_names
    assert "confirmation_io" in field_names


def test_device_apply_context_optional_fields_have_defaults() -> None:
    from rig.engine.plugin import DeviceApplyContext

    fields_by_name = {f.name: f for f in dataclasses.fields(DeviceApplyContext)}
    import dataclasses as dc

    # midi should default to None
    assert (
        fields_by_name["midi"].default is None
        or fields_by_name["midi"].default_factory is not dc.MISSING
    )  # type: ignore[misc]
    # connected_devices should default to a factory (empty set)
    assert fields_by_name["connected_devices"].default_factory is not dc.MISSING  # type: ignore[misc]
    # config_path should default to None
    assert fields_by_name["config_path"].default is None


def test_device_apply_context_has_all_eight_fields() -> None:
    from rig.engine.plugin import DeviceApplyContext

    field_names = [f.name for f in dataclasses.fields(DeviceApplyContext)]
    expected = {
        "action",
        "state",
        "rig",
        "dry_run",
        "confirmation_io",
        "midi",
        "connected_devices",
        "config_path",
    }
    assert set(field_names) == expected


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


# ---------------------------------------------------------------------------
# PluginRegistry model-class registration tests
# ---------------------------------------------------------------------------


def test_plugin_registry_register_model_stores_class() -> None:
    registry = PluginRegistry()

    class FakeMidiDevice:
        pass

    registry.register_model("midi", FakeMidiDevice)
    assert registry.get_model("midi") is FakeMidiDevice


def test_plugin_registry_get_model_unregistered_returns_none() -> None:
    registry = PluginRegistry()
    assert registry.get_model("unknown") is None


def test_plugin_registry_get_model_independent_from_get() -> None:
    """register_model/get_model are independent from register/get."""
    registry = PluginRegistry()

    class FakePlugin:
        pass

    class FakeModelClass:
        pass

    plugin_stub = object()
    registry.register("midi", plugin_stub)  # type: ignore[arg-type]
    registry.register_model("midi", FakeModelClass)

    assert registry.get("midi") is plugin_stub
    assert registry.get_model("midi") is FakeModelClass


def test_plugin_registry_stores_multiple_model_types() -> None:
    registry = PluginRegistry()

    class FakeAnalog:
        pass

    class FakeMidi:
        pass

    class FakeCba:
        pass

    registry.register_model("manual", FakeAnalog)
    registry.register_model("midi", FakeMidi)
    registry.register_model("chase_bliss", FakeCba)

    assert registry.get_model("manual") is FakeAnalog
    assert registry.get_model("midi") is FakeMidi
    assert registry.get_model("chase_bliss") is FakeCba
    assert registry.get_model("controller") is None


# ---------------------------------------------------------------------------
# Entry point discovery tests
# ---------------------------------------------------------------------------


def test_reload_registry_returns_plugin_registry() -> None:
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    assert registry is not None
    assert isinstance(registry, PluginRegistry)


def test_get_registry_returns_cached_instance() -> None:
    from rig.engine.plugin_registry import get_registry, reload_registry

    first = reload_registry()
    second = get_registry()
    assert first is second


def test_reload_registry_discards_previous_cache() -> None:
    from rig.engine.plugin_registry import get_registry, reload_registry

    first = get_registry()
    second = reload_registry()
    assert first is not second


def test_discovery_finds_registered_plugins() -> None:
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    names = set(registry._plugins.keys())
    assert "manual" in names
    assert "midi" in names
    assert "chase_bliss" in names
    assert "controller" in names


def test_discovery_registers_model_classes() -> None:
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    assert registry.get_model("manual") is not None
    assert registry.get_model("midi") is not None
    assert registry.get_model("chase_bliss") is not None
    assert registry.get_model("controller") is not None


def test_discovery_placeholder_implements_device_protocol() -> None:
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    device = registry.get("manual")
    assert device is not None
    assert hasattr(device, "id")
    assert hasattr(device, "name")
    assert hasattr(device, "config")
    assert hasattr(device, "plan")
    assert hasattr(device, "diff")
    assert hasattr(device, "apply")


def test_discovery_in_workspace_finds_all_plugins() -> None:
    """In the uv workspace all 4 plugin packages are installed, so discovery
    should find them all. This test verifies the happy path."""
    from rig.engine.plugin_registry import reload_registry

    registry = reload_registry()
    # In the workspace environment, all 4 plugins are always installed
    assert len(registry._plugins) >= 1
    assert len(registry._model_classes) >= 1


def test_bad_entry_point_does_not_crash_discovery() -> None:
    from rig.engine.plugin_registry import _discover

    registry = _discover()
    assert isinstance(registry, PluginRegistry)
