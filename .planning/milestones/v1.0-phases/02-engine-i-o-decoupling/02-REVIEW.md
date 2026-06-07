---
phase: 02-engine-i-o-decoupling
reviewed: 2026-06-04T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - conftest.py
  - src/rig/cli/commands/apply.py
  - src/rig/engine/appliers/analog.py
  - src/rig/engine/appliers/base.py
  - src/rig/engine/appliers/chase_bliss.py
  - src/rig/engine/appliers/midi_device.py
  - src/rig/engine/apply.py
  - src/rig/engine/ports.py
  - tests/fakes.py
  - tests/test_appliers.py
  - tests/test_apply.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-06-04
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This phase introduces I/O port Protocols (`ConfirmationIO`, `StateWriter`, `MidiConnectionIO`) that decouple the apply engine from MIDI hardware and interactive prompts. The structural approach is sound — `Protocol` classes, production adapters in `ports.py`, and in-memory test fakes in `tests/fakes.py`. The major wiring in `apply.py` and the applier chain is functionally correct for the happy path.

Five warning-level issues were found: two relate to partial state loss on mid-run cancellation, one is a logic error in MC6 state-modified detection, one is a dead-code wrapper function, and one is a missing validation in the test fake. Four info-level issues cover a misleading test name, three TODO markers left in production code, and duplicate-enqueueing in the CBA action queue.

No security vulnerabilities were found.

## Warnings

### WR-01: Confirmed MIDI port state is lost on mid-run cancellation

**File:** `src/rig/engine/apply.py:112-114`

**Issue:** When a user confirms MIDI port connection for device_1 during the connection loop (lines 115-118 update state in memory and set `state_modified = True`), and then quits at device_2's connection prompt (line 112), the function returns `"cancelled"` at line 114 without writing state to disk. The in-memory `state` has device_1's `midi_port` recorded but it is never persisted. On the next run the user must reconnect device_1 again. The same early-return-without-flush pattern exists for cancellations during CBA setup (line 130) and during scene apply (line 174).

**Fix:** Flush state to disk before returning `"cancelled"` when `state_modified` is true and `config_path` is set:

```python
def _flush_state_if_needed(config_path, dry_run, state_modified, state, state_writer):
    if config_path and not dry_run and state_modified:
        state_writer.write(config_path, state)

# At each early-return cancellation point:
if res == "quit":
    console.print("[red]Apply cancelled by user[/red]")
    _flush_state_if_needed(config_path, dry_run, state_modified, state, state_writer)
    return ApplyResult(status="cancelled", ...)
```

---

### WR-02: MC6 state-modified check uses pre-existing state rather than tracking actual writes

**File:** `src/rig/engine/apply.py:193-195`

**Issue:** After calling `apply_banks(mc6_banks, ctx)`, the code checks `if state.devices.get("mc6"):` to determine whether to mark `state_modified`. This check is truthy when `"mc6"` exists in the *loaded* state from a prior run — even if `apply_banks` did not write any new state this run. This causes `state_writer.write()` to be called unnecessarily on every subsequent apply run that has an MC6 controller in state, even when nothing changed.

**Fix:** Track state modification inside `MC6Applier.apply_banks` (e.g., return a bool or check state before and after), or snapshot the `state.devices` key before `apply_banks` to detect the delta:

```python
mc6_before = state.devices.get("mc6")
get_mc6_applier().apply_banks(mc6_banks, ctx)
if state.devices.get("mc6") != mc6_before:
    state_modified = True
```

---

### WR-03: Dead-code wrapper `_update_device_state` in `apply.py`

**File:** `src/rig/engine/apply.py:42-44`

**Issue:** `_update_device_state` is defined as a module-level wrapper that delegates entirely to the imported `update_device_state`. It is never called anywhere — the only direct call at line 116 goes to `update_device_state` directly. The wrapper is dead code that adds noise and could mislead future contributors into believing it has a distinct purpose.

**Fix:** Remove the function entirely.

```python
# DELETE these three lines:
def _update_device_state(state: RigState, device: str, **fields) -> None:
    """Update a device's state fields in-place."""
    update_device_state(state, device, **fields)
```

---

### WR-04: `InMemoryMidiConnectionIO` does not validate the `result` parameter

**File:** `tests/fakes.py:102`

**Issue:** `InMemoryPromptAdapter` guards against invalid values with `assert default in _VALID` at construction time (line 37-40). `InMemoryMidiConnectionIO` accepts any string as `result` with no validation. An invalid value (e.g., a typo like `"confirmed"` instead of `"confirm"`) would be silently returned to the caller, causing tests to neither confirm nor quit — silently falling through the `if` branches and potentially producing a false-pass.

**Fix:** Add the same assertion used by `InMemoryPromptAdapter`:

```python
def __init__(self, result: str = "confirm", port_name: str | None = "FakePort") -> None:
    assert result in _VALID, f"Invalid result {result!r}; must be one of {_VALID}"
    self.result = result
    self.port_name = port_name
```

---

### WR-05: `_establish_channel` silently returns `"skipped"` when user confirms but device is not MIDI-connected — no user feedback

**File:** `src/rig/engine/appliers/chase_bliss.py:118-146`

**Issue:** When `midi_sent = False` (device not in `ctx.connected_devices` or `ctx.midi is None`), and the user responds `"confirm"` to Step 1's prompt, the function skips Step 3 entirely and returns `DeviceApplyResult(status="skipped")`. There is no console output explaining why the operation was skipped. From the user's perspective, they answered "confirm" and received no acknowledgment or error — the CBA channel is not established and `channel_established` stays False.

**Fix:** Add a console message explaining the skip reason when `not midi_sent` after Step 1 confirms:

```python
if not midi_sent:
    console.print(
        f"  [yellow]⚠[/yellow] {action.device}: MIDI not connected — "
        "channel establishment skipped"
    )
    return DeviceApplyResult(device=action.device, status="skipped", preset=None)
```

---

## Info

### IN-01: Test name `test_clean_plan_prints_no_changes` is misleading — does not test a clean plan

**File:** `tests/test_apply.py:59`

**Issue:** The test name implies it verifies that a clean (unchanged) plan prints "No changes needed". However, `compute_plan(config)` with no `root_path` produces a plan with `status="changes_detected"` (all scenes are new). The assertion `assert "No changes needed" not in captured.out` vacuously passes because the code under test never reaches the `plan.status == "clean"` branch. The actual clean-plan behavior (early return with the message) has no test.

**Fix:** Rename the test to reflect what it actually tests, and add a separate test for the clean-plan early-return:

```python
def test_non_clean_plan_does_not_print_no_changes(self, capsys):
    ...

def test_clean_plan_returns_no_changes_status(self):
    # Pre-populate state so all scenes are unchanged
    ...
    result = apply_plan(plan, ...)
    assert result.status == "no_changes"
```

---

### IN-02: Three TODO markers left in production apply.py

**File:** `src/rig/engine/apply.py:47,82,122`

**Issue:** Three `TODO` comments document known design concerns: the function being too large (line 47), controller identification ordering (line 82), and CBA setup belonging in device-level plans rather than the global plan (line 122). Per CLAUDE.md, TODO markers are acceptable in side-project mode. Noting here for tracking.

**Fix:** Track as a GitHub issue or keep as-is per side-project velocity policy. No code change required now.

---

### IN-03: Duplicate actions can accumulate in CBA setup `pending` queue

**File:** `src/rig/engine/appliers/chase_bliss.py:40-46`

**Issue:** `_enqueue_new_actions()` checks `if key not in seen` before appending to `pending`, but `seen` only has items added when they are popped and processed (line 53). If `_enqueue_new_actions()` is called multiple times before a re-detected action is processed, the same action is appended to `pending` multiple times. The duplicate-processing guard at line 51 (`if action_key in seen: continue`) prevents executing the same action twice, but dead entries accumulate in `pending`.

**Fix:** Add the action key to `seen` immediately when enqueueing:

```python
def _enqueue_new_actions() -> None:
    if ctx.rig is None:
        return
    for a in detect_cba_setup(ctx.rig, ctx.state):
        key = (a.device, a.type, a.preset_id)
        if key not in seen:
            seen.add(key)   # prevent duplicate queuing
            pending.append(a)
```

---

### IN-04: Module-level `Console()` instances in appliers cannot be injected or suppressed in tests

**File:** `src/rig/engine/appliers/analog.py:11`, `src/rig/engine/appliers/midi_device.py:11`, `src/rig/engine/appliers/chase_bliss.py:17`

**Issue:** Each applier creates a `Console()` at module scope. Rich output from appliers during tests is not captured by `capsys` (which captures `stdout`/`stderr` but not Rich `Console` that writes to its own `file`). Tests that assert on console output (e.g., `test_cba_setup_shown_in_dry_run`) may be fragile or passing vacuously. The `apply.py` console instance has the same pattern but is consistent.

**Fix:** For this project's scale and velocity target this is acceptable. If test fidelity matters, pass `Console` via `ApplyContext` or use `Console(file=sys.stdout)` so `capsys` captures it. No urgent change required.

---

_Reviewed: 2026-06-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
