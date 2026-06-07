---
phase: 6
plan: P1
type: implementation
wave: 1
depends_on: []
files_modified:
  - packages/rig/src/rig/engine/plugin_registry.py
  - packages/rig/src/rig/engine/devices.py
  - packages/rig/src/rig/config/loader.py
  - packages/rig/pyproject.toml
  - packages/rig-analog/pyproject.toml
  - packages/rig-analog/src/rig_analog/__init__.py
  - packages/rig-chasebliss/pyproject.toml
  - packages/rig-chasebliss/src/rig_chasebliss/__init__.py
  - packages/rig-morningstar/pyproject.toml
  - packages/rig-morningstar/src/rig_morningstar/__init__.py
  - packages/rig-hx/pyproject.toml
  - packages/rig-hx/src/rig_hx/__init__.py
  - packages/rig-hx/src/rig_hx/device.py
requirements: [CORE-01, CORE-02, CORE-03]
must_haves:
  - `rig` core `pyproject.toml` declares empty `[project.entry-points."rig.devices"]` group
  - `get_registry()` discovers plugins via `importlib.metadata.entry_points(group='rig.devices')` loading Device classes directly
  - All 4 plugin entry points updated to point to Device model classes (not `register()` callbacks)
  - Plugin `__init__.py` `register()` functions removed
  - Hardcoded `default_registry` registrations in `devices.py` removed
  - Entry points are the single registration path — no fallback needed per D-03
  - `loader.py` still resolves device types correctly via registry
  - `uv run python3 -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(r._plugins.keys())"` shows all 4 device types
---

# Phase 6 P1: Entry Point Group Schema & PluginRegistry Discovery

## Context

Currently device registration happens two ways simultaneously:
1. **Hardcoded** in `packages/rig/src/rig/engine/devices.py` — `default_registry` is populated at module level with all 4 device types
2. **Callback-based** in plugin packages — each `register()` calls `get_registry().register(...)` against the same singleton

This plan removes both in favor of a single path: **Setuptools Entry Points** resolve directly to Device Pydantic model classes. The `PluginRegistry` discovers all `rig.devices` entry points at startup, loads each class, and registers it. No `register()` callbacks, no hardcoded registrations, no circular import patterns.

Per D-01: entry point → Device class directly (not `register()` callback).
Per D-03: old hardcoded registrations removed; entry points are the single path.
Per D-06: core `pyproject.toml` declares empty `rig.devices` group (ensures `entry_points()` returns valid iterable even when no plugins installed).

The built-in Device classes (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device`) remain in `rig.engine.devices` for this phase (they move to plugin packages in Phase 7). Plugin packages currently reference these same core classes via import — the entry points will point directly to the core class (e.g., `rig.engine.devices:AnalogDevice`).

---

## Task P6-T1: Add empty `rig.devices` entry point group to core pyproject.toml

**File:** `packages/rig/pyproject.toml`

**Changes:**

Add a `[project.entry-points."rig.devices"]` table after the `[project.scripts]` section. The table is empty — it declares the group name so `importlib.metadata.entry_points(group='rig.devices')` always returns a valid list even when zero plugins are installed.

Insert after the `[project.scripts]` block:

```toml
[project.entry-points."rig.devices"]
```

The group must be declared as empty (no key-value pairs). This satisfies both D-06 and CORE-04 (zero hard deps on plugins).

**Verification:** `uv run python3 -c "import importlib.metadata as m; print(list(m.entry_points(group='rig.devices')))"` runs without error and returns a list (possibly empty if no plugins are installed with `rig.devices` entry points).

---

## Task P6-T2: Refactor `get_registry()` for entry point discovery

**File:** `packages/rig/src/rig/engine/plugin_registry.py`

**Changes:**

Replace the entire content of the file. The new implementation:

```python
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
            # Create a lazy placeholder instance for plugin dispatch.
            # The instance will be replaced when the loader parses actual device YAML.
            try:
                placeholder = model_class(id=f"__{ep.name}__", name=str(ep.name), config=None)
            except Exception:
                # Some model classes may require non-None config; try minimal constructor
                try:
                    placeholder = model_class(id=f"__{ep.name}__", name=str(ep.name), config=object())
                except Exception as exc:
                    logger.warning(
                        "Could not instantiate placeholder for '%s': %s", ep.name, exc
                    )
                    continue
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
```

Key design decisions in this implementation:
- `_discover()` iterates all `rig.devices` entry points, loads the class, and registers it
- The entry point's NAME (e.g., `analog`, `chase_bliss`) becomes the `config_type` key
- The class itself is registered as the `model_class` for loader dispatch
- A lazy placeholder instance is created for `plugin` dispatch (matches the pattern used by the old `default_registry`)
- Errors are logged but do not crash the CLI — CORE-02 compliance
- `get_registry()` is a cached singleton (lazy)
- `reload_registry()` exposed for test isolation
- The registry starts empty when no plugins are installed — CLI still works for `--help`, graceful degradation

Remove the old `default_registry` import pattern. The `get_registry()` function now owns the singleton.

**Verification:** `uv run python3 -c "from rig.engine.plugin_registry import get_registry; r = get_registry(); print(dict((k, type(v).__name__) for k,v in r._plugins.items()))"` prints the 4 device types.

---

## Task P6-T3: Remove hardcoded default_registry from devices.py

**File:** `packages/rig/src/rig/engine/devices.py`

**Changes:**

Remove the `default_registry` section at the bottom of the file:

```python
# ---------------------------------------------------------------------------
# Default PluginRegistry instance
# ---------------------------------------------------------------------------

default_registry = PluginRegistry()

# Register plugin instances (for registry.get())
default_registry.register("manual", AnalogDevice(id="__analog__", name="AnalogDevice", config=None))
default_registry.register("midi", MidiDevice(id="__midi__", name="MidiDevice", config=None))
default_registry.register(
    "chase_bliss", ChaseBlissDevice(id="__cba__", name="ChaseBlissDevice", config=None)
)
default_registry.register("controller", MC6Device(id="__mc6__", name="MC6Device", config=None))

# Register model classes (for registry.get_model() — used by loader in P3)
default_registry.register_model("manual", AnalogDevice)
default_registry.register_model("midi", MidiDevice)
default_registry.register_model("chase_bliss", ChaseBlissDevice)
default_registry.register_model("controller", MC6Device)
```

Remove this entire block. The `default_registry` global is no longer defined in this module.

Also update the imports at the top — remove:
```python
from rig.engine.plugin_registry import PluginRegistry
```
(already imported under `TYPE_CHECKING` or remove if only used for `default_registry`)

Check if `PluginRegistry` is still used elsewhere in the file — it should NOT be; the class import was only needed for `default_registry`. If `PluginRegistry` appears only in the removed block, remove the import entirely.

Similarly, remove any type annotations or references to `default_registry` in comments or docstrings.

The Device classes themselves (`AnalogDevice`, `MidiDevice`, `ChaseBlissDevice`, `MC6Device`) remain in this file. They are still the canonical implementations and are imported directly by plugin packages.

**Edge case:** The `ChaseBlissDevice` class has `from rig.engine.appliers.base import DeviceApplyResult, update_device_state` at top level — keep that import. The `ChaseBlissDevice` class also creates `self._midi_device = MidiDevice(id="", name="", config=None)` — keep that too. Only remove the `default_registry` + imports that only supported it.

**Verification:** `uv run python3 -c "from rig.engine.devices import AnalogDevice; print('OK')"` succeeds. `uv run python3 -c "from rig.engine.devices import default_registry"` raises `ImportError`.

---

## Task P6-T4: Update plugin entry points and remove `register()` functions

### 4a: rig-analog

**Files:**
- `packages/rig-analog/pyproject.toml`
- `packages/rig-analog/src/rig_analog/__init__.py`

**pyproject.toml changes:**

Change the entry point from:
```toml
[project.entry-points."rig.devices"]
analog = "rig_analog:register"
```
to:
```toml
[project.entry-points."rig.devices"]
analog = "rig_analog.device:AnalogDevice"
```

**__init__.py changes:**

Remove the content and leave the file empty (only `__init__.py` marker). The `register()` function is no longer needed — the entry point loads the `AnalogDevice` class directly.

The file should be:
```python
# Empty — device registration handled via entry point
```

### 4b: rig-chasebliss

**Files:**
- `packages/rig-chasebliss/pyproject.toml`
- `packages/rig-chasebliss/src/rig_chasebliss/__init__.py`

**pyproject.toml changes:**

Change from:
```toml
[project.entry-points."rig.devices"]
chase_bliss = "rig_chasebliss:register"
```
to:
```toml
[project.entry-points."rig.devices"]
chase_bliss = "rig.engine.devices:ChaseBlissDevice"
```

**__init__.py changes:**

Remove the `register()` function. The file should be:
```python
# Empty — device registration handled via entry point from core
```

### 4c: rig-morningstar

**Files:**
- `packages/rig-morningstar/pyproject.toml`
- `packages/rig-morningstar/src/rig_morningstar/__init__.py`

**pyproject.toml changes:**

Change from:
```toml
[project.entry-points."rig.devices"]
controller = "rig_morningstar:register"
```
to:
```toml
[project.entry-points."rig.devices"]
controller = "rig_morningstar.device:MC6Device"
```

**__init__.py changes:**

Remove the `register()` function. The file should be:
```python
# Empty — device registration handled via entry point
```

### 4d: rig-hx

**Files:**
- `packages/rig-hx/pyproject.toml`
- `packages/rig-hx/src/rig_hx/__init__.py`
- (new) `packages/rig-hx/src/rig_hx/device.py`

**pyproject.toml changes:**

Change from:
```toml
[project.entry-points."rig.devices"]
hx_stomp = "rig_hx:register"
```
to:
```toml
[project.entry-points."rig.devices"]
hx_stomp = "rig.engine.devices:MidiDevice"
```

(Note: HX Stomp currently has no dedicated Device class — it uses `MidiDevice` from core with `type: modeler`. This is correct until a dedicated `HXStompDevice` is created in a future phase.)

**__init__.py changes:**

Remove the `register()` function stub. The file should be:
```python
# Empty — device registration handled via entry point from core
```

No `device.py` file is needed — the entry point references the core class directly.

**Verification for all 4 plugins:** `uv run python3 -c "
import importlib.metadata as m
for ep in m.entry_points(group='rig.devices'):
    cls = ep.load()
    print(f'{ep.name} → {cls.__name__}')
"` prints the 4 device types with their class names.

---

## Task P6-T5: Re-`pip install -e` all packages to refresh entry point metadata

After updating `pyproject.toml` files, the editable installs need to be refreshed so the entry_points.txt metadata is regenerated.

Run:
```bash
uv pip install -e packages/rig
uv pip install -e packages/rig-analog
uv pip install -e packages/rig-chasebliss
uv pip install -e packages/rig-morningstar
uv pip install -e packages/rig-hx
```

**Verification:** `uv run python3 -c "
from rig.engine.plugin_registry import get_registry
r = get_registry()
for k in sorted(r._plugins):
    print(k, type(r._plugins[k]).__name__, r._model_classes[k].__name__)
"` prints:
```
analog AnalogDevice AnalogDevice
chase_bliss ChaseBlissDevice ChaseBlissDevice
controller MC6Device MC6Device
hx_stomp MidiDevice MidiDevice
```

---

## Task P6-T6: Run existing test suite — identify and fix failures

Run the full test suite to find regressions:

```bash
uv run pytest packages/rig/tests/ -q --no-header 2>&1
```

Expected failures and fixes:

1. **`test_default_registry_*` tests in `test_devices.py`** — These import `default_registry` from `rig.engine.devices` which no longer exists. Remove or update these tests (handled in P2).

2. **`test_get_registry_returns_registry_with_all_four_types`** in `test_devices.py` — This calls `get_registry()` and expects 4 types. After the change, it should still work since the workspaces packages are installed and entry points are discovered.

3. **`test_register_populates_registry`** in `packages/rig-analog/tests/test_analog_device.py` — This calls `register()` which no longer exists. Needs update.

4. **`test_plugin_registry_*` tests** — These create standalone `PluginRegistry()` instances and test basic get/set operations. They should still pass since the class interface is unchanged.

5. **Any test that imports from `rig.engine.devices`** — The module-level exports of Device classes are unchanged, only `default_registry` was removed.

Collect the list of failures and fix them. Do NOT modify P1 tests that belong in P2 — just note which tests fail and why.

**Verification:** Run `uv run pytest packages/rig/tests/ -q --no-header` and report pass/fail counts.

---

## Task P6-T7: Update loader.py to handle unregistered device types gracefully

**File:** `packages/rig/src/rig/config/loader.py`

**Changes:**

The `_parse_device()` function currently raises `ValidationError` when `get_registry().get_model(config_type)` returns `None`. This is correct behavior — an unregistered config type means no plugin is installed for that device.

No code changes needed. Verify by reading the function:

```python
def _parse_device(data: dict):
    config_data = data.get("config") or {}
    config_type = config_data.get("type") if isinstance(config_data, dict) else None
    model_class = get_registry().get_model(config_type)
    if model_class is None:
        raise ValidationError(
            f"Unknown device config type '{config_type}' — is the plugin registered?"
        )
    temp = Device(**data)
    return model_class(**{**data, "config": temp.config})
```

This already handles the "no plugins installed" case gracefully — it raises a clear error when the config references a device type that has no corresponding plugin installed. The CLI itself doesn't crash; only `rig validate` on a rig referencing unregistered devices would show this error.

**However**, the import `from rig.engine.plugin_registry import get_registry` at line 8 is fine — `get_registry()` still exists in the refactored module.

**No changes needed for this task.**

---

## Verification Checklist

Run all of these and confirm each succeeds:

1. **Core entry point group declared:**
   ```bash
   grep -q "rig.devices" packages/rig/pyproject.toml && echo "PASS: Core declares rig.devices group"
   ```

2. **Plugin entry points point to Device classes, not register:**
   ```bash
   grep -r "rig.devices" packages/rig-*/pyproject.toml | grep -v "register" && echo "PASS: All entry points point to Device classes"
   ```
   (This should show 4 lines, none containing `register`)

3. **No `register()` functions remain in plugin `__init__.py`:**
   ```bash
   grep -l "def register" packages/rig-*/src/*/__init__.py
   ```
   (Should print nothing — no matches)

4. **`default_registry` no longer in devices.py:**
   ```bash
   grep -c "default_registry" packages/rig/src/rig/engine/devices.py
   ```
   (Should print `0`)

5. **Discovery returns all 4 types when plugins installed:**
   ```bash
   uv run python3 -c "
   from rig.engine.plugin_registry import get_registry
   r = get_registry()
   assert len(r._plugins) == 4, f'Expected 4 plugins, got {len(r._plugins)}'
   print('PASS: 4 plugins discovered')
   "
   ```

6. **`get_registry()` works with zero plugins (empty env):**
   ```bash
   uv run python3 -c "
   from rig.engine.plugin_registry import PluginRegistry
   r = PluginRegistry()
   assert r.get('analog') is None
   print('PASS: Empty registry works')
   "
   ```
