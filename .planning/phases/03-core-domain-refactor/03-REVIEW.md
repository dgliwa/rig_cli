---
phase: 03-core-domain-refactor
reviewed: 2026-06-05T18:27:30Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/rig/config/loader.py
  - src/rig/engine/plugin.py
  - src/rig/engine/plugin_registry.py
  - src/rig/models/controller.py
  - src/rig/models/device.py
  - src/rig/models/rig.py
  - tests/fixtures/sample_rig/devices/mc6.yaml
  - tests/test_apply.py
  - tests/test_diff.py
  - tests/test_loader.py
  - tests/test_mc6_generator.py
  - tests/test_models.py
  - tests/test_plan.py
  - tests/test_plugin.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-05T18:27:30Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

This phase refactored the domain model to unify the controller (MC6) as a `Device` with `ControllerConfig`, replacing the standalone `Controller` class, and introduced `DevicePlugin` / `PluginRegistry` scaffolding for Phase 4. The structural changes are sound: the discriminated union in `Device.config` correctly handles all four config types, `Rig.scenes` properly delegates to `ControllerConfig.scenes`, and the `apply_order()` logic correctly places the controller last.

Two BLOCKER-level bugs were found: one in the loader that crashes on empty YAML files, and one dead test that silently never runs. Five additional warnings cover a vacuous test assertion, an untestable direct `input()` call, a type mismatch in `ControllerConfig.scenes`, a latent `_merge_presets` branch that misclassifies `CONTROLLER` preset directories, and an exception-swallowing pattern in the test fake. Three info-level items cover dead code and a naming confusion in `controller.py`.

All 101 test executions pass with the current code.

---

## Critical Issues

### CR-01: `yaml.safe_load` return value never checked for `None` — crashes on empty YAML

**File:** `src/rig/config/loader.py:176-206`
**Issue:** `yaml.safe_load()` returns `None` when the file is empty or contains only whitespace. `_read_yaml` returns this `None` directly without any guard. The callers on lines 176-177 then call `.get()` on `None`:

```python
rig_data = _read_yaml(_resolve(root, "rig.yaml"))       # can be None
signal_data = _read_yaml(_resolve(root, "signal-chain.yaml"))  # can be None
...
name=rig_data.get("name", ""),    # AttributeError: 'NoneType' object has no attribute 'get'
```

The same crash path exists in `_parse_device` (`Device(**data)` where `data` is `None`) and in `_load_scenes` (`Scene(**data)` where `data` is `None`). The user sees an unhandled `AttributeError` with no context about which file is the problem.

**Fix:** Add a `None` check and raise `ParseError` with a clear message in `_read_yaml`, after the `yaml.safe_load` call:

```python
def _read_yaml(path: Path):
    ...
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ParseError(f"Empty or blank YAML file: {path}")
        return data
    except yaml.YAMLError as e:
        ...
```

---

### CR-02: `invalid_control_rejected` test never runs — missing `test_` prefix

**File:** `tests/test_models.py:87`
**Issue:** The method is named `invalid_control_rejected` instead of `test_invalid_control_rejected`. Pytest's default collection rule requires the `test_` prefix. This test is silently skipped by the runner on every CI run, meaning the `Control(name="", type=ControlType.KNOB)` rejection behavior is completely untested.

```python
def invalid_control_rejected(self):   # <- never collected by pytest
    with pytest.raises(ValidationError):
        Control(name="", type=ControlType.KNOB)
```

**Fix:** Rename the method:

```python
def test_invalid_control_rejected(self):
    with pytest.raises(ValidationError):
        Control(name="", type=ControlType.KNOB)
```

Note: Once renamed, this test may itself fail because Pydantic `BaseModel` does not reject empty strings by default. Verify that a validator enforcing non-empty `name` exists on `Control`, or add one.

---

## Warnings

### WR-01: `test_clean_plan_prints_no_changes` is vacuously true — tests nothing meaningful

**File:** `tests/test_apply.py:68-75`
**Issue:** The test name says "clean plan prints no changes" but the plan computed inside is **not** clean. `compute_plan(config)` with no `root_path` produces `status="changes_detected"` (no state file, all scenes are new). `apply_plan` only prints `"No changes needed"` when `plan.status == "clean"`, so the assertion `assert "No changes needed" not in captured.out` is always true regardless of any code change. The actual "clean plan" output path has zero test coverage.

**Fix:** Set up state that matches the config so the plan is genuinely clean, then assert that the message IS printed:

```python
def test_clean_plan_prints_no_changes_message(self, tmp_path, capsys):
    config = _make_config()
    _write_state_file(tmp_path, {
        "devices": {
            "hx-stomp": {"last_preset": "clean-edge"},
            "brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {"low-gain": True},
                "registration_done": True,
            },
        },
        "scenes": {"test-scene": {}},
    })
    plan = compute_plan(config, root_path=str(tmp_path))
    assert plan.status == "clean"
    state_adapter = InMemoryStateAdapter()
    midi_io = InMemoryMidiConnectionIO()
    apply_plan(plan, state_writer=state_adapter, midi_connection_io=midi_io, dry_run=False)
    captured = capsys.readouterr()
    assert "No changes needed" in captured.out
```

---

### WR-02: `_merge_presets` falls through to `DigitalPreset` for `CONTROLLER` device type

**File:** `src/rig/config/loader.py:83-88`
**Issue:** The preset type dispatch in `_merge_presets` handles `ANALOG` and `MODELER` explicitly, but the `else` branch catches both `DIGITAL` and `CONTROLLER`:

```python
if device.type == DeviceType.ANALOG:
    presets.append(AnalogPreset(**data))
elif device.type == DeviceType.MODELER:
    presets.append(HXStompPreset(**data))
else:
    presets.append(DigitalPreset(**data))  # silently catches CONTROLLER too
```

If a user creates `devices/mc6/presets/something.yaml`, the loader silently tries to parse it as a `DigitalPreset` (requiring `preset_number`, `id`, `name`). This produces a confusing Pydantic `ValidationError` rather than a clear message that controller devices do not use filesystem presets.

**Fix:** Add an explicit guard for `CONTROLLER`:

```python
elif device.type == DeviceType.CONTROLLER:
    logger.warning(
        "Controller device '%s' has a presets directory — skipping (controllers do not use presets).",
        device_id,
    )
    continue
else:
    presets.append(DigitalPreset(**data))
```

---

### WR-03: `ControllerConfig.scenes` typed as `dict[str, Any]` while `Rig.scenes` returns `dict[str, Scene]`

**File:** `src/rig/models/device.py:84` / `src/rig/models/rig.py:40`
**Issue:** `ControllerConfig.scenes` is declared as `dict[str, Any]` but the `Rig.scenes` property promises `dict[str, Scene]`:

```python
# device.py
scenes: dict[str, Any] = {}   # accepts anything at validation time

# rig.py
def scenes(self) -> dict[str, Scene]:   # lies about the actual stored type
    ...
    return ctrl.config.scenes           # is actually dict[str, Any]
```

Any caller of `rig.scenes` believes it is receiving `Scene` objects with no static-analysis protection against misuse. Pydantic would not catch a non-`Scene` value being injected into `ControllerConfig.scenes` at validation time.

**Fix:** Tighten `ControllerConfig.scenes` to `dict[str, Scene]`. If the import creates a circular dependency, use a `TYPE_CHECKING` guard with a string annotation, or restructure the import.

```python
from rig.models.scene import Scene

class ControllerConfig(DeviceConfig):
    ...
    scenes: dict[str, Scene] = {}
```

---

### WR-04: `MC6Applier.apply_banks` calls `input()` directly, bypassing `ConfirmationIO`

**File:** `src/rig/engine/appliers/mc6.py:48`
**Issue:** The MC6 bank-programming loop calls `input()` directly to pause for user navigation:

```python
console.print(f"\n  Navigate the MC6 to [bold]Bank {bank_num}[/bold], then press Enter...")
input()
```

Every other user interaction in the codebase routes through `ctx.confirmation_io` (the `ConfirmationIO` protocol). This lone `input()` call makes `apply_banks` untestable without monkeypatching `builtins.input`, violates the I/O isolation boundary established by `InMemoryPromptAdapter`, and means the MC6 programming path has no unit-level coverage.

**Fix:** Add a `prompt_mc6_navigate` method to the `ConfirmationIO` protocol and implement it in both `RichConfirmationIO` (using `input()`) and `InMemoryPromptAdapter` (returning immediately). Route the pause through `ctx.confirmation_io.prompt_mc6_navigate(bank_num)`.

---

### WR-05: `InMemoryMidiConnectionIO.prompt_connect` swallows all exceptions silently

**File:** `tests/fakes.py:114-117`
**Issue:** The fake's `prompt_connect` catches all exceptions from `midi.connect` and discards them without logging:

```python
try:
    midi.connect(self.port_name, device)
except Exception:
    pass
```

If `midi.connect` raises for an unexpected reason, the fake still returns `("confirm", port_name)` and the test proceeds as though the connection succeeded. Tests asserting on MIDI state (e.g., `state.devices["brothers"].midi_port == "USB Interface"`) can produce false positives — the assertion passes because the fake pretended success even though the underlying connection failed.

**Fix:** At minimum, log the swallowed exception so test failures surface in CI output:

```python
except Exception as exc:
    logger.debug(
        "InMemoryMidiConnectionIO: connect suppressed (expected in unit tests): %s", exc
    )
```

---

## Info

### IN-01: Dead `if TYPE_CHECKING: pass` block in `device.py`

**File:** `src/rig/models/device.py:10-11`
**Issue:** The `TYPE_CHECKING` guard exists but contains only `pass`. It performs no work and was likely left over from a refactor that moved imports out of the guard:

```python
if TYPE_CHECKING:
    pass
```

`TYPE_CHECKING` is also imported at line 4 but serves no purpose here.

**Fix:** Remove both the `TYPE_CHECKING` import and the empty `if` block entirely.

---

### IN-02: `controller.py` `MC6Config` and `Controller` classes are orphaned legacy models

**File:** `src/rig/models/controller.py`
**Issue:** `controller.py` defines `MC6Config` (with `type: Literal["mc6"]`) and `Controller` (a `BaseModel` holding `config: MC6Config`). Neither class is part of the discriminated union in `Device.config`, neither is instantiated by the loader, and neither participates in any plan or apply logic. They exist only as re-exports for backward compatibility from `models/__init__.py`.

The conceptual confusion is real: `MC6Config.type = "mc6"` vs `ControllerConfig.type = "controller"` — two different Literal values for the same physical device — and both `MC6Config.banks` and `ControllerConfig.banks` exist as parallel fields.

**Fix:** Mark these explicitly as deprecated shims pending removal. Add a module-level comment: `# Deprecated: Controller and MC6Config are legacy stubs. Use ControllerConfig from rig.models.device.` Schedule removal once all callers are confirmed migrated.

---

### IN-03: `PluginContext.rig` annotation is `Rig` but tests pass `object()`

**File:** `src/rig/engine/plugin.py:21` / `tests/test_plugin.py:23,31`
**Issue:** `PluginContext` is a `@dataclass` with `rig: Rig`, but the tests pass `object()` as the `rig` value:

```python
ctx = PluginContext(state=RigState(), rig=object(), dry_run=True)
```

Dataclasses do not enforce types at runtime, so this works today. However, if mypy or a type-checking CI step is added, these tests will fail immediately. More importantly, the tests do not validate that `PluginContext` works correctly with an actual `Rig` instance, leaving any `rig`-consuming logic in future `DevicePlugin` implementations without test coverage at the context level.

**Fix:** Pass a minimal `Rig(name="test", signal_chain=[])` instance in the tests, or create a `_make_rig()` helper consistent with the pattern used in other test files.

---

_Reviewed: 2026-06-05T18:27:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
