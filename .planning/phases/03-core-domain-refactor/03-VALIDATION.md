---
phase: 3
slug: core-domain-refactor
status: compliant
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-06
---

# Phase 3 — Nyquist Validation Strategy

Per-phase validation contract for **core-domain-refactor**: Controller-as-Device model, Rig device-graph, loader cleanup, and DevicePlugin Protocol.

---

## Test Infrastructure

| Tool | Config | Command |
|------|--------|---------|
| pytest | `pyproject.toml` | `uv run pytest tests/ -q` |
| ruff | `pyproject.toml` | `uv run ruff check src/` |

**Baseline at phase start:** 180 tests
**At phase close:** 274 tests (+94 across all plans)

---

## Per-Task Requirement Map

### P1 — Controller-as-Device Model

| ID | Requirement | Test File | Test Name | Status |
|----|-------------|-----------|-----------|--------|
| P1-R1 | `DeviceType.CONTROLLER` exists with value `'controller'` | `tests/test_models.py` | `TestControllerConfig::test_device_type_controller_value` | COVERED |
| P1-R2 | `ControllerConfig` parses via `DeviceConfig` discriminated union | `tests/test_models.py` | `TestControllerConfig` class | COVERED |
| P1-R3 | `Device` with `type=controller` round-trips through Pydantic | `tests/test_models.py` | `test_controller_config_round_trips_via_discriminated_union` | COVERED |
| P1-R4 | `controller.py` re-exports `ControllerType`, `MC6Config`, `Controller` | `tests/test_models.py` | backward-compat import assertions | COVERED |
| P1-R5 | Sample fixture `devices/mc6.yaml` has `type: controller` | `tests/fixtures/sample_rig/devices/mc6.yaml` | fixture exists, used by test_loader | COVERED |

**Run:** `uv run pytest tests/test_models.py -k "Controller" -v`

---

### P2 — Rig Device-Graph Model and `apply_order()`

| ID | Requirement | Test File | Test Name | Status |
|----|-------------|-----------|-----------|--------|
| P2-R1 | `Rig` has no `controller` or `scenes` Pydantic fields | `tests/test_models.py` | `TestRigConfig::test_rig_controller_and_scenes_are_not_pydantic_fields` | COVERED |
| P2-R2 | `Rig.scenes` property returns scenes from `ControllerConfig` | `tests/test_models.py` | `test_rig_scenes_returns_controller_config_scenes` | COVERED |
| P2-R3 | `Rig.controller` returns `Device(type=CONTROLLER)` or `None` | `tests/test_models.py` | `test_rig_controller_returns_none_when_absent`, `test_rig_controller_returns_controller_device` | COVERED |
| P2-R4 | `apply_order()` returns controller last | `tests/test_models.py` | `TestApplyOrder::test_apply_order_controller_comes_last` | COVERED |
| P2-R5 | `apply_order()` with no controller sorted by signal-chain position | `tests/test_models.py` | `TestApplyOrder::test_apply_order_no_controller_returns_devices_by_position` | COVERED |
| P2-R6 | All existing tests pass after `_make_rig()` update | `tests/test_mc6_generator.py` | full suite | COVERED |

**Run:** `uv run pytest tests/test_models.py::TestRigConfig tests/test_models.py::TestApplyOrder -v`

---

### P3 — Loader Cleanup

| ID | Requirement | Test File | Test Name | Status |
|----|-------------|-----------|-----------|--------|
| P3-R1 | Loader routes `type: controller` YAML through `_parse_device` | `tests/test_loader.py` | `test_loads_controller_as_device` | COVERED |
| P3-R2 | `load_rig()` injects scenes into `ControllerConfig` after load | `tests/test_loader.py` | `test_scenes_accessible_via_controller` | COVERED |
| P3-R3 | `rig.scenes` works via compat shim after `load_rig()` | `tests/test_loader.py` | `test_scenes_accessible_via_controller` (line 188) | COVERED |
| P3-R4 | `_parse_controller_legacy` is removed | `src/rig/config/loader.py` | grep confirms absence; all loader tests pass | COVERED |
| P3-R5 | All existing loader tests pass | `tests/test_loader.py` | full loader test class | COVERED |

**Run:** `uv run pytest tests/test_loader.py -v`

---

### P4 — DevicePlugin Protocol + PluginRegistry

| ID | Requirement | Test File | Test Name | Status |
|----|-------------|-----------|-----------|--------|
| P4-R1 | `Device` Protocol class exists (renamed from `DevicePlugin`) | `tests/test_plugin.py` | protocol existence + `DevicePlugin` absence assertion | COVERED |
| P4-R2 | `PluginContext` is a dataclass with exactly `state`, `rig`, `dry_run` | `tests/test_plugin.py` | `test_plugin_context_is_dataclass`, `test_plugin_context_fields` | COVERED |
| P4-R3 | `PluginRegistry.register()` and `get()` work correctly | `tests/test_plugin.py` | `test_registry_register_and_get` | COVERED |
| P4-R4 | `PluginRegistry.get()` returns `None` for unregistered types | `tests/test_plugin.py` | `test_registry_get_unregistered_returns_none` | COVERED |
| P4-R5 | No appliers registered in Phase 3 (empty registry at import) | `tests/test_plugin.py` | empty registry assertions (lines 209–212) | COVERED |
| P4-R6 | `from __future__ import annotations` + `TYPE_CHECKING` guard | `src/rig/engine/plugin.py`, `plugin_registry.py` | verified by import checks in test suite | COVERED |

**Run:** `uv run pytest tests/test_plugin.py -v`

---

## Full-Suite Sign-Off

```
uv run pytest tests/ -q
# 274 passed (as of 2026-06-06)
```

All requirements across P1–P4 have automated verification. Phase 3 is **Nyquist-compliant**.

---

## Validation Audit 2026-06-06

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Gap resolved:** Added `test_rig_controller_and_scenes_are_not_pydantic_fields` to `tests/test_models.py::TestRigConfig` — asserts `"controller" not in Rig.model_fields` and `"scenes" not in Rig.model_fields`.
