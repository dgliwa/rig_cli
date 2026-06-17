# Phase 23: ApplyContext Consolidation & Test Capture Fixes - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the legacy `ApplyContext` dataclass from `engine/appliers/base.py`; consolidate
`DeviceApplyResult`, `update_device_state`, and `mark_preset_saved` into `engine/plugin.py`;
migrate `ChaseBlissApplier.apply_setup` to accept `SetupContext`; add a generic `prompt(text: str) -> str`
method to `ConfirmationIO` so CBA interaction functions route through the Protocol instead of calling
`input()` directly; fix the 3 stdin-capture test failures so `make test` passes without `-s`.

Zero user-visible behavior changes.

</domain>

<decisions>
## Implementation Decisions

### ApplyContext retirement
- **D-01:** Delete `ApplyContext` dataclass from `engine/appliers/base.py` entirely — no backwards-compat shim. Remove the `ctx = ApplyContext(...)` creation in `apply_plan`; use the field values directly when building `SetupContext` and `DeviceApplyContext`.
- **D-02:** `ChaseBlissApplier.apply_setup(actions, ctx)` switches its type annotation from `ApplyContext` → `SetupContext`. The caller (`ChaseBlissDevice.setup`) already holds a `SetupContext` — no bridging needed.
- **D-03:** Move `DeviceApplyResult`, `update_device_state`, and `mark_preset_saved` from `appliers/base.py` to `engine/plugin.py`. `appliers/base.py` becomes empty and is deleted. All importers (`rig_chasebliss/applier.py`, any core files) update to `from rig.engine.plugin import ...`.

### ConfirmationIO Protocol extension
- **D-04:** Add `prompt(text: str) -> str` to `ConfirmationIO` in `engine/ports.py`. This is a generic raw-input method — no CBA-specific knowledge in the core Protocol.
- **D-05:** `RichConfirmationIO.prompt(text)` wraps `input(text)` directly.
- **D-06:** All 4 CBA interaction functions (`prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_after_pc`, `prompt_cba_register`) in `rig_chasebliss/interaction.py` accept `confirmation_io: ConfirmationIO` as a parameter and call `confirmation_io.prompt(...)` instead of `input(...)`.
- **D-07:** `ChaseBlissApplier` threads `ctx.confirmation_io` to each interaction function call. No signature changes outside `rig-chasebliss`.

### Test clean-up
- **D-08:** Delete `_patch_cba_prompts` from `tests/test_apply.py` — module-level monkeypatching is obsolete once all prompts flow through `ctx.confirmation_io`. Tests use `InMemoryPromptAdapter` with the desired response sequence instead.
- **D-09:** `test_build_preset_confirm_sends_ccs_and_updates_state` in `test_appliers.py` — remove the `@patch("rig_chasebliss.applier.prompt_cba_build_preset")` decorator; wire an `InMemoryPromptAdapter` into the test context so both `prompt_cba_build_preset` and `prompt_cba_after_pc` are served from it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §TYPE-05 — exact acceptance criteria: `apply.py` imports `DeviceApplyContext` exclusively; grep for old `ApplyContext` import in engine source returns zero hits
- `.planning/REQUIREMENTS.md` §TEST-02 — exact acceptance criteria: the 3 named tests pass with `make test`; interaction functions delegate to `ConfirmationIO`

### Source files being changed (core)
- `packages/rig/src/rig/engine/appliers/base.py` — file being deleted; exports `ApplyContext`, `DeviceApplyResult`, `update_device_state`, `mark_preset_saved`; understand all importers before deleting
- `packages/rig/src/rig/engine/plugin.py` — receives `DeviceApplyResult`, `update_device_state`, `mark_preset_saved`; planner must check for name collisions before adding
- `packages/rig/src/rig/engine/apply.py` — removes `ctx = ApplyContext(...)` creation; drops `from rig.engine.appliers.base import ApplyContext`; uses field values directly
- `packages/rig/src/rig/engine/ports.py` — adds `prompt(text: str) -> str` to `ConfirmationIO` Protocol and `RichConfirmationIO`

### Source files being changed (rig-chasebliss plugin)
- `packages/rig-chasebliss/src/rig_chasebliss/applier.py` — `apply_setup` type: `ApplyContext` → `SetupContext`; imports update; interaction function calls gain `ctx.confirmation_io` argument
- `packages/rig-chasebliss/src/rig_chasebliss/interaction.py` — all 4 prompt functions gain `confirmation_io: ConfirmationIO` parameter; replace `input(...)` with `confirmation_io.prompt(...)`

### Test files being changed
- `packages/rig/tests/test_apply.py` — delete `_patch_cba_prompts`; rebuild affected tests using `InMemoryPromptAdapter`
- `packages/rig/tests/test_appliers.py` — remove `@patch` decorators on the 3 failing tests; wire `InMemoryPromptAdapter` into the test context

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InMemoryPromptAdapter` — already exists in the test suite; used by `test_apply.py` for MIDI/channel prompts; extend its `side_effect` list to include CBA prompt responses
- `SetupContext` in `engine/plugin.py` — already has all fields that `ApplyContext` had (`confirmation_io`, `connected_devices`, `state`, `config_path`, `rig`, `dry_run`, `midi`); direct drop-in for `ChaseBlissApplier`
- `DeviceApplyContext` in `engine/plugin.py` — the target single-context type for `apply.py`; already used by device.apply() calls

### Established Patterns
- No backwards-compat shims (per CLAUDE.md anti-patterns) — confirmed by prior phases; delete files and fix importers directly
- `TYPE_CHECKING` guard pattern — used in `appliers/base.py` for `Rig` and `DeviceAction`; preserve this pattern when moving exports to `engine/plugin.py`
- Interaction functions in `rig_chasebliss` already have structured return types (`_ConfirmResult = Literal[...]`); adding `confirmation_io` param follows the same pattern as `MidiManager` threading in the apply flow

### Integration Points
- `ChaseBlissDevice.setup(ctx: SetupContext)` in `rig_chasebliss/device.py` — calls `ChaseBlissApplier().apply_setup(actions, ctx)`; after D-02 the type annotation on `apply_setup` matches what the caller already passes — no change at the call site
- `apply.py` creates both `SetupContext` and `DeviceApplyContext` from the same flat fields; after D-01 it just constructs them directly without the intermediate `ApplyContext` bag

</code_context>

<specifics>
## Specific Ideas

- All 4 CBA interaction functions need `confirmation_io` added — do them all in one pass to avoid an inconsistent intermediate state where some functions route through the Protocol and some still call `input()` directly
- `InMemoryPromptAdapter` response sequence must account for the two-step CBA build flow: `prompt_cba_build_preset` response first, then `prompt_cba_after_pc` response — order matters for tests that check both

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-applycontext-consolidation-test-capture-fixes*
*Context gathered: 2026-06-16*
