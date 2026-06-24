# Phase 33.1: Apply-01/02 Completions - Research

**Researched:** 2026-06-24
**Domain:** Python CLI apply engine — analog device skip display + device-filter cross-scene apply
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- APPLY-01: `rig apply` with an analog device whose state matches the scene preset skips the manual prompt
- APPLY-02: `rig apply --device <id>` applies that device's preset for every scene in the plan without touching other devices
- Tests must use `InMemoryPromptAdapter` and `InMemoryStateAdapter` (no real MIDI, no disk I/O)
- No new CLI flags or options beyond what's required
- APPLY-02 must NOT touch other devices' state
- Python 3.12+, Pydantic BaseModel, conventional commits format

### Claude's Discretion
- Whether to implement APPLY-02 via a `device_filter` param on `apply_plan()` or a new `apply_device_scenes()` function
- Exact console output string for the APPLY-01 VERIFY branch

### Deferred Ideas (OUT OF SCOPE)
- MC6 state write-back bug (`controller.apply()` result discarded in `apply_plan:184`)
- Catalog-constants-in-tests-only warning
</user_constraints>

---

## Summary

Phase 33.1 completes two apply-engine behaviors. Both were partially designed in prior phases but neither is fully shipped.

**APPLY-01** has all mechanical wiring in place. `compute.py:122` correctly assigns `ActionStatus.VERIFY` when `actual_preset == preset_id` for analog devices. `apply.py:115-119` already has the VERIFY guard that bypasses `device.apply()` and returns a skipped `DeviceApplyResult`. The two gaps are: (a) no console output in the VERIFY branch — the user sees nothing when a device is already set, and (b) the existing test `TestVerifyActionSkipped.test_verify_action_does_not_call_device_apply` only asserts that `AnalogDevice.apply()` is not called — it does not assert that console output was printed. Adding a console.print and a focused output-assertion test closes the gap.

**APPLY-02** is not implemented at all. The CLI guard at `apply.py:44-46` (`bool(device) != bool(preset)`) unconditionally rejects `--device` without `--preset`. The engine has no function that filters a full plan by device ID across all scenes. The cleanest implementation is a `device_filter: str | None = None` parameter on `apply_plan()` — filter inside the existing scene loop rather than adding a new top-level function. This reuses all existing setup, state, and controller phases without duplication.

**Primary recommendation:** Add `console.print` in the VERIFY branch of `apply.py`, add `device_filter` param to `apply_plan()`, update the CLI guard, add two focused test classes.

---

## Project Constraints (from CLAUDE.md)

| Directive | Category |
|-----------|----------|
| Protocol-first: new abstractions use `Protocol` classes, not ABC | Architecture |
| Pydantic `BaseModel` for all domain data | Models |
| `from __future__ import annotations` in all modules | Language |
| `snake_case.py` for source files, `PascalCase` for classes | Naming |
| `type \| None` union syntax (Python 3.10+ style) | Types |
| Test helpers named `_make_*`, test doubles in `tests/fakes.py` | Testing |
| No real MIDI hardware in tests — use `InMemoryPromptAdapter` | Testing |
| `make test` / `uv run pytest tests/ -v` | CI |
| `ruff check` + `ruff format`, line length 100 | Style |
| `type(scope): description` commit format | Commits |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| VERIFY skip + display | Engine (`apply.py`) | — | `apply.py` owns all device-action dispatch; display belongs here |
| VERIFY status assignment | Plan engine (`compute.py`) | — | Already correct; no change needed |
| Cross-scene device filter | Engine (`apply.py`) | — | Filter logic belongs in the loop that iterates scenes |
| CLI guard change (APPLY-02) | CLI (`commands/apply.py`) | — | Only CLI layer knows which arg combination is legal |
| Test infrastructure | `tests/test_apply.py` | `tests/test_cli_apply.py` | APPLY-01 E2E in test_apply; APPLY-02 CLI in test_cli_apply |

---

## Standard Stack

No new packages. All implementation uses existing dependencies. [ASSUMED]

### Existing Relevant APIs

| Symbol | Location | Used by |
|--------|----------|---------|
| `ActionStatus.VERIFY` | `rig.engine.plan.models` | APPLY-01 guard in apply.py:115 |
| `ActionStatus.ANALOG` | `rig.engine.plan.models` | Normal analog action path |
| `DeviceApplyResult(status="skipped")` | `rig.engine.plugin` | VERIFY branch return value |
| `console.print(...)` | `rich.console.Console` (module-level in apply.py) | APPLY-01 display |
| `InMemoryPromptAdapter` | `tests/fakes.py` | Test assertion on prompt calls |
| `InMemoryStateAdapter` | `tests/fakes.py` | Test assertion on state writes |
| `_write_state_file(tmp_path, data)` | `tests/test_apply.py` | Pre-populate state.json for VERIFY precondition |
| `AnalogDevice` | `rig_analog.device` | Used in existing TestVerifyActionSkipped |
| `AnalogPreset` | `rig_analog.preset` | Used in existing TestVerifyActionSkipped |
| `FakeDevice` | `tests/conftest.py` | Controller stub in test rigs |

---

## Architecture Patterns

### Recommended Project Structure

No structural changes. All work fits into existing files:

```
packages/rig/src/rig/engine/
  apply.py              # VERIFY branch display (APPLY-01) + device_filter param (APPLY-02)
packages/rig/src/rig/cli/commands/
  apply.py              # CLI guard change + new device-only routing branch (APPLY-02)
packages/rig/tests/
  test_apply.py         # APPLY-01 E2E display test + APPLY-02 engine-level tests
  test_cli_apply.py     # APPLY-02 CLI routing tests + guard update tests
```

### Pattern 1: VERIFY Branch Display (APPLY-01)

**What:** Add a single `console.print` in the existing VERIFY guard inside `apply_plan()`.

**When to use:** Any time `action.status == ActionStatus.VERIFY` — applies to both analog devices (ANALOG status when state matches) and non-analog devices (VERIFY status when state matches).

**Current code (apply.py:115-119):**
```python
if action.status == ActionStatus.VERIFY:
    logger.debug("Device '%s': preset already correct — skipping apply", action.device)
    action_result = DeviceApplyResult(
        device=action.device, status="skipped", preset=action.preset_name
    )
```

**After change:**
```python
if action.status == ActionStatus.VERIFY:
    logger.debug("Device '%s': preset already correct — skipping apply", action.device)
    console.print(
        f"  [green]✓[/green] {action.device}: already set to '{action.preset_name}'"
    )
    action_result = DeviceApplyResult(
        device=action.device, status="skipped", preset=action.preset_name
    )
```

Source: direct code read of `packages/rig/src/rig/engine/apply.py`. [ASSUMED — pattern follows existing `console.print` style in apply.py]

### Pattern 2: device_filter Parameter (APPLY-02)

**What:** Add `device_filter: str | None = None` to `apply_plan()`. Inside the per-scene device-action loop, skip any action whose `action.device != device_filter` when the filter is set.

**Why `device_filter` on `apply_plan()` rather than a new function:**
- `apply_plan()` already handles setup, state read, controller programming, and state write — duplicating any of these in a new function creates drift risk.
- The filter is a one-line conditional inside the inner loop; no structural change to the function needed.
- Test setup for APPLY-02 can use the exact same `InMemoryStateAdapter` + `InMemoryPromptAdapter` patterns as existing tests.
- A new function would require either duplicating or delegating to `apply_plan()` — delegation is equivalent to a param; a new function adds surface area with no gain. [ASSUMED — architectural judgment based on codebase read]

**Inner loop change:**
```python
for action in sp.device_actions:
    # APPLY-02: skip actions not targeting the filtered device
    if device_filter and action.device != device_filter:
        continue
    device = rig.devices.get(action.device) if rig else None
    ...
```

**State write scope for APPLY-02:** The existing `state.scenes[sp.scene_name] = {}` write at line 151-153 is guarded by `any(r.status == "confirmed" for r in device_results)`. With `device_filter`, only the filtered device's results are in `device_results`, so `state.scenes` update only fires if the filtered device was confirmed — correct behavior. No extra state-scoping logic required.

**Controller programming phase for APPLY-02:** The controller phase at line 164 (`if rig and rig.controller and not scene:`) must NOT run when `device_filter` is set. Add `and not device_filter` to the condition, or skip the phase entirely when filtering. The cleanest approach:
```python
if rig and rig.controller and not scene and not device_filter:
```

### Pattern 3: CLI Guard Change (APPLY-02)

**What:** Replace the symmetric guard (both or neither) with a three-way routing branch.

**Current guard (cli/commands/apply.py:43-46):**
```python
# D-05: --device and --preset must be used together
if bool(device) != bool(preset):
    console.print("[red]✗[/red] --device and --preset must be used together")
    raise typer.Exit(1)
```

**After change — remove D-05 guard entirely, update D-06 validation and routing:**
```python
# D-05 removed: --device without --preset now valid (cross-scene apply)
# D-06: existence validation only when --preset is given
if device and preset:
    if device not in rig.devices:
        ...
    target_device = rig.devices[device]
    if not any(p.id == preset for p in target_device.presets):
        ...
elif device and not preset:
    # Validate device exists
    if device not in rig.devices:
        console.print(f"[red]✗[/red] Device '{device}' not found in rig config")
        raise typer.Exit(1)
```

**Routing block:**
```python
if device and preset:
    apply_device_preset(...)
elif device:
    result = compute_plan(rig, root_path=config_path)
    apply_plan(result, ..., device_filter=device)
else:
    result = compute_plan(rig, root_path=config_path)
    apply_plan(result, ...)
```

### Anti-Patterns to Avoid

- **New top-level function for APPLY-02:** A `apply_device_scenes()` function would duplicate the setup phase, state read, and state write that already live in `apply_plan()`. Adding a parameter is strictly less code and less risk.
- **Filtering at the plan level:** Do not create a filtered copy of the Plan object. Filter at dispatch time inside `apply_plan()` — the plan structure is computed once and the filter is a runtime concern.
- **Printing "already set" outside apply.py:** The VERIFY display must live in `apply.py` next to the existing VERIFY guard. Pushing it into `AnalogDevice` would mean the analog plugin knows about VERIFY, coupling the plugin to engine internals.
- **Modifying scenes state for non-targeted devices in APPLY-02:** Only the targeted device's confirmed results should gate `state.scenes` update. The existing guard `any(r.status == "confirmed" for r in device_results)` already handles this correctly once `device_results` only contains the filtered device's result.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Console output | Custom formatter | `console.print(...)` with Rich markup | Module-level `console = Console()` already in apply.py |
| Test state injection | Disk writes in tests | `InMemoryStateAdapter` + `_write_state_file` | Established pattern, no disk I/O |
| Test prompt tracking | `patch(builtins.input)` | `InMemoryPromptAdapter` with `side_effect` tracking | Already used across all apply tests |
| Device existence check | Manual loop | `device not in rig.devices` | `rig.devices` is a dict |

---

## Common Pitfalls

### Pitfall 1: VERIFY Branch Output Missing for Non-Analog VERIFY Actions

**What goes wrong:** The VERIFY status is assigned by `compute.py:167` (`ActionStatus.CONFIGURE if needs_config else ActionStatus.VERIFY`) for ALL device types when state matches. If the "already set" print only fires for `DeviceType.ANALOG`, it silently skips non-analog devices already at correct state.

**Why it happens:** The developer adds the output only to the ANALOG block thinking "this is just for analog."

**How to avoid:** Add the `console.print` inside `if action.status == ActionStatus.VERIFY:` — which covers both analog and non-analog VERIFY actions. No `DeviceType` check needed.

**Warning signs:** Test for HX Stomp with state already matching does not show "already set" output.

### Pitfall 2: APPLY-02 state.scenes Written for the Wrong Scene

**What goes wrong:** If `device_results` is populated with results from other devices (before filter), the `any(r.status == "confirmed" ...)` guard can fire for scenes where the target device had no action.

**Why it happens:** The device filter is placed after `device_results.append(action_result)` instead of before.

**How to avoid:** `continue` the action loop before appending any result for non-target devices.

**Warning signs:** `state.scenes` shows a scene the filtered device was not present in.

### Pitfall 3: Controller Phase Runs During device_filter Apply

**What goes wrong:** Controller programming fires even when `device_filter` is set, potentially re-sending the full bank config to MC6 when the user only intended to update one device.

**Why it happens:** The controller phase condition (`if rig and rig.controller and not scene:`) does not account for `device_filter`.

**How to avoid:** Add `and not device_filter` to the controller phase condition.

### Pitfall 4: D-05 Guard Test Assertion Still Expects Old Error Message

**What goes wrong:** `test_cli_apply.py:test_device_without_preset_exits_1` asserts `"--device and --preset must be used together" in result.stdout`. After removing D-05, this test now fails because `--device` without `--preset` is valid.

**Why it happens:** The test was written to cover D-05 which is now removed.

**How to avoid:** Update `TestDevicePresetFlagValidation` — the test `test_device_without_preset_exits_1` must be changed to verify that `--device` without `--preset` succeeds (exit 0) or routes to `apply_plan`. The class name stays but the test purpose inverts.

**Warning signs:** `uv run pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation::test_device_without_preset_exits_1` fails after D-05 removal.

### Pitfall 5: APPLY-01 Test Only Asserts on device.apply() Not Being Called

**What goes wrong:** The existing `TestVerifyActionSkipped` test passes before and after the APPLY-01 change because it only checks that `AnalogDevice.apply()` was not called — it does not check for console output.

**Why it happens:** The test was written to verify the skip behavior, not the display behavior.

**How to avoid:** Add a separate test class `TestVerifyDisplay` that uses `capsys` to assert the "already set" text appears in stdout.

---

## Code Examples

### APPLY-01: Full VERIFY Branch After Change

```python
# Source: packages/rig/src/rig/engine/apply.py lines 115-119 (before change)
if action.status == ActionStatus.VERIFY:
    logger.debug("Device '%s': preset already correct — skipping apply", action.device)
    console.print(                                                  # NEW LINE
        f"  [green]✓[/green] {action.device}: already set to '{action.preset_name}'"  # NEW LINE
    )                                                               # NEW LINE
    action_result = DeviceApplyResult(
        device=action.device, status="skipped", preset=action.preset_name
    )
```

### APPLY-01: Test Pattern (capsys assertion)

```python
# New test in test_apply.py — pattern derived from existing test_apply.py + TestVerifyActionSkipped
class TestVerifyDisplay:
    def test_verify_action_prints_already_set(self, tmp_path, capsys):
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        analog = AnalogDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[AnalogPreset(id="edge", pedal="tumnus", name="Edge", values={"gain": 5.0})],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={"s1": {"presets": {"tumnus": "edge"}}},
                type="controller", midi_channel=1, banks=[],
            ),
        )
        rig = Rig(name="test", signal_chain=[], devices={"tumnus": analog, "mc6": ctrl})

        _write_state_file(tmp_path, {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})
        plan = compute_plan(rig, root_path=str(tmp_path))
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_plan(plan, state_writer=state_adapter, confirmation_io=prompt_io,
                   rig=rig, config_path=str(tmp_path), dry_run=False)

        captured = capsys.readouterr()
        assert "already set" in captured.out
        assert "tumnus" in captured.out
        assert "edge" in captured.out
```

### APPLY-02: engine-level test pattern

```python
# New test class in test_apply.py — pattern follows existing TestApplyPlan
class TestDeviceFilterApply:
    def test_device_filter_applies_only_named_device(self, tmp_path):
        """apply_plan with device_filter only runs actions for the named device."""
        # Build rig with two devices in two scenes
        # Pass device_filter="klon" to apply_plan
        # Assert state only has "klon", not "brothers"
        ...

    def test_device_filter_across_multiple_scenes(self, tmp_path):
        """device_filter applies the named device's action in every scene, not just the first."""
        ...

    def test_device_filter_does_not_run_controller_phase(self, tmp_path):
        """Controller programming phase is skipped when device_filter is set."""
        ...
```

### APPLY-02: CLI routing test pattern

```python
# Update to test_cli_apply.py
class TestDeviceOnlyApply:
    def test_device_without_preset_routes_to_apply_plan_with_filter(self, tmp_path):
        """--device without --preset calls apply_plan with device_filter, not apply_device_preset."""
        ...
    def test_device_only_unknown_device_exits_1(self, tmp_path):
        """--device without --preset with unknown device exits 1."""
        ...
```

---

## APPLY-01 Full Path Trace (Verified)

```
state.json → read_state() → RigState.devices["tumnus"].last_preset = "edge"
                                        ↓
compute_plan() → for pedal_id, preset_id in scene.presets.items():
  pedal.type == DeviceType.ANALOG                           [compute.py:120]
  analog_needs_change = actual_preset != preset_id         [compute.py:121]
  → False (both "edge")
  analog_status = ActionStatus.VERIFY                      [compute.py:122]
  DeviceAction(status=ActionStatus.VERIFY, ...)            [compute.py:130-140]
                                        ↓
apply_plan() → for action in sp.device_actions:
  action.status == ActionStatus.VERIFY                     [apply.py:115]
  → logger.debug(...)                                      [apply.py:116]
  → (GAP: no console.print here)
  → DeviceApplyResult(status="skipped", ...)               [apply.py:117-119]
  → device.apply() is NOT called                           ✓ confirmed by TestVerifyActionSkipped
```

The mechanism is verified end-to-end by `test_same_scene_applied_twice_no_reprompt_on_second_apply`. The only missing piece is the `console.print` line and an output assertion test. [VERIFIED: direct code read]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (dev dependency) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/rig/tests/test_apply.py -q` |
| Full suite command | `uv run pytest packages/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APPLY-01a | VERIFY branch prints "already set to '<preset>'" | unit | `pytest packages/rig/tests/test_apply.py::TestVerifyDisplay -x` | ❌ Wave 0 |
| APPLY-01b | VERIFY branch does NOT call device.apply() | unit | `pytest packages/rig/tests/test_apply.py::TestVerifyActionSkipped -x` | ✅ exists |
| APPLY-01c | Prompt adapter never called when state already matches | unit | `pytest packages/rig/tests/test_apply.py::TestVerifyDisplay -x` | ❌ Wave 0 |
| APPLY-02a | `apply_plan(device_filter="x")` skips other devices' actions | unit | `pytest packages/rig/tests/test_apply.py::TestDeviceFilterApply -x` | ❌ Wave 0 |
| APPLY-02b | `device_filter` applies named device across all scenes | unit | `pytest packages/rig/tests/test_apply.py::TestDeviceFilterApply -x` | ❌ Wave 0 |
| APPLY-02c | Controller phase skipped when `device_filter` is set | unit | `pytest packages/rig/tests/test_apply.py::TestDeviceFilterApply -x` | ❌ Wave 0 |
| APPLY-02d | `--device` without `--preset` routes to apply_plan with filter | CLI | `pytest packages/rig/tests/test_cli_apply.py::TestDeviceOnlyApply -x` | ❌ Wave 0 |
| APPLY-02e | D-05 guard updated: `--device` alone is now valid | CLI | `pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation -x` | needs update |
| APPLY-02f | `--preset` alone still exits 1 | CLI | `pytest packages/rig/tests/test_cli_apply.py::TestDevicePresetFlagValidation -x` | ✅ unchanged |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/rig/tests/test_apply.py packages/rig/tests/test_cli_apply.py -q`
- **Per wave merge:** `uv run pytest packages/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `TestVerifyDisplay` class in `test_apply.py` — covers APPLY-01a, APPLY-01c
- [ ] `TestDeviceFilterApply` class in `test_apply.py` — covers APPLY-02a, APPLY-02b, APPLY-02c
- [ ] `TestDeviceOnlyApply` class in `test_cli_apply.py` — covers APPLY-02d
- [ ] Update `TestDevicePresetFlagValidation.test_device_without_preset_exits_1` in `test_cli_apply.py` — must invert from "exits 1" to "exits 0" (APPLY-02e)

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`. No new network surface, no new inputs beyond existing CLI args.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI tool |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (device_id param) | Validate `device_id` exists in `rig.devices` before use |
| V6 Cryptography | no | N/A |

V5 is already covered: the CLI validates `device not in rig.devices` and exits 1 before calling the engine. The engine `apply_device_preset()` also validates and raises ValueError. The new `device_filter` path in the CLI must include the same existence check. [ASSUMED — ASVS L1 for local CLI tools applies only to input validation of user-supplied identifiers]

---

## Open Questions

1. **Output format for multi-device "already set" in APPLY-02 scenes**
   - What we know: VERIFY prints "already set to 'X'" per device; with device_filter only the target device's VERIFY shows
   - What's unclear: Whether the scene header ("Scene: sceneName (unchanged)") should still print when all actions in a filtered scene are VERIFY-skipped
   - Recommendation: Keep the scene header suppressed for "unchanged" scenes (existing behavior, `sp.status == "unchanged"` already returns early). The VERIFY case only fires for scenes that are "new" or "changed" by status, so the header already prints.

2. **`--preset` alone without `--device` — remains exit 1?**
   - What we know: Current code exits 1 with D-05 message. APPLY-02 only defines `--device` alone as valid.
   - What's unclear: Whether `--preset` alone should be an informative error or a typer validation error.
   - Recommendation: Keep existing behavior — `--preset` without `--device` remains exit 1. The error message should update to something like "–preset requires –device".

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `device_filter` param on `apply_plan()` is preferable to a new `apply_device_scenes()` function | Architecture Patterns | Low — either approach works; device_filter is simpler and less code |
| A2 | Controller phase must be gated with `and not device_filter` | Architecture Patterns | Medium — if not gated, MC6 reprograms on every device-only apply |
| A3 | "already set" output format follows existing apply.py green checkmark style | Code Examples | Low — cosmetic only, easily changed |
| A4 | ASVS L1 for local CLI applies only to V5 input validation | Security Domain | Low — no auth or network surface exists |

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `packages/rig/src/rig/engine/apply.py` — full file, 271 lines
- Direct code read: `packages/rig/src/rig/engine/plan/compute.py` — full file, 211 lines
- Direct code read: `packages/rig/src/rig/engine/plan/models.py` — full file, 47 lines
- Direct code read: `packages/rig/src/rig/cli/commands/apply.py` — full file, 87 lines
- Direct code read: `packages/rig/tests/test_apply.py` — full file, 817 lines
- Direct code read: `packages/rig/tests/test_apply_device_preset.py` — full file, 266 lines
- Direct code read: `packages/rig/tests/test_cli_apply.py` — full file, 155 lines
- Direct code read: `packages/rig/tests/fakes.py` — full file, 75 lines
- Direct code read: `packages/rig/tests/conftest.py` — FakeDevice
- Direct code read: `packages/rig-analog/src/rig_analog/device.py` — full file, 120 lines
- Direct code read: `packages/rig/src/rig/engine/plugin.py` — full file, 208 lines
- Test run: `uv run pytest packages/rig/tests/test_apply.py packages/rig/tests/test_cli_apply.py -q` → 31 passed

### Secondary (MEDIUM confidence)
- CONTEXT.md — locked decisions and constraints read directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing dependencies confirmed by test run
- Architecture: HIGH — full code read of all key files; patterns derived from direct inspection
- Pitfalls: HIGH — identified from direct read of affected test assertions (D-05 guard test)

**Research date:** 2026-06-24
**Valid until:** 90 days (stable internal codebase, no external dependencies)
