# Phase 20: Quick Wins — Dead Code - Research

**Researched:** 2026-06-12
**Domain:** Python codebase cleanup — dead method stubs, stale test infrastructure, raw string comparisons, TODO resolution
**Confidence:** HIGH

## Summary

Phase 20 is four independent cleanup tasks with zero production-logic risk. The codebase has been through a plugin-extraction refactor that left behind: (1) `plan()` and `diff()` methods in the Device Protocol and all four plugin implementations that raise `NotImplementedError` and are never called by the engine; (2) a stale root-level `tests/` directory whose 9 broken test files import from pre-plugin-extraction module paths that no longer exist, causing `make test` to fail with 9 collection errors; (3) three raw string device-type comparisons in engine and CLI code that should use the `DeviceType` StrEnum; (4) a TODO comment in `models/device.py` questioning the inconsistency between `Literal` and `DeviceType` usage, which is not actually inconsistent — they serve different purposes.

Each of the four tasks is a purely mechanical change. None of them touches business logic, state serialization, MIDI communication, or external-facing behavior. The only risk is test cleanup: removing `plan()`/`diff()` from implementations and the Protocol requires removing 8 tests from `packages/rig/tests/test_devices.py` and 4 related assertions from `packages/rig/tests/test_plugin.py` that verify these now-absent stubs.

**Primary recommendation:** Execute the four tasks in the order TYPE-04 → TEST-01 → QUAL-01 → QUAL-02. Each task is green in isolation; no inter-task dependencies.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Device Protocol definition | Engine (plugin.py) | — | Structural contract for all device plugins |
| Test infrastructure routing | pyproject.toml + Makefile | — | testpaths config determines which tests run |
| Device-type runtime comparisons | Engine (compute.py) | CLI (plan.py) | Plan computation and output formatting use device type |
| Model documentation | Models layer | — | TODO comment lives in models/device.py |

---

## TYPE-04: Dead `plan()` and `diff()` Stubs

### Confirmed locations — Protocol definition

**File:** `packages/rig/src/rig/engine/plugin.py`

Lines 142–144 (Protocol body — must be deleted):
```python
    def plan(self, ctx: PluginContext) -> object: ...

    def diff(self, ctx: PluginContext) -> object: ...
```

Lines 109–113 (docstring example code — must also be updated):
```python
            def plan(self, ctx: PluginContext) -> object:
                raise NotImplementedError

            def diff(self, ctx: PluginContext) -> object:
                raise NotImplementedError
```

Lines 19–24 (module-level docstring bullet — must be updated):
```
- **plan** / **diff** — currently raise ``NotImplementedError``; the plan
  command routes through ``rig.engine.plan.compute.compute_plan()`` and does
  not call these directly.
```

### Confirmed locations — Plugin implementations

All four implementations have identical 4-line stub blocks:

**`packages/rig-analog/src/rig_analog/device.py` lines 42–46:**
```python
    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError
```

**`packages/rig-hx/src/rig_hx/device.py` lines 58–62:**
```python
    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError
```

**`packages/rig-chasebliss/src/rig_chasebliss/device.py` lines 202–206:**
```python
    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError
```

**`packages/rig-morningstar/src/rig_morningstar/device.py` lines 39–43:**
```python
    def plan(self, ctx: PluginContext) -> object:
        raise NotImplementedError

    def diff(self, ctx: PluginContext) -> object:
        raise NotImplementedError
```

### PluginContext import becomes unused after removal

In all four plugin device files, `PluginContext` is imported alongside `DeviceApplyContext`, `SetupContext`, `SetupResult`. After removing the `plan()` and `diff()` methods, `PluginContext` is no longer referenced. The ruff linter enforces F401 (unused imports), so each import line must be updated.

**Before (same pattern in all 4 files):**
```python
from rig.engine.plugin import DeviceApplyContext, PluginContext, SetupContext, SetupResult
```

**After:**
```python
from rig.engine.plugin import DeviceApplyContext, SetupContext, SetupResult
```

### Verification: plan() and diff() are never called in production code

Confirmed by grep — `.plan(` and `.diff(` method calls on device objects appear **only** in test files:

- `packages/rig/tests/test_devices.py` lines 122, 131, 193, 202, 246, 255, 299, 308
- No production code calls these methods

The engine dispatches device work through `.apply(ctx)`, `.setup(ctx)`, and `.get_scene_pc_command(preset_id)` — never through `.plan()` or `.diff()`.

### Test cleanup required (TYPE-04 side effect)

Removing the stubs breaks 8 tests in `packages/rig/tests/test_devices.py` and 4 assertions/tests in `packages/rig/tests/test_plugin.py`. These tests must be deleted as part of TYPE-04.

**`packages/rig/tests/test_devices.py` — 8 tests to delete:**
- `test_analog_device_plan_raises_not_implemented` (line 116)
- `test_analog_device_diff_raises_not_implemented` (line 125)
- `test_midi_device_plan_raises_not_implemented` (line 187)
- `test_midi_device_diff_raises_not_implemented` (line 196)
- `test_chase_bliss_device_plan_raises_not_implemented` (line 240)
- `test_chase_bliss_device_diff_raises_not_implemented` (line 249)
- `test_mc6_device_plan_raises_not_implemented` (line 293)
- `test_mc6_device_diff_raises_not_implemented` (line 302)

**`packages/rig/tests/test_devices.py` line 389 — protocol check needs updating:**
```python
# Before:
for attr in ("id", "name", "config", "plan", "diff", "apply"):
# After:
for attr in ("id", "name", "config", "apply"):
```

**`packages/rig/tests/test_plugin.py` — tests/assertions to update:**

- `test_device_protocol_satisfied_by_class_with_all_members` (line 55): Remove `plan()` and `diff()` from `GoodDevice` inner class, remove `hasattr(device, "plan")` and `hasattr(device, "diff")` assertions.
- `test_device_protocol_missing_property_detected_via_hasattr` (line 89): Update comment, remove `not hasattr(device, "plan")` and `not hasattr(device, "diff")` assertions.
- `test_device_protocol_has_distinct_context_types` (line 110): Delete entire test (it accesses `Device.plan.__annotations__`).
- `test_discovery_placeholder_implements_device_protocol` (line 365): Remove `hasattr(device, "plan")` and `hasattr(device, "diff")` assertions.

---

## TEST-01: Stale Root `tests/` Directory

### What's in it and why it fails

The root `tests/` directory at `/Users/derekgliwa/dev/rig-cli/tests/` contains 19 items (18 Python files + `__init__.py`). These are copies of test files from the pre-plugin-extraction layout. After the plugin extraction refactor, modules they import from were moved, renamed, or removed.

**9 files fail collection with import errors:**

| File | Import Error |
|------|-------------|
| `test_appliers.py` | `ModuleNotFoundError: No module named 'rig.engine.appliers.chase_bliss'` |
| `test_apply.py` | `ModuleNotFoundError: No module named 'rig.engine.devices'` |
| `test_catalog.py` | `ModuleNotFoundError: No module named 'rig.catalog.chase_bliss'` |
| `test_diff.py` | `ImportError: cannot import name 'ChaseBlissConfig' from 'rig.models.device'` |
| `test_graph.py` | `ImportError: cannot import name 'ControllerConfig' from 'rig.models.device'` |
| `test_mc6_generator.py` | `ModuleNotFoundError: No module named 'rig.generators.mc6_presets'` |
| `test_mc6_sysex.py` | `ModuleNotFoundError: No module named 'rig.midi.mc6'` |
| `test_models.py` | `ModuleNotFoundError: No module named 'rig.models.controller'` |
| `test_plan.py` | `ImportError: cannot import name 'ChaseBlissConfig' from 'rig.models.device'` |

The remaining 9 files collect successfully but 76 of their 152 tests fail at runtime (stale fixture paths, changed model shapes, removed modules). None of the passing tests cover functionality not already covered in `packages/rig/tests/` — the packages tests are a superset.

**`test_mc6_generator.py` is notable:** it tests `rig.generators.mc6_presets.generate_mc6` which no longer exists anywhere in the codebase (`packages/rig/src/rig/generators/__init__.py` is empty). The MC6 apply behavior moved to `rig-morningstar` plugin's `MC6Device.apply()`.

### Current `make test` behavior

`make test` runs `uv run pytest tests/ -v` (hardcoded in `Makefile`). This hits the stale directory and **fails immediately** with 9 collection errors:

```
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 9 errors in 0.26s ===============================
make: *** [test] Error 2
```

### What to do

1. **Delete `tests/` directory entirely** — `rm -rf tests/`
2. **Update `Makefile` test target** — remove the explicit `tests/` path so pytest uses `testpaths = ["packages"]` from `pyproject.toml`

**Before:**
```makefile
test:              ## Run all tests
	uv run pytest tests/ -v
```

**After:**
```makefile
test:              ## Run all tests
	uv run pytest -v
```

### Nothing worth preserving

After exhaustive comparison, no test in root `tests/` covers functionality absent from `packages/rig/tests/`. The packages tests are newer and more comprehensive:

- `test_plugin.py` in packages has 7 additional tests (entry point discovery, reload, workspace)
- `test_loader.py` in packages has updated test names and 2 additional tests for new schema
- `test_mc6_generator.py` in root tests dead code that was deleted in the plugin refactor

---

## QUAL-01: Raw String Device-Type Comparisons

### All 3 occurrences in non-test source (confirmed by grep)

**Occurrence 1 — `packages/rig/src/rig/engine/plan/compute.py` line 88:**
```python
if pedal.type.value == "analog":
```
`pedal.type` is a `DeviceType` StrEnum. `.value` is redundant (StrEnum `==` str directly). Replace with enum member comparison.

**Occurrence 2 — `packages/rig/src/rig/cli/commands/plan.py` line 97:**
```python
if action.device_type == "analog":
```
`action.device_type` is typed as `str` on `DeviceAction`. This string is populated from `pedal.type.value` (compute.py line 117) and from the literal `"analog"` (compute.py line 92). The comparison should use `DeviceType.ANALOG`.

**Occurrence 3 — `packages/rig-hx/src/rig_hx/device.py` line 40:**
```python
if data.get("type") == "modeler":
```
`data` is a raw YAML dict; `data.get("type")` returns the string `"modeler"`. Since `DeviceType` is a `StrEnum`, comparing `DeviceType.MODELER == "modeler"` is `True`. Replace with enum member.

### Replacement expressions

| File | Line | Before | After |
|------|------|--------|-------|
| `engine/plan/compute.py` | 88 | `pedal.type.value == "analog"` | `pedal.type == DeviceType.ANALOG` |
| `cli/commands/plan.py` | 97 | `action.device_type == "analog"` | `action.device_type == DeviceType.ANALOG` |
| `rig-hx/device.py` | 40 | `data.get("type") == "modeler"` | `data.get("type") == DeviceType.MODELER` |

### Required import additions

`DeviceType` is **not currently imported** in `compute.py` or `plan.py`. It **is** already imported in `rig_hx/device.py` (line 14).

**`packages/rig/src/rig/engine/plan/compute.py` — add import:**
```python
from rig.models.device import DeviceType
```

**`packages/rig/src/rig/cli/commands/plan.py` — add import:**
```python
from rig.models.device import DeviceType
```

### Note on `device_type` field in `DeviceAction`

`DeviceAction.device_type` is currently typed as `str`. The comparison fix (`action.device_type == DeviceType.ANALOG`) works because StrEnum `==` str is symmetric. The planner may optionally change the field type to `DeviceType`, but this is not required by QUAL-01 and would cascade into test fixture updates. The minimal fix is the comparison-site change only.

### Note on `pedal.type.value` (compute.py line 117)

Line 117 in compute.py also uses `.value`:
```python
device_type=pedal.type.value,
```
This populates the `str`-typed `device_type` field on `DeviceAction`. Since the field is `str`, passing `pedal.type` (StrEnum) or `pedal.type.value` (str) both work. QUAL-01 only requires fixing `==` comparisons; line 117 is not a comparison. The planner may choose to clean up `.value` here for consistency but it is not required by the stated requirement.

### Also confirmed: no other raw string comparisons exist

The grep for `== "analog"`, `== "digital"`, `== "controller"`, `== "modeler"` in `packages/` source (non-test) returns **only** the three occurrences listed above.

---

## QUAL-02: Resolve the Enums-vs-Literals TODO

### Exact location

**File:** `packages/rig/src/rig/models/device.py` **line 11**

**Verbatim current text:**
```python
# TODO: we inconsistently use Enums and Literals. Pick one (whichever is the better python convention)
```

### Why both exist and why that is correct

**`DeviceType` StrEnum** (`models/device.py` lines 12–16) — used for **runtime comparisons** on `Device` objects. When the engine asks "is this pedal an analog device?", it compares `pedal.type == DeviceType.ANALOG`. StrEnum gives IDE completions, catches typos at definition time, and produces readable `repr()`.

**`Literal["chase_bliss"]` etc.** (e.g., `rig_chasebliss/device.py` line 33) — used as **Pydantic discriminated union type fields** on config models. Pydantic's discriminated union mechanism requires `Literal` types (not StrEnum) to identify which config subtype to instantiate. This is a Pydantic constraint, not a style choice.

These two mechanisms operate at **different layers**:
- `DeviceType` StrEnum operates on `Device` objects (the plugin model) — runtime comparison
- `Literal` operates on `DeviceConfig` objects (the config submodel) — Pydantic schema discrimination

They are not in conflict. A single device has both a `DeviceType` (what kind of device it is at runtime) and a config whose `type: Literal["chase_bliss"]` field tells Pydantic which config class to instantiate.

### Replacement comment text

```python
# DeviceType StrEnum is for runtime comparisons (engine, CLI, plan output).
# Config submodels use Literal type fields (e.g. Literal["chase_bliss"]) — Pydantic
# requires Literal for discriminated union dispatch. The two are orthogonal: StrEnum
# describes device kind; Literal identifies config schema. Both must coexist.
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dead import cleanup | Manual grep | ruff F401 | Ruff catches unused imports automatically after plan/diff removal |
| StrEnum string comparisons | Custom type guard | `DeviceType` StrEnum `==` | StrEnum `__eq__` handles plain string comparison on both sides |

---

## Risk Assessment

### "Zero cross-phase risk" — CONFIRMED with one caveat

**TYPE-04:** `plan()` and `diff()` are confirmed never called by production code. Only tests call them. The method removal is safe. The caveat: test cleanup is required in `packages/rig/tests/test_devices.py` (8 tests) and `packages/rig/tests/test_plugin.py` (4 tests/assertions). This is expected work, not a surprise.

**TEST-01:** The stale `tests/` directory has zero functional overlap with the authoritative `packages/` tests. Deleting it removes noise. The Makefile must be updated simultaneously — deleting `tests/` without fixing the Makefile would leave `make test` broken (pytest would error: path `tests/` does not exist).

**QUAL-01:** All three raw string comparisons are in non-performance-critical paths (plan computation and CLI output). StrEnum `==` string comparison is semantically identical to `.value ==` string comparison. No behavior changes.

**QUAL-02:** Replacing a comment with a better comment. Zero code behavior change.

### Pre-existing test failures (not caused by Phase 20)

Three tests in `packages/` currently fail before any Phase 20 changes:

```
FAILED packages/rig/tests/test_appliers.py::TestChaseBlissApplierSetup::test_build_preset_confirm_sends_ccs_and_updates_state
FAILED packages/rig/tests/test_apply.py::TestMidiApply::test_midi_connect_and_send
FAILED packages/rig/tests/test_apply.py::TestCbaApply::test_cba_channel_establishment_writes_state
```

These fail because they call `input()` during test capture (MIDI port prompt reads from stdin). These are pre-existing failures unrelated to Phase 20 — they must not be regressed further, but Phase 20 does not touch them.

---

## Current Test Baseline

### `make test` (current state — BROKEN)
```
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 9 errors in 0.26s ===============================
make: *** [test] Error 2
```

### `uv run pytest packages/ -q` (authoritative suite)
```
3 failed, 302 passed in 0.47s
```
305 tests collected. 3 pre-existing stdin-capture failures. 302 pass.

### Expected state after Phase 20

After deleting `tests/`, fixing `Makefile`, removing plan/diff stubs, and cleaning up their 12 test assertions:

- `make test` → `uv run pytest -v` → collects 305 tests from `packages/`
- 8 `*_plan_raises_not_implemented` and `*_diff_raises_not_implemented` tests deleted
- Net: ~289 tests collected (305 - 8 deleted + possibly some assertions removed from existing tests)
- 3 pre-existing stdin failures remain (not touched by Phase 20)
- Expected: `3 failed, ~289 passed`

---

## Common Pitfalls

### Pitfall 1: Forgetting to remove the PluginContext import
**What goes wrong:** After removing `plan()` and `diff()` from plugin device files, `PluginContext` becomes an unused import. Ruff F401 will flag it, and `make lint` will fail.
**How to avoid:** Update the import line in all 4 plugin device files simultaneously with the method deletion.

### Pitfall 2: Deleting `tests/` without updating the Makefile
**What goes wrong:** `make test` runs `uv run pytest tests/ -v`; with `tests/` deleted, pytest errors with "no such directory".
**How to avoid:** Update `Makefile` `test` target in the same commit as the `tests/` deletion.

### Pitfall 3: Leaving plan/diff in the docstring example
**What goes wrong:** The docstring in `plugin.py` (lines 93–124) shows a `MyDevice` example class with `plan()` and `diff()`. If the Protocol methods are removed but the example is not updated, the docstring shows a pattern that no longer matches the Protocol contract.
**How to avoid:** Update the example class in the docstring to remove `plan()` and `diff()` alongside Protocol definition removal. Update the module-level bullet list (lines 21–23) similarly.

### Pitfall 4: test_plugin.py line 114 accessing Device.plan annotations
**What goes wrong:** `test_device_protocol_has_distinct_context_types` accesses `Device.plan.__annotations__` directly on the Protocol class. After removing `plan` from the Protocol, this raises `AttributeError`.
**How to avoid:** Delete this test entirely as part of TYPE-04.

### Pitfall 5: test_devices.py line 389 structural check still includes "plan" and "diff"
**What goes wrong:** `test_all_device_types_satisfy_device_protocol_structurally` checks all four device classes for `("id", "name", "config", "plan", "diff", "apply")`. After removal, this test fails with `AssertionError: AnalogDevice missing 'plan'`.
**How to avoid:** Update the attribute tuple to `("id", "name", "config", "apply")` as part of TYPE-04.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/ -q` |
| Full suite command | `uv run pytest -v` (after Makefile fix) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TYPE-04 | `plan()`/`diff()` absent from Protocol | unit | `uv run pytest packages/rig/tests/test_plugin.py -q` | Yes |
| TYPE-04 | `plan()`/`diff()` absent from all implementations | unit | `uv run pytest packages/rig/tests/test_devices.py -q` | Yes |
| TEST-01 | `make test` completes with no collection errors | integration | `make test` | Yes (after fix) |
| QUAL-01 | grep returns zero hits | manual grep | `grep -rn '"analog"\|"digital"\|"controller"\|"modeler"' packages/rig/src packages/rig-*/src` | N/A |
| QUAL-02 | TODO replaced with inline explanation | manual review | read `packages/rig/src/rig/models/device.py` | Yes |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/ -q`
- **Per wave merge:** `uv run pytest -v` (after Makefile fixed)
- **Phase gate:** Full suite green (3 pre-existing failures acceptable, no new failures)

---

## Security Domain

This phase makes no changes to authentication, input handling, MIDI message construction, file I/O, or any security-relevant paths. No ASVS categories apply.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — pure source code changes)

---

## Runtime State Inventory

Step 2.5: SKIPPED (not a rename/refactor phase — no stored state, registered services, or OS-level registrations are affected by removing dead method stubs)

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection via grep, Read, and Bash — all findings confirmed from actual source files

### Metadata

**Confidence breakdown:**
- TYPE-04 locations: HIGH — every file/line confirmed by Read and grep
- TEST-01 errors: HIGH — run `uv run pytest tests/ -q` and captured all 9 error messages
- QUAL-01 occurrences: HIGH — confirmed by grep with zero false positives
- QUAL-02 TODO text: HIGH — verbatim from `models/device.py` line 11

**Research date:** 2026-06-12
**Valid until:** Until next plugin package change (stable — 30 days)
