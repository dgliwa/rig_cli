# Phase 23: ApplyContext Consolidation & Test Capture Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 23-applycontext-consolidation-test-capture-fixes
**Areas discussed:** ApplyContext retirement, ConfirmationIO boundary for CBA prompts

---

## ApplyContext Retirement

### Q1: Delete ApplyContext entirely from apply.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | Remove the ctx = ApplyContext(...) creation; use field values directly when building SetupContext and DeviceApplyContext | ✓ |
| Keep as local alias | Keep as a convenient local struct for holding shared fields | |

**User's choice:** Delete it
**Notes:** `apply.py` creates `ApplyContext` only to copy fields into `SetupContext` and `DeviceApplyContext` — it's a redundant intermediate. No value in keeping it.

---

### Q2: What should ChaseBlissApplier.apply_setup accept after migration?

| Option | Description | Selected |
|--------|-------------|----------|
| SetupContext | Switch apply_setup to accept SetupContext — identical fields, already what the caller holds | ✓ |
| DeviceApplyContext minus action | Use DeviceApplyContext but it carries an action field that doesn't belong in setup | |
| New shared context type | Introduce a base context dataclass in engine.plugin | |

**User's choice:** SetupContext
**Notes:** `ChaseBlissDevice.setup(ctx: SetupContext)` already passes `SetupContext` to `apply_setup`. Changing the type annotation is a 1-line fix at the applier boundary.

---

### Q3: What happens to appliers/base.py after ApplyContext is gone?

| Option | Description | Selected |
|--------|-------------|----------|
| Move utilities to engine.plugin | DeviceApplyResult and state helpers move to engine/plugin.py — one place for the full plugin public surface | ✓ |
| Keep appliers/base.py as utility module | Drop ApplyContext but keep other exports in place | |
| Move to engine/appliers/utils.py | Separate utilities module in appliers subpackage | |

**User's choice:** Move utilities to engine.plugin
**Notes:** Consolidates all plugin-facing types and helpers in one module. Importers in `rig-chasebliss` update from `rig.engine.appliers.base` to `rig.engine.plugin`.

---

## ConfirmationIO Boundary for CBA Prompts

### Q1: How should CBA interaction functions become testable?

| Option | Description | Selected |
|--------|-------------|----------|
| Generic prompt on ConfirmationIO | Add `prompt(text: str) -> str` to ConfirmationIO. Interaction functions accept confirmation_io and call confirmation_io.prompt(...) instead of input(). RichConfirmationIO.prompt() wraps input(). | ✓ |
| CBA sub-Protocol in rig-chasebliss | CBA plugin defines CbaConfirmationIO(Protocol) with 4 specific methods | |
| Just add prompt_cba_after_pc to test patches | Quick fix but doesn't route through ConfirmationIO | |

**User's choice:** Generic prompt on ConfirmationIO
**Notes:** Core Protocol stays generic — no CBA-specific methods leak into the base. The `ConfirmationIO.prompt(text)` method is the raw-input primitive; interaction functions keep their own parsing logic.

---

### Q2: How does confirmation_io reach the interaction functions?

| Option | Description | Selected |
|--------|-------------|----------|
| Thread through applier context | ChaseBlissApplier already has ctx.confirmation_io; pass it as argument to each interaction function | ✓ |
| Module-level injectable on rig_chasebliss.interaction | Module-level _io variable tests set before calling — shared mutable state, fragile | |

**User's choice:** Thread through applier context
**Notes:** Clean data flow — no shared mutable state. Each interaction function gains one parameter: `confirmation_io: ConfirmationIO`.

---

### Q3: Should _patch_cba_prompts be deleted?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it — InMemoryPromptAdapter covers all CBA prompts | Module-level patching obsolete once prompts route through ctx.confirmation_io | ✓ |
| Keep it as a fallback | Might still be useful for edge-case tests | |

**User's choice:** Delete it
**Notes:** `InMemoryPromptAdapter` with the right side_effect sequence handles all CBA prompt interactions. Removing the helper eliminates a confusing vestigial pattern.

---

## Claude's Discretion

None — all decisions were made by the user.

## Deferred Ideas

None — discussion stayed within phase scope.
