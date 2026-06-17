# Phase 25: I/O Parity - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Thread `ConfirmationIO` through `AnalogDevice.apply()` — eliminate the one remaining raw `input()` call in an applier path. After this phase, all device confirmation prompts go through the `ConfirmationIO` protocol and analog tests use `InMemoryPromptAdapter` without monkeypatching `builtins.input`.

</domain>

<decisions>
## Implementation Decisions

### ConfirmationIO method for analog
- **D-01:** `AnalogDevice.apply()` calls `ctx.confirmation_io.prompt_device(action.device, action.preset_name, None, None, False)` instead of `prompt_analog()`. `preset_number=None`, `midi_channel=None`, `midi_connected=False`.
- **D-02:** `rig.interaction.midi.prompt_device()` is updated to display `"Set {device} manually"` (or similar non-MIDI text) when `midi_channel is None`, instead of `"→ Connect MIDI to {device}"`.

### Retry support
- **D-03:** `AnalogDevice.apply()` loops on `"retry"` — if `prompt_device()` returns `"retry"`, re-call `prompt_device()` until the user confirms, skips, or quits. Analog retry = "I need to adjust the knobs again."

### prompt_analog fate
- **D-04:** Delete `prompt_analog()` from `rig_analog/interaction.py`. It has one call site (`AnalogDevice.apply()`) which moves to `ctx.confirmation_io.prompt_device()`. Also remove the export from `rig_analog/__init__.py` (`__all__` and the import).

### Test migration
- **D-05:** Migrate exactly 3 tests in `packages/rig/tests/test_devices.py` (lines ~140, ~153, ~343). Replace `with patch("rig_analog.device.prompt_analog", return_value="confirm"/"quit"/"skip"):` with `_make_apply_ctx(confirmation_io=InMemoryPromptAdapter(default="confirm"/"quit"/"skip"))`. Remove `from unittest.mock import patch` in those tests.

### MC6 scope exclusion
- **D-06:** `RichConfirmationIO.prompt_mc6_navigate()` contains `input()` but is the adapter's production implementation — not an applier callsite. `rig_morningstar/device.py` already calls `ctx.confirmation_io.prompt_mc6_navigate()` correctly. MC6 is out of scope for Phase 25.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core I/O Abstraction
- `packages/rig/src/rig/engine/ports.py` — `ConfirmationIO` Protocol, `RichConfirmationIO` production adapter, `prompt_mc6_navigate` and `prompt_device` implementations
- `packages/rig/tests/fakes.py` — `InMemoryPromptAdapter` — the test double to use after migration

### Analog Plugin
- `packages/rig-analog/src/rig_analog/device.py` — `AnalogDevice.apply()` — the callsite being changed (currently calls `prompt_analog()` at line 70)
- `packages/rig-analog/src/rig_analog/interaction.py` — `prompt_analog()` — to be deleted
- `packages/rig-analog/src/rig_analog/__init__.py` — exports `prompt_analog` in `__all__`, needs cleanup

### Tests to migrate
- `packages/rig/tests/test_devices.py` — 3 tests at lines ~140, ~153, ~343 that `patch("rig_analog.device.prompt_analog", ...)`

### Display logic
- `packages/rig/src/rig/interaction/midi.py` — `prompt_device()` — needs to handle `midi_channel=None` case to show non-MIDI text for analog

### Requirements
- `.planning/REQUIREMENTS.md` — IO-01, IO-02 (the two requirements mapped to this phase)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InMemoryPromptAdapter` (`packages/rig/tests/fakes.py`): Already implements all `ConfirmationIO` methods including `prompt_device()`. Accepts `default` and `side_effect` args. Used in ChaseBliss and MC6 tests today.
- `_make_apply_ctx()` helper (`packages/rig/tests/test_devices.py`): Already accepts `confirmation_io` parameter — no new test infrastructure needed.

### Established Patterns
- `DeviceApplyContext.confirmation_io` already exists and is threaded through to all other device appliers (MC6, ChaseBliss, HX). Analog is the only outlier.
- MC6 (`rig_morningstar/device.py:99`) uses `ctx.confirmation_io.prompt_mc6_navigate()` — exact same pattern to follow for analog.

### Integration Points
- `AnalogDevice.apply()` in `rig_analog/device.py` is the only file that needs a logic change. The Protocol and adapters are already complete.
- `prompt_device()` in `rig.interaction.midi` needs a one-line display fix for the `midi_channel=None` branch.

</code_context>

<specifics>
## Specific Ideas

- Retry loop in `AnalogDevice.apply()`: While `result == "retry"`, call `prompt_device()` again. No max iteration limit — same as current `prompt_analog()` behavior which loops until valid input.
- The display update in `rig.interaction.midi.prompt_device()`: When `midi_channel is None`, replace `"→ Connect MIDI to {device}"` with something like `"→ Set {device} manually (knobs/switches)"`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-I/O Parity*
*Context gathered: 2026-06-17*
