---
phase: 3
plan: P4
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
    - "DevicePlugin is a Protocol class with plan, diff, and apply methods"
    - "PluginContext is a dataclass with exactly three fields: state, rig, dry_run"
    - "PluginRegistry has register(config_type, plugin) and get(config_type) methods"
    - "PluginRegistry.get() returns None for unregistered type strings"
    - "No appliers are registered in PluginRegistry in Phase 3"
    - "Both new files use from __future__ import annotations and TYPE_CHECKING guard"
  artifacts:
    - path: "src/rig/engine/plugin.py"
      provides: "DevicePlugin Protocol + PluginContext dataclass"
      exports: ["DevicePlugin", "PluginContext"]
    - path: "src/rig/engine/plugin_registry.py"
      provides: "PluginRegistry class (empty registry)"
      exports: ["PluginRegistry"]
    - path: "tests/test_plugin.py"
      provides: "Tests for PluginContext fields and PluginRegistry register/get"
      contains: "test_plugin_registry"
  key_links:
    - from: "src/rig/engine/plugin.py"
      to: "src/rig/engine/state.py"
      via: "PluginContext.state: RigState (direct import, not TYPE_CHECKING)"
      pattern: "from rig.engine.state import RigState"
    - from: "src/rig/engine/plugin_registry.py"
      to: "src/rig/engine/plugin.py"
      via: "TYPE_CHECKING import of DevicePlugin"
      pattern: "TYPE_CHECKING"
---

<objective>
Create engine/plugin.py with the DevicePlugin Protocol and PluginContext dataclass, and engine/plugin_registry.py with the PluginRegistry class. Both files are structurally independent of the Wave 2/3 model and loader changes — they can execute in parallel with P1 (Wave 1). Add tests/test_plugin.py with unit tests for the registry and context.

Purpose: Establishes the DevicePlugin/PluginContext/PluginRegistry scaffold per D-08, D-09, D-10. No appliers are registered in Phase 3. Phase 4 will register existing appliers against this registry.

Output: Two new engine files + test file. No modifications to existing code.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/03-core-domain-refactor/03-CONTEXT.md
@.planning/phases/03-core-domain-refactor/03-RESEARCH.md
@.planning/phases/03-core-domain-refactor/03-PATTERNS.md
@src/rig/engine/appliers/base.py
@src/rig/engine/appliers/registry.py
@src/rig/engine/ports.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create engine/plugin.py — DevicePlugin Protocol + PluginContext dataclass</name>
  <files>src/rig/engine/plugin.py, tests/test_plugin.py</files>
  <behavior>
    - Test: PluginContext is a dataclass (not a Pydantic BaseModel)
    - Test: PluginContext can be instantiated with state=RigState(), rig=..., dry_run=False
    - Test: PluginContext.dry_run is False by default? No — all three fields are required (no defaults per D-09)
    - Test: A class with plan/diff/apply methods satisfies DevicePlugin Protocol structurally
    - Test: A class missing any of the three methods does NOT satisfy DevicePlugin at runtime (Protocol is not enforced at runtime, but the existence check via hasattr works)
  </behavior>
  <action>
Create src/rig/engine/plugin.py following the exact pattern from src/rig/engine/appliers/base.py and src/rig/engine/ports.py:

```
File: src/rig/engine/plugin.py
```

Structure:
1. Module docstring: `"""DevicePlugin Protocol and PluginContext for the plugin architecture.\n\nPhase 3: Protocol and context defined; no appliers registered yet (Phase 4).\n"""`

2. `from __future__ import annotations` at the top.

3. Imports:
   - `from dataclasses import dataclass` (no `field` needed — all three fields are required, no defaults)
   - `from typing import TYPE_CHECKING, Protocol`
   - `from rig.engine.state import RigState` — import directly (not under TYPE_CHECKING) because it's used in the dataclass field type annotation at class definition time. RigState is a Pydantic model in engine/state.py; no circular import risk.

4. TYPE_CHECKING guard for forward references that would create circular imports:
   ```python
   if TYPE_CHECKING:
       from rig.models.device import Device
       from rig.models.rig import Rig
   ```

5. PluginContext dataclass:
   ```python
   @dataclass
   class PluginContext:
       state: RigState
       rig: Rig
       dry_run: bool
   ```
   All three fields are required (no defaults). `rig` is NOT Optional — per PATTERNS.md note: "rig is NOT Optional here — the plugin always has access to the full rig." Return type uses `Rig` from the TYPE_CHECKING import; with `from __future__ import annotations` this is fine.

6. DevicePlugin Protocol:
   ```python
   class DevicePlugin(Protocol):
       def plan(self, device: Device, ctx: PluginContext) -> object: ...
       def diff(self, device: Device, ctx: PluginContext) -> object: ...
       def apply(self, device: Device, ctx: PluginContext) -> object: ...
   ```
   Return type is `object` per RESEARCH.md (Phase 3 does not lock in a specific return shape — Phase 4 will define result types). Use `...` as method bodies (same as DeviceApplier in base.py and Port protocols in ports.py). No `@abstractmethod`, no ABC inheritance.

In tests/test_plugin.py (new file), write tests for PluginContext:
- Import PluginContext from rig.engine.plugin
- Import RigState from rig.engine.state
- Test that PluginContext(state=RigState(), rig=None, dry_run=False) raises TypeError (rig is required, not None)? No — rig: Rig is a type annotation, not a runtime enforcement. Dataclass fields accept None at runtime even if typed Rig. Test instead: PluginContext(state=RigState(), rig=object(), dry_run=True).dry_run == True
- Test that PluginContext has attributes state, rig, dry_run via dataclasses.fields()
- Test that PluginContext is NOT a Pydantic BaseModel (not isinstance(ctx, BaseModel))
  </action>
  <verify>
    <automated>uv run pytest tests/test_plugin.py -q 2>&1 | tail -10</automated>
  </verify>
  <done>tests/test_plugin.py passes. plugin.py exists with DevicePlugin Protocol and PluginContext dataclass. Both classes are importable without error.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create engine/plugin_registry.py — PluginRegistry (empty, wirable)</name>
  <files>src/rig/engine/plugin_registry.py, tests/test_plugin.py</files>
  <behavior>
    - Test: PluginRegistry() instantiates with an empty internal dict
    - Test: registry.get("manual") returns None (unregistered)
    - Test: After registry.register("manual", mock_plugin), registry.get("manual") returns mock_plugin
    - Test: registry.get("nonexistent") returns None after registrations
    - Test: registering the same config_type twice overwrites the first registration
    - Test: No appliers are registered at module load time (registry is empty by default)
  </behavior>
  <action>
Create src/rig/engine/plugin_registry.py following the dict-dispatch pattern from src/rig/engine/appliers/registry.py, but as a class rather than module-level functions:

```
File: src/rig/engine/plugin_registry.py
```

Structure:
1. Module docstring: `"""PluginRegistry — maps device config type strings to DevicePlugin implementations.\n\nPhase 3: Registry is wirable but empty. Appliers are registered in Phase 4.\n"""`

2. `from __future__ import annotations` at the top.

3. Imports:
   - `from typing import TYPE_CHECKING`
   - TYPE_CHECKING guard:
     ```python
     if TYPE_CHECKING:
         from rig.engine.plugin import DevicePlugin
     ```
     DevicePlugin is under TYPE_CHECKING to avoid importing plugin.py at module load time (keeping the dependency graph clean). The internal dict type annotation uses the string form via `from __future__ import annotations`.

4. PluginRegistry class:
   ```python
   class PluginRegistry:
       def __init__(self) -> None:
           self._plugins: dict[str, DevicePlugin] = {}

       def register(self, config_type: str, plugin: DevicePlugin) -> None:
           self._plugins[config_type] = plugin

       def get(self, config_type: str) -> DevicePlugin | None:
           return self._plugins.get(config_type)
   ```

   NOTE: Do NOT add a module-level `_registry = PluginRegistry()` singleton. RESEARCH.md recommends it, but D-10 says "exists and is wirable" — the class existing is sufficient for Phase 3. Phase 4 will decide the singleton strategy when it needs to wire appliers. Keeping Phase 3 clean of singletons avoids hard-to-test global state.

In tests/test_plugin.py, add PluginRegistry tests:
- Import PluginRegistry from rig.engine.plugin_registry
- Test empty registry returns None for any key
- Test register then get returns the registered plugin (use a simple lambda or stub object as the plugin — no need for a real DevicePlugin implementation)
- Test overwrite works (register same key twice, second wins)
- Test that the registry is empty when freshly instantiated (no module-level registrations happened)
  </action>
  <verify>
    <automated>uv run pytest tests/test_plugin.py tests/ -q 2>&1 | tail -15</automated>
  </verify>
  <done>tests/test_plugin.py passes all PluginContext and PluginRegistry tests. Full suite passes (167+ tests). plugin_registry.py has no module-level singleton and no registered appliers.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PluginRegistry.register | Accepts any object as a plugin — no validation in Phase 3 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03P4-01 | Tampering | PluginRegistry.register accepts arbitrary objects | accept | Phase 3 registry is internal/trusted; external plugin injection is Phase 4+ concern |
| T-03P4-02 | Information Disclosure | DevicePlugin Protocol methods return object | accept | Return type is intentionally broad in Phase 3; Phase 4 narrows to specific result types |
| T-03P4-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in Phase 3 |
</threat_model>

<verification>
Run full test suite to confirm new files integrate cleanly:

```
uv run pytest tests/ -q
```

Expected: 167+ tests pass (new plugin tests added on top of baseline).

Verify imports work without circular dependencies:
```
uv run python -c "
from rig.engine.plugin import DevicePlugin, PluginContext
from rig.engine.plugin_registry import PluginRegistry
import dataclasses
print('PluginContext fields:', [f.name for f in dataclasses.fields(PluginContext)])
r = PluginRegistry()
print('empty get:', r.get('manual'))
r.register('test', object())
print('registered get is not None:', r.get('test') is not None)
"
```
Expected: `PluginContext fields: ['state', 'rig', 'dry_run']`, `empty get: None`, `registered get is not None: True`
</verification>

<success_criteria>
- src/rig/engine/plugin.py exists with DevicePlugin (Protocol) and PluginContext (dataclass)
- PluginContext has exactly three fields: state (RigState), rig (Rig), dry_run (bool)
- DevicePlugin has plan, diff, apply methods; no ABC inheritance
- src/rig/engine/plugin_registry.py exists with PluginRegistry class
- PluginRegistry is empty by default; register() and get() work correctly
- No appliers registered at module level in plugin_registry.py
- tests/test_plugin.py covers all PluginContext and PluginRegistry behaviors
- Full suite: 167+ tests pass
</success_criteria>

<output>
Create `.planning/phases/03-core-domain-refactor/03-P4-SUMMARY.md` when done
</output>
