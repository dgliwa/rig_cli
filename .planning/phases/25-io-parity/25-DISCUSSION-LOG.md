# Phase 25: I/O Parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 25-io-parity
**Areas discussed:** ConfirmationIO method choice, analog display text, retry support, prompt_analog fate, test migration scope, MC6 scope check

---

## ConfirmationIO Method Choice

| Option | Description | Selected |
|--------|-------------|----------|
| prompt_device() | Semantically correct device confirmation; InMemoryPromptAdapter already implements it returning _ConfirmResult; needs small display fix in rig.interaction.midi | ✓ |
| prompt() with text | Build prompt string in apply(), parse raw response; InMemoryPromptAdapter.prompt() returns _ConfirmResult so apply() would need to accept both short and full forms | |

**User's choice:** `prompt_device()`
**Notes:** Semantically correct, InMemoryPromptAdapter already wired for it.

---

## Analog Display Text

| Option | Description | Selected |
|--------|-------------|----------|
| Update rig.interaction.midi.prompt_device() | When midi_channel is None, show "Set {device} manually" instead of "→ Connect MIDI to {device}" | ✓ |
| Keep prompt_analog() display via prompt() | Display logic stays in rig_analog, apply() parses response | |

**User's choice:** Update `rig.interaction.midi.prompt_device()`
**Notes:** One-line change in the existing function, keeps display logic centralized.

---

## Retry Support

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — loop on retry | AnalogDevice.apply() loops if result is "retry" — user adjusts knobs and re-prompts | ✓ |
| No — map retry to skip | Simpler; user reruns rig apply to redo | |

**User's choice:** Support retry with a loop
**Notes:** Makes sense for analog — user may need multiple attempts to dial in knob positions.

---

## prompt_analog Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | One call site; dead code once apply() uses ctx.confirmation_io | ✓ |
| Keep it | Leave as dead code with raw input() — defeats the phase goal | |

**User's choice:** Delete `prompt_analog()` and remove its export from `rig_analog/__init__.py`

---

## Test Migration Scope

**Finding:** Exactly 3 tests in `packages/rig/tests/test_devices.py` (lines ~140, ~153, ~343) patch `rig_analog.device.prompt_analog`. All 3 migrate to `InMemoryPromptAdapter` via `_make_apply_ctx(confirmation_io=...)`.

No other files monkeypatch `builtins.input` in applier tests.

---

## MC6 prompt_mc6_navigate Check

**Finding:** `RichConfirmationIO.prompt_mc6_navigate()` calls `input()` internally, but this is the adapter's production implementation — not an applier callsite. `rig_morningstar/device.py:99` already correctly calls `ctx.confirmation_io.prompt_mc6_navigate()`. MC6 is out of scope for Phase 25.

---

## Claude's Discretion

None — all decisions made by user.

## Deferred Ideas

None — discussion stayed within phase scope.
