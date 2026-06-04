# Phase 2: Engine I/O Decoupling - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Introduce three narrow Protocol-typed I/O ports (`ConfirmationIO`, `StateWriter`, `MidiConnectionIO`) so `apply_plan` and the appliers can be tested without MIDI hardware and without patching `builtins.input`. All production behaviour is preserved — this is pure internal seam work with no user-visible changes. Deliverables: `engine/ports.py` (Protocols + production adapters), updated `ApplyContext` and `apply_plan` signatures, `tests/fakes.py` (in-memory adapters), and existing patched tests rewritten to use fakes.

Seven requirements from REQUIREMENTS.md §Engine Decoupling: DEC-01 through DEC-07.

</domain>

<decisions>
## Implementation Decisions

### ConfirmationIO method shape
- **D-01:** `ConfirmationIO` has **5 methods**, one per existing interaction function — `prompt_analog`, `prompt_device`, `prompt_cba_channel`, `prompt_cba_preset`, `prompt_cba_register`. Mirrors the current call sites 1:1; production adapter is a thin wrapper; fakes are straightforward to reason about.

### MidiConnectionIO scope
- **D-02:** `MidiConnectionIO` is **prompt-only** — its single method returns the chosen port name (`str | None`). `apply_plan` handles the actual `midi.open_port()` call separately. No mixing of prompt and port-open concerns.

### Adapter file location
- **D-03:** Protocols **and** their production adapters all live in `src/rig/engine/ports.py`. `cli.py` imports and instantiates. No separate `adapters.py` file. Single source of truth for the I/O seam.

### ApplyContext.confirmation_io field strategy
- **D-04:** `confirmation_io` is a **required field** (no default). DEC-04 (adding the field) and DEC-07 (rewriting tests to use fakes) land in the same phase so all call sites are updated atomically. No fallback branching in appliers.

### apply_plan parameter strategy
- **D-05:** `state_writer: StateWriter` and `midi_connection_io: MidiConnectionIO` are **required parameters** on `apply_plan` (no defaults). Consistent with D-04; every caller must explicitly provide adapters. Production adapters instantiated at the CLI boundary in `cli.py`.

### InMemoryPromptAdapter shape
- **D-06:** `InMemoryPromptAdapter(default="confirm")` with optional `side_effect: list[str]` — uses the same semantics as `unittest.mock.Mock.side_effect`. Returns `default` for every call unless a `side_effect` list is provided, in which case it pops responses in order. Covers all existing `patch("builtins.input", return_value=...)` and `side_effect=[...]` test patterns without recording.

### InMemoryStateAdapter shape
- **D-07:** `InMemoryStateAdapter` is **store-only** — holds a `RigState` in memory; `read_state` / `write_state` operate against it. Tests assert on the resulting state value. No call-count recording needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` §Engine Decoupling — exact signatures, Protocol names, adapter names, and success criteria for DEC-01 through DEC-07
- `.planning/ROADMAP.md` §Phase 2 — success criteria assertions to verify

### Files being modified / created
- `src/rig/engine/appliers/base.py` — `ApplyContext` dataclass (gains required `confirmation_io` field); `update_device_state` and `mark_preset_saved` helpers stay here
- `src/rig/engine/apply.py` — `apply_plan` function (gains required `state_writer` and `midi_connection_io` params; inline `read_state`/`write_state`/`prompt_midi_connect` calls replaced with adapter calls; DEC-06 scene-write fix)
- `src/rig/engine/ports.py` — **new file**: all three Protocols + their production adapters
- `src/rig/interaction/analog.py` — `prompt_analog` (wrapped by production `ConfirmationIO` adapter)
- `src/rig/interaction/midi.py` — `prompt_midi_connect`, `collect_midi_devices` (wrapped by `MidiConnectionIO` adapter)
- `src/rig/interaction/cba.py` — `prompt_cba_channel`, `prompt_cba_preset`, `prompt_cba_register` (wrapped by `ConfirmationIO` adapter)
- `tests/fakes.py` — **new file**: `InMemoryStateAdapter`, `InMemoryPromptAdapter`, `InMemoryMidiConnectionIO`
- `tests/test_appliers.py` — patched `builtins.input` calls replaced with fake adapters
- `tests/test_apply.py` — patched `builtins.input` calls replaced with fake adapters

### Applier files (call sites for ConfirmationIO)
- `src/rig/engine/appliers/analog.py` — `AnalogApplier` calls `confirmation_io.prompt_analog`
- `src/rig/engine/appliers/midi_device.py` — `MidiApplier` calls `confirmation_io.prompt_device`
- `src/rig/engine/appliers/chase_bliss.py` — `ChaseBlissApplier` calls `confirmation_io.prompt_cba_*`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `update_device_state(state, device, **fields)` in `base.py:39` — all state mutations go through this; `InMemoryStateAdapter.write_state` must use the same `RigState` model
- `DeviceApplyResult` and `ApplyContext` dataclass in `base.py` — `ApplyContext` is the struct being extended
- `DeviceApplier` Protocol in `base.py` — proof of pattern for the new Protocols in `ports.py`

### Established Patterns
- `@dataclass` for `ApplyContext` (not Pydantic) — keep this; just add the required `confirmation_io` field
- `Protocol` classes for structural subtyping — already established in `base.py`; `ports.py` follows the same pattern
- `Literal` return types — `_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]` in `interaction/analog.py`; all five `ConfirmationIO` methods return this type

### Integration Points
- `cli.py` — instantiates production adapters and passes them to `apply_plan`; this is the only wiring point
- `apply.py` — `apply_plan` is the single function gaining the two new params; no other public API changes
- All three appliers call `ctx.confirmation_io.*` instead of importing from `interaction.*` directly

</code_context>

<specifics>
## Specific Ideas

No specific requirements — implementation follows REQUIREMENTS.md DEC-01 through DEC-07 exactly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-engine-i-o-decoupling*
*Context gathered: 2026-06-04*
