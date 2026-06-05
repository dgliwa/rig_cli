---
phase: 4
plan: P1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/rig/engine/plugin.py
  - src/rig/engine/plugin_registry.py
  - tests/test_plugin.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Device is a Protocol in plugin.py with properties id, name, config and methods plan(ctx), diff(ctx), apply(ctx)"
    - "DeviceApplyContext dataclass exists in plugin.py with fields: action, state, rig, dry_run, confirmation_io, midi, connected_devices, config_path"
    - "PluginRegistry.register_model(config_type, model_class) stores model class by type string"
    - "PluginRegistry.get_model(config_type) returns stored model class or None"
    - "DevicePlugin Protocol is removed or deprecated (Device Protocol replaces it)"
    - "Existing test_plugin.py tests updated to reflect new Device Protocol shape"
  artifacts:
    - path: "src/rig/engine/plugin.py"
      provides: "Device Protocol, DeviceApplyContext, PluginContext"
      contains: "class Device(Protocol)"
    - path: "src/rig/engine/plugin_registry.py"
      provides: "PluginRegistry with register_model + get_model"
      contains: "register_model"
  key_links:
    - from: "src/rig/engine/plugin.py"
      to: "src/rig/engine/plan/models.py"
      via: "DeviceApplyContext.action field"
      pattern: "from rig.engine.plan.models import DeviceAction"
    - from: "src/rig/engine/plugin.py"
      to: "src/rig/engine/ports.py"
      via: "DeviceApplyContext.confirmation_io field"
      pattern: "from rig.engine.ports import ConfirmationIO"
    - from: "src/rig/engine/plugin.py"
      to: "src/rig/midi/adapter.py"
      via: "DeviceApplyContext.midi field"
      pattern: "from rig.midi.adapter import MidiManager"
---

<objective>
Redesign plugin.py to define Device as a Protocol (replacing DevicePlugin) and add DeviceApplyContext for apply-time context. Extend PluginRegistry with model-class registration so the loader can use registry-driven dispatch in Phase P3.

This is the foundation wave. P2 and P3 depend on the contracts defined here.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-plugin-migration/04-CONTEXT.md
@src/rig/engine/plugin.py
@src/rig/engine/plugin_registry.py
@src/rig/engine/appliers/base.py
@src/rig/engine/ports.py
@src/rig/engine/plan/models.py
@tests/test_plugin.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace DevicePlugin with Device Protocol in plugin.py</name>
  <files>src/rig/engine/plugin.py, tests/test_plugin.py</files>
  <behavior>
    Replace the `DevicePlugin` Protocol (which took `device` as first arg) with a `Device` Protocol where the device IS the protocol instance. The new Device Protocol has:
    - Property `id: str`
    - Property `name: str`
    - Property `config: object` (typed as `Any` or the base `DeviceConfig`)
    - Method `plan(ctx: PluginContext) -> object`
    - Method `diff(ctx: PluginContext) -> object`
    - Method `apply(ctx: DeviceApplyContext) -> object`

    Keep `PluginContext` unchanged: `{state: RigState, rig: Rig, dry_run: bool}`.

    - Test: class with id/name/config properties and plan/diff/apply methods satisfies Device Protocol structurally
    - Test: class missing any property or method does NOT satisfy Device Protocol
    - Test: Device Protocol is a typing.Protocol (not an ABC)
    - Test: plan and diff take PluginContext, apply takes DeviceApplyContext (distinct types)
  </behavior>
  <action>
    Update `src/rig/engine/plugin.py`:
    1. Remove `DevicePlugin` Protocol class
    2. Add `Device` Protocol class with id, name, config properties and plan/diff/apply methods
    3. TYPE_CHECKING guard for DeviceConfig import to avoid circular dep
    4. Update module docstring: "Device Protocol replaces DevicePlugin; concrete types implement this Protocol as Pydantic models."

    Update `tests/test_plugin.py`:
    1. Remove tests that verify old DevicePlugin shape
    2. Add tests verifying Device Protocol structure (properties + methods)
    3. Keep PluginContext tests unchanged
  </action>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add DeviceApplyContext dataclass to plugin.py</name>
  <files>src/rig/engine/plugin.py, tests/test_plugin.py</files>
  <behavior>
    `DeviceApplyContext` is a dataclass that carries everything a concrete device's `apply()` method needs:
    - `action: DeviceAction` — which preset to activate
    - `state: RigState` — current state (for reading/writing device state)
    - `rig: Rig` — full rig (for cross-device lookups)
    - `dry_run: bool` — if True, no side effects
    - `confirmation_io: ConfirmationIO` — for prompting the user
    - `midi: MidiManager | None = None` — MIDI hardware access
    - `connected_devices: set[str] = field(default_factory=set)` — devices with open MIDI connections
    - `config_path: str | None = None` — rig config repo root for state I/O

    - Test: DeviceApplyContext is a dataclass (not a Pydantic model)
    - Test: required fields are action, state, rig, dry_run, confirmation_io
    - Test: midi, connected_devices, config_path have defaults (None, empty set, None)
    - Test: DeviceApplyContext instantiates with all required fields
  </behavior>
  <action>
    In `src/rig/engine/plugin.py`:
    1. Import `DeviceAction` under TYPE_CHECKING guard (from rig.engine.plan.models)
    2. Import `ConfirmationIO` under TYPE_CHECKING guard (from rig.engine.ports)
    3. Import `MidiManager` under TYPE_CHECKING guard (from rig.midi.adapter)
    4. Add `DeviceApplyContext` dataclass with fields as specified
    5. Update Device Protocol: `apply(ctx: DeviceApplyContext) -> object`

    Note: use `from __future__ import annotations` so TYPE_CHECKING guard works for dataclass field types.
  </action>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend PluginRegistry with model-class registration</name>
  <files>src/rig/engine/plugin_registry.py, tests/test_plugin.py</files>
  <behavior>
    Add `register_model(config_type, model_class)` and `get_model(config_type)` to `PluginRegistry`.
    These are used by the loader (P3) to know which Pydantic model class to instantiate when parsing a device YAML with a given config type.

    Keep existing `register(config_type, plugin)` and `get(config_type)` for backward compat (they become no-ops or point to same registry after P2 registers concrete types).

    - Test: register_model("midi", MidiDeviceClass) stores the class
    - Test: get_model("midi") returns the stored class
    - Test: get_model("unknown") returns None
    - Test: register and get_model are independent from register and get
    - Test: PluginRegistry can store multiple config types
  </behavior>
  <action>
    In `src/rig/engine/plugin_registry.py`:
    1. Add `_model_classes: dict[str, type] = {}` to `__init__`
    2. Add `register_model(self, config_type: str, model_class: type) -> None`
    3. Add `get_model(self, config_type: str) -> type | None`
    4. Keep existing `_plugins` dict, `register`, and `get` methods
    5. Update module docstring to mention model-class registration for loader dispatch
  </action>
</task>

</tasks>

<success_criteria>
- `python -c "from rig.engine.plugin import Device, DeviceApplyContext, PluginContext"` exits 0
- `python -c "from rig.engine.plugin_registry import PluginRegistry; r = PluginRegistry(); r.register_model('midi', object); assert r.get_model('midi') is object"` exits 0
- `uv run pytest tests/test_plugin.py -v` all pass
- No `DevicePlugin` references remain in plugin.py (it is replaced by Device Protocol)
- `DeviceApplyContext` has all 8 fields: action, state, rig, dry_run, confirmation_io, midi, connected_devices, config_path
</success_criteria>
