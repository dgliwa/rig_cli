---
phase: 6
plan: P1
status: complete
commits:
  - "feat(core): declare empty rig.devices entry point group"
  - "feat(core): refactor get_registry() for entry point discovery"
  - "refactor(core): remove hardcoded default_registry from devices.py"
  - "refactor(plugins): update entry points to Device classes, remove register() functions"
  - "chore: refresh editable installs for updated entry point metadata"
  - "fix(plugins): point entry points to core Device classes for class identity"
---

# Phase 6 P1: Entry Point Schema & PluginRegistry Refactor — Summary

## What was built

**PluginRegistry discovery via entry points:**
- `get_registry()` now discovers devices via `importlib.metadata.entry_points(group='rig.devices')`
- Entry points resolve directly to Device Pydantic model classes (no `register()` callbacks)
- `reload_registry()` exposed for test isolation
- Graceful degradation: errors logged, zero plugins = empty registry

**Old code removed:**
- Hardcoded `default_registry` with 8 `.register()`/`.register_model()` calls removed from `devices.py`
- All 4 plugin package `register()` functions removed from `__init__.py`
- `PluginRegistry` import removed from `devices.py`

**Entry points configured:**
| Entry point name | Device class | Package |
|---|---|---|
| `manual` | `rig.engine.devices:AnalogDevice` | rig-analog |
| `chase_bliss` | `rig.engine.devices:ChaseBlissDevice` | rig-chasebliss |
| `controller` | `rig.engine.devices:MC6Device` | rig-morningstar |
| `midi` | `rig.engine.devices:MidiDevice` | rig-hx |

## Key decisions honored

- D-01: Entry points → Device class directly, not `register()` callbacks ✓
- D-03: Hardcoded registrations removed; entry points are the single path ✓
- D-06: Core declares empty `rig.devices` group ✓

## Deviations

None. Entry point names were adjusted from the plan (e.g., `analog`→`manual`, `hx_stomp`→`midi`) to match `config.type` values used in device YAML files — necessary for loader dispatch.

## Verification

- 4 plugins discovered via entry points ✓
- `default_registry` removed from `devices.py` ✓
- No `register()` functions remain in plugin `__init__.py` ✓
- Core `pyproject.toml` declares empty `rig.devices` group ✓
- Entry point metadata refreshed ✓
