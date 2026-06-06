---
phase: 05-dependency-graph-plan-command
reviewed: 2026-06-06T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/rig/models/graph.py
  - src/rig/models/rig.py
  - src/rig/engine/plan/models.py
  - src/rig/engine/plan/compute.py
  - src/rig/engine/diff.py
  - src/rig/cli/commands/plan.py
  - src/rig/engine/apply.py
  - tests/test_graph.py
  - tests/test_plan.py
  - tests/test_apply.py
  - tests/test_cli_plan.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-06-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This phase delivered `DeviceGraph`, the `compute_plan` engine refactor, a new `plan` CLI command, and updated `apply_plan` orchestration. The domain logic in `graph.py`, `plan/models.py`, and `plan/compute.py` is generally sound. Two critical defects exist: unhandled `ConfigError` propagation in the `apply` CLI command, and a plan-status / missing-refs inconsistency that can cause `apply_plan` to silently do nothing when the rig config is broken. Four warnings cover weaker spots: the untyped `Rig.devices` field enabling silent `AttributeError` crashes, the double state-read per apply invocation, off-chain device ordering being non-deterministic, and signal-chain entries referencing non-existent devices being silently ignored.

---

## Critical Issues

### CR-01: `apply` CLI command does not catch `ConfigError` from `compute_plan`

**File:** `src/rig/cli/commands/apply.py:38`
**Issue:** `compute_plan` is called outside any `try/except` block. If `compute_plan` raises a `CycleError` (which is a `ConfigError`) — e.g., when the signal chain contains a duplicate device reference — the exception propagates as an unhandled Python traceback rather than a clean `[red]✗[/red]` error message. The `plan` command gets this right (lines 52–56 of `plan.py`), but `apply` does not.

**Fix:**
```python
# src/rig/cli/commands/apply.py
try:
    result = compute_plan(rig, root_path=config_path)
except ConfigError as e:
    console.print(f"[red]✗[/red] {e}")
    raise typer.Exit(1)
```

---

### CR-02: `missing_refs` does not set `plan.status = "changes_detected"` — `apply_plan` silently no-ops on broken configs

**File:** `src/rig/engine/plan/compute.py:215-223`
**Issue:** `_detect_missing_refs` and `_detect_unused_presets` populate fields on `Plan` but neither sets `any_changes = True`. If all scenes happen to be unchanged (state matches config) but the config has broken references (e.g., a scene references a device or preset that no longer exists), `plan.status` is `"clean"`. `apply_plan` short-circuits at line 69 of `apply.py` on `"clean"` status and returns `ApplyResult(status="no_changes")` without surfacing the broken references to the caller. The CLI `plan` command compensates by independently checking `result.missing_refs` for exit-code 2, but `apply_plan` itself — and any programmatic caller — gets silent misdirection.

**Fix:** Set `any_changes = True` when missing refs are detected so `plan.status` accurately reflects that the config is not in a valid/applied state:

```python
# src/rig/engine/plan/compute.py
missing_refs = _detect_missing_refs(rig)
unused_presets = _detect_unused_presets(rig)

if missing_refs:          # broken config → not "clean"
    any_changes = True

cba_setup = detect_cba_setup(rig, actual)
if cba_setup:
    any_changes = True
```

---

## Warnings

### WR-01: `Rig.devices: dict[str, Any]` allows non-`Device` objects that crash `Rig` properties at runtime

**File:** `src/rig/models/rig.py:21`
**Issue:** `devices` is typed `dict[str, Any]` to accommodate plugin device types (`MidiDevice`, `ChaseBlissDevice`) during the P3 migration. The `Rig` properties `digital_presets`, `hx_presets`, `analog_presets`, `_controller_device`, and `pedals` all access `device.presets`, `device.type`, or `device.config` on those values — attributes that are not guaranteed to exist on an arbitrary `Any` object. `DeviceGraph.apply_order` also does `device.type == DeviceType.CONTROLLER` over `Rig.devices.values()`. If any non-conforming object ends up in `devices`, the resulting `AttributeError` has no useful context. The plugin types (`AnalogDevice`, `MidiDevice`, etc.) all carry `id`, `type`, `config`, and `presets`, so in practice today this does not crash. But the type annotation erases that guarantee.

**Fix:** Narrow the annotation to a structural Protocol or a union type once the migration stabilises. As a minimum, add a Pydantic validator that checks each value has the required attributes, or use `dict[str, Device]` and rely on `model_config = ConfigDict(arbitrary_types_allowed=True)` which is already set.

---

### WR-02: `apply_plan` reads state twice per apply invocation — plan computed from potentially stale state

**File:** `src/rig/cli/commands/apply.py:38`, `src/rig/engine/apply.py:75-78`
**Issue:** The `apply` CLI command calls `compute_plan(rig, root_path=config_path)` (line 38 of `apply.py` CLI), which internally calls `read_state`. Then `apply_plan` calls `state_writer.read(config_path)` again (line 77 of `engine/apply.py`) for the state it uses during the apply loop. These are two independent reads. If another process (or the user) modifies `.rig/state.json` between the two reads, the plan was computed from state A but the apply loop executes against state B. For a single-user local CLI the risk is low, but more importantly, `apply_plan` is designed to accept a pre-computed plan; it should use the state snapshot that the plan was derived from, not re-read independently.

**Fix:** Pass the `RigState` object that `compute_plan` used into `apply_plan` (e.g., as a parameter), or have `apply_plan` skip its own state read when a pre-computed plan is provided and the state was already read by the caller. Alternatively, thread the `RigState` through via the `Plan` model.

---

### WR-03: Off-chain device ordering in `DeviceGraph.apply_order` is non-deterministic

**File:** `src/rig/models/graph.py:40-53`
**Issue:** Devices not in the signal chain are placed into `off_chain` by iterating `self._rig.devices.values()` (insertion order). No sort is applied to `off_chain` before building the result list. With two or more off-chain devices the apply order depends on dict insertion order, which varies with how the rig was loaded. This makes the apply order inconsistent across runs when devices are added or reordered in YAML files. The test at `test_off_chain_device_between_chain_and_controller` only exercises one off-chain device and cannot detect this.

**Fix:** Sort `off_chain` by a stable key such as `device.id` before appending:
```python
off_chain.sort(key=lambda d: d.id)
```

---

### WR-04: Signal-chain entries referencing non-existent devices are silently ignored

**File:** `src/rig/models/graph.py:36-51`
**Issue:** `chain_positions` is built from `self._rig.signal_chain` and can contain `device_ref` values that do not exist in `self._rig.devices`. The device loop (lines 43–49) only touches devices that *are* in `devices`, so a dangling `device_ref` in the signal chain is silently dropped — no warning, no error. `_detect_cycles` (lines 58–64) does not check whether each `device_ref` resolves to a real device. A typo in `signal-chain.yaml` will be invisible at plan time.

**Fix:** Add a validation pass in `_detect_cycles` (or a new `_detect_dangling_refs`) after cycle detection:
```python
for sc in self._rig.signal_chain:
    if sc.device_ref not in self._rig.devices:
        raise CycleError(
            f"Signal chain references unknown device '{sc.device_ref}'"
        )
```
(`CycleError` is already a `ConfigError`; rename to `SignalChainError` or reuse `MissingReferenceError` for precision.)

---

## Info

### IN-01: `test_cli_plan.py` test coverage does not exercise missing-refs or `--scene` filter paths

**File:** `tests/test_cli_plan.py`
**Issue:** The CLI smoke tests cover only exit-code 0 (clean), exit-code 2 (changes), cold-start warning, and summary line presence. There is no test for: `--scene <name>` filter, `--format json` output, scenes with broken references (which should exit 2 even when plan status is "clean"), or the `--show-unchanged` flag.

**Fix:** Add tests for the missing-refs exit-code path (a scene referencing a non-existent device should exit 2) and for `--scene` filtering, to prevent the CR-02 regression from going unnoticed.

---

### IN-02: Multiple `CONTROLLER` devices — only first is handled; rest silently become off-chain

**File:** `src/rig/models/graph.py:30-34`, `src/rig/models/rig.py:31-41`
**Issue:** Both `DeviceGraph.apply_order` and `Rig._controller_device` use `break`/`return` on the first `CONTROLLER`-typed device. A rig with two controllers results in the second being treated as an off-chain non-controller device with no warning. This is presumably not a supported configuration, but the code does not validate or document this constraint.

**Fix:** Add a guard that raises `ConfigError` (or `ValidationError`) when more than one `CONTROLLER` device is found, or document explicitly that only one controller is supported.

---

### IN-03: `# TODO: issue #13` marker in production code

**File:** `src/rig/engine/plan/compute.py:109`
**Issue:** `# TODO: issue #13` is left above the `compute_plan` function signature. Per project conventions (`CLAUDE.md`), TODO markers are acceptable for unresolved design questions, but this references a specific issue tracker number, making it harder to understand the intent without external context.

**Fix:** Replace with a self-contained comment describing *what* is deferred and *why*, or resolve the linked issue.

---

_Reviewed: 2026-06-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
