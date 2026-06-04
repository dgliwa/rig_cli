# Architecture: Apply Engine Decoupling

**Project:** rig-cli
**Milestone:** Decouple apply engine I/O (issues #1, #11, #12)
**Researched:** 2026-06-04
**Confidence:** HIGH (direct codebase analysis, no external sources needed)

---

## Current State: What Exactly Is Coupled

Before defining protocols, it is useful to name every coupling precisely.

### `apply_plan` in `src/rig/engine/apply.py`

The function is 150 lines that mixes four distinct concerns:

1. **User prompt I/O** — calls `prompt_midi_connect` (from `rig.interaction`) to ask which MIDI
   port to open. This is interactive `input()` that belongs at the CLI boundary.

2. **State mutation** — calls `update_device_state` and `write_state` directly, and also sets
   `state.scenes[sp.scene_name] = {}` inline (a raw dict mutation, not through the helper).

3. **MIDI I/O** — calls `midi.is_connected`, `midi.connect` via the MIDI connection phase.

4. **Console output** — `console.print(...)` called throughout the function body, not delegated
   to a renderer. Rich markup is embedded inside orchestration logic.

The `console = Console()` module-level singleton in `apply.py` is the same anti-pattern as the
one in each applier file — output is scattered across the call stack.

### `AnalogApplier` in `src/rig/engine/appliers/analog.py`

Calls `prompt_analog` (interactive `input()`) directly. Tests patch `builtins.input` globally,
which means the prompt function is not swappable without a process-level patch.

### `MidiApplier` in `src/rig/engine/appliers/midi_device.py`

Same coupling: calls `prompt_device` directly. Tests use `patch("builtins.input")`.

### `ChaseBlissApplier` in `src/rig/engine/appliers/chase_bliss.py`

Three couplings:

1. **Prompt calls** — `prompt_cba_channel`, `prompt_cba_build_preset`, `prompt_cba_register`
   called directly inside `_establish_channel`, `_build_preset`, `_register_scenes`.

2. **Private symbol import** (#12) — `from rig.engine.plan import ..., _detect_cba_setup`.
   `_detect_cba_setup` is a private function (underscore prefix) in the plan module; importing it
   from an applier creates a cross-layer private-symbol dependency.

3. **Inconsistent state mutation** (#11) — `_build_preset` directly constructs a new DeviceState
   object and assigns it to `ctx.state.devices[action.device]`, bypassing the
   `update_device_state` helper used everywhere else:
   ```python
   ds = ctx.state.devices.get(action.device, DeviceState())
   ps = dict(ds.presets_saved)
   ps[action.preset_id] = True
   ctx.state.devices[action.device] = ds.model_copy(update={"presets_saved": ps})
   ```
   This pattern leaks internal dict-construction logic that `update_device_state` should absorb.

---

## Proposed Architecture: Three Protocol Interfaces

### Protocol 1: `ConfirmationIO`

**File:** `src/rig/engine/appliers/base.py` (alongside existing `DeviceApplier` Protocol)

**Purpose:** Replaces direct `prompt_*` calls inside appliers. Any applier that needs user
confirmation goes through this interface instead of calling `rig.interaction` functions directly.

**Sketch:**
```python
from typing import Literal, Protocol

ConfirmResult = Literal["confirm", "retry", "skip", "quit"]

class ConfirmationIO(Protocol):
    def confirm_device(
        self,
        device: str,
        preset_name: str,
        preset_number: int | None,
        midi_channel: int | None,
        midi_connected: bool,
    ) -> ConfirmResult: ...

    def confirm_analog(self, device: str, preset_name: str) -> ConfirmResult: ...

    def confirm_cba_channel(
        self, device: str, midi_channel: int, midi_sent: bool
    ) -> ConfirmResult: ...

    def confirm_cba_build_preset(
        self, device: str, preset_name: str, preset_number: int | None, midi_channel: int
    ) -> ConfirmResult: ...

    def confirm_cba_register(self, device: str, scene_refs: list[str]) -> ConfirmResult: ...
```

**Production implementation:** `InteractiveConfirmationIO` in `src/rig/interaction.py`. This
class wraps the existing five standalone `prompt_*` functions — no logic moves, only a thin
adapter class is added on top.

**Test implementation:** `AutoConfirmationIO` (or a simple `MagicMock`) that returns a
pre-programmed sequence of `ConfirmResult` values. Tests no longer need `patch("builtins.input")`.

### Protocol 2: `MidiConnectionIO`

**File:** `src/rig/engine/appliers/base.py`

**Purpose:** Replaces the MIDI connection prompt block in `apply_plan` (Phase -1). Currently
`prompt_midi_connect` is called directly inside `apply_plan`, interleaving user I/O with
orchestration. This protocol covers the "which port do you want?" interaction.

**Sketch:**
```python
class MidiConnectionIO(Protocol):
    def connect_device(
        self,
        device_id: str,
        midi_channel: int,
        midi: MidiManager,
        cached_port: str | None,
    ) -> tuple[ConfirmResult, str | None]: ...
```

**Production implementation:** `InteractiveMidiConnectionIO` in `src/rig/interaction.py`, wrapping
the existing `prompt_midi_connect` function.

**Note:** This protocol is narrower than `ConfirmationIO` — it handles port selection UI,
which is inherently interactive and only relevant to the MIDI connection phase. Separating it
gives cleaner seam points and avoids an oversized protocol.

### Protocol 3: `StateWriter`

**File:** `src/rig/engine/state.py`

**Purpose:** Replaces direct `write_state(config_path, state)` calls in `apply_plan`.
Currently the apply engine calls the file I/O function directly, making it impossible to verify
state-write behavior in tests without filesystem setup.

**Sketch:**
```python
class StateWriter(Protocol):
    def write(self, state: RigState) -> None: ...
```

**Production implementation:** `FileStateWriter` in `src/rig/engine/state.py`, wrapping the
existing `write_state` function:
```python
class FileStateWriter:
    def __init__(self, root: str) -> None:
        self._root = root

    def write(self, state: RigState) -> None:
        write_state(self._root, state)
```

**Test implementation:** `NoOpStateWriter` or a mock that captures the state it was called with,
allowing tests to assert on final state without touching the filesystem.

---

## Updated `ApplyContext`

Once the three protocols are in place, `ApplyContext` in `src/rig/engine/appliers/base.py` gains
two additional fields:

```python
@dataclass
class ApplyContext:
    dry_run: bool
    midi: MidiManager | None = None
    connected_devices: set[str] = field(default_factory=set)
    state: RigState = field(default_factory=RigState)
    config_path: str | None = None
    rig: Rig | None = None
    confirmation_io: ConfirmationIO = field(default_factory=InteractiveConfirmationIO)
    state_writer: StateWriter | None = None   # None → no-op (dry_run or test path)
```

`MidiConnectionIO` is NOT added to `ApplyContext` because it is only used in the Phase -1
connection block of `apply_plan`, not inside individual appliers. It is passed as a parameter
to `apply_plan` instead (or constructed inline in the CLI entry point).

**Why `confirmation_io` goes in context but `MidiConnectionIO` does not:** Appliers are invoked
by the registry and receive `ctx` only. Appliers need `confirmation_io`. The MIDI connection
phase happens before appliers are dispatched and only `apply_plan` needs it directly.

---

## Tech-Debt Fixes: #11 and #12

### Fix #11: Consistent `presets_saved` mutation in `ChaseBlissApplier._build_preset`

The raw dict-construction pattern must be absorbed into `update_device_state`. The helper in
`src/rig/engine/appliers/base.py` already handles arbitrary `**fields` via `model_copy`, but
`presets_saved` is a nested dict, so a field-level merge is not enough. Two options:

**Option A (preferred):** Add `merge_preset_saved(state, device, preset_id)` as a named helper
in `src/rig/engine/appliers/base.py`:
```python
def mark_preset_saved(state: RigState, device: str, preset_id: str) -> None:
    ds = state.devices.get(device, DeviceState())
    updated = dict(ds.presets_saved)
    updated[preset_id] = True
    state.devices[device] = ds.model_copy(update={"presets_saved": updated})
```

Then `_build_preset` becomes:
```python
mark_preset_saved(ctx.state, action.device, action.preset_id)
```

This gives the operation a name and makes the dict-surgery invisible at the call site.

**Option B:** Add `presets_saved` as a supported kwarg to `update_device_state` with special
merge behavior. More flexible but requires the helper to know about the internal structure of
`DeviceState.presets_saved`. Option A is cleaner.

### Fix #12: Promote `_detect_cba_setup` to public API

`ChaseBlissApplier.apply_setup` imports `_detect_cba_setup` from `rig.engine.plan`. This creates
a cross-layer private-symbol dependency: an applier reaches into plan internals.

**Option A (minimal, preferred):** Rename `_detect_cba_setup` to `detect_cba_setup` in
`plan.py`. Update the import in `chase_bliss.py` and any test references. No module movement.

**Option B:** Move `detect_cba_setup` to a shared module, e.g. `src/rig/engine/cba.py`, so
it is not co-located with plan computation. This is cleaner for future CBA feature growth, but
adds a file and requires more import changes. Deferred to a later milestone.

Similarly, `_is_cba` in `plan.py` has the underscore prefix but is a pure utility. It should
also lose the underscore when #12 is fixed, or be replaced by a method on `ChaseBlissConfig`.

---

## Build Order (Dependency Graph)

Each step is a mergeable unit. Later steps depend on earlier ones being complete.

```
Step 1: Fix #11 — mark_preset_saved helper
  - Add mark_preset_saved to src/rig/engine/appliers/base.py
  - Update ChaseBlissApplier._build_preset to use it
  - Update tests/test_appliers.py: assertion unchanged, but no raw dict logic to verify
  - No protocol work required; standalone cleanup

Step 2: Fix #12 — rename _detect_cba_setup
  - Rename _detect_cba_setup → detect_cba_setup in src/rig/engine/plan.py
  - Update import in src/rig/engine/appliers/chase_bliss.py
  - Rename _is_cba → is_cba (same file) while touching the function
  - No protocol work required; standalone rename

Step 3: Define ConfirmationIO Protocol + InteractiveConfirmationIO
  - Add ConfirmationIO Protocol to src/rig/engine/appliers/base.py
  - Add InteractiveConfirmationIO class to src/rig/interaction.py wrapping existing prompt fns
  - No callers changed yet; this is additive only

Step 4: Thread ConfirmationIO into ApplyContext
  - Add confirmation_io field to ApplyContext with InteractiveConfirmationIO default
  - Update AnalogApplier, MidiApplier, ChaseBlissApplier to use ctx.confirmation_io
    instead of calling prompt_* directly
  - Update tests/test_appliers.py: replace patch("builtins.input") with
    ApplyContext(confirmation_io=<stub>)
  - Steps 1 and 2 must be complete first (cleaner base for CBA changes)

Step 5: Define StateWriter Protocol + FileStateWriter
  - Add StateWriter Protocol to src/rig/engine/state.py
  - Add FileStateWriter class to same file
  - No callers changed yet

Step 6: Thread StateWriter into apply_plan
  - Add state_writer parameter to apply_plan signature (default: None → skip write)
  - Replace write_state(config_path, state) call with state_writer.write(state)
  - CLI constructs FileStateWriter(config_path) before calling apply_plan
  - Update tests/test_apply.py: pass a capturing state_writer stub instead of
    using tmp_path filesystem assertions where the intent is to verify state content

Step 7: Define MidiConnectionIO Protocol + InteractiveMidiConnectionIO
  - Add MidiConnectionIO Protocol to src/rig/engine/appliers/base.py
  - Add InteractiveMidiConnectionIO to src/rig/interaction.py wrapping prompt_midi_connect
  - Add midi_connection_io parameter to apply_plan (default: InteractiveMidiConnectionIO())
  - Replace Phase -1 prompt_midi_connect call with midi_connection_io.connect_device(...)
  - Update tests/test_apply.py: TestMidiApply can now inject a stub instead of
    relying on patch("rig.midi.adapter.mido.*")
```

Steps 1 and 2 are independent of each other and can be done in either order. Steps 3-7 must
follow the dependency order shown. A single PR can bundle Steps 1+2 (pure cleanup), and a
second PR can implement Steps 3-7 (protocol introduction).

---

## How `plan` Command Fits the Existing Layer Model

The `plan` command (#13) is already partially supported: `compute_plan` in `plan.py` exists
and the `plan` CLI command exists. The milestone context notes that plan is "read-only against
state.json" with no MIDI.

After the decoupling work above, the plan command's position is clear:

```
CLI (plan command)
  └─ compute_plan(rig, root_path) → Plan
       └─ read_state(root_path)  [read-only, no write]
            └─ returns Plan (typed action list)
```

No `ApplyContext`, no `ConfirmationIO`, no `StateWriter`, no MIDI. The plan engine remains in
`src/rig/engine/plan.py` with only the `detect_cba_setup` rename (Step 2) as a visible change.

The output rendering (text table, JSON) belongs in `cli.py`, consistent with the principle that
formatting is a CLI concern. The Plan model already carries all the data needed to render both
formats (`status`, `scenes: dict[str, ScenePlan]`, `cba_setup: list[CbaSetupAction]`).

The one structural note for the plan command: `CbaSetupAction` lives on `Plan.cba_setup` as a
flat list, separate from `ScenePlan.device_actions`. The existing TODO comments in `plan.py`
(lines 219-224) acknowledge this is wrong. For the plan display command, this oddity is
cosmetic. Fix it in a later milestone if the separation causes rendering confusion.

---

## Existing Test Coverage: Impact Per Step

| Step | Files Affected | Change Type | Risk |
|------|---------------|-------------|------|
| 1 (#11 fix) | `tests/test_appliers.py` — `TestChaseBlissApplierSetup.test_build_preset_confirm_sends_ccs_and_updates_state` | State assertion unchanged, internal impl change | Low |
| 2 (#12 fix) | `tests/test_plan.py` — any tests importing `_detect_cba_setup` directly | Import rename only | Low |
| 3 (ConfirmationIO Protocol) | No test changes | Additive only | None |
| 4 (thread ConfirmationIO) | `tests/test_appliers.py` — all tests using `patch("builtins.input")` | Replace global patch with stub injection; test becomes simpler | Medium — test rewrite |
| 5 (StateWriter Protocol) | No test changes | Additive only | None |
| 6 (thread StateWriter) | `tests/test_apply.py` — `TestApplyPlan` filesystem assertions | Can use capturing stub; tmp_path still valid for integration tests | Low — optional improvement |
| 7 (MidiConnectionIO) | `tests/test_apply.py` — `TestMidiApply` | Can replace `patch("rig.midi.adapter.mido.*")` with stub; keep integration tests for confidence | Medium — optional improvement |

The existing `tests/test_apply.py::TestMidiApply` tests are integration-style: they exercise
`apply_plan` end-to-end with a real (mocked) MIDI library. These tests are valuable and should
be preserved even after refactoring. The protocol injection improves unit-testability of
individual phases but does not invalidate the integration tests.

The `tests/test_appliers.py` tests for `AnalogApplier` and `MidiApplier` use
`patch("builtins.input")` — a process-global patch that works but is fragile. After Step 4,
these tests should switch to injecting a `ConfirmationIO` stub via `ApplyContext`, eliminating
the global patch. The test logic (what is asserted) does not change; only the setup changes.

---

## Component Boundary Summary After Refactor

```
src/rig/interaction.py
  InteractiveConfirmationIO   (implements ConfirmationIO, wraps prompt_* fns)
  InteractiveMidiConnectionIO (implements MidiConnectionIO, wraps prompt_midi_connect)
  collect_midi_devices        (unchanged — pure function, no I/O)
  prompt_*                    (unchanged — kept as standalone fns for backward compat)

src/rig/engine/appliers/base.py
  ConfirmationIO              (new Protocol)
  MidiConnectionIO            (new Protocol)
  ApplyContext                (+ confirmation_io field, state_writer field)
  DeviceApplier               (unchanged)
  DeviceApplyResult           (unchanged)
  update_device_state         (unchanged)
  mark_preset_saved           (new helper, fixes #11)

src/rig/engine/state.py
  StateWriter                 (new Protocol)
  FileStateWriter             (new class)
  read_state / write_state    (unchanged)

src/rig/engine/appliers/analog.py
  AnalogApplier.apply_scene   uses ctx.confirmation_io.confirm_analog(...)

src/rig/engine/appliers/midi_device.py
  MidiApplier.apply_scene     uses ctx.confirmation_io.confirm_device(...)

src/rig/engine/appliers/chase_bliss.py
  imports detect_cba_setup (not _detect_cba_setup)
  uses ctx.confirmation_io.confirm_cba_*(...)
  uses mark_preset_saved(...) (not raw dict construction)

src/rig/engine/plan.py
  detect_cba_setup            (renamed from _detect_cba_setup, fixes #12)
  is_cba                      (renamed from _is_cba)
  compute_plan                (unchanged in behavior)

src/rig/engine/apply.py
  apply_plan(plan, rig, config_path, dry_run, scene, midi,
             midi_connection_io=..., state_writer=...)
  Phase -1 uses midi_connection_io.connect_device(...)
  Final write uses state_writer.write(state) instead of write_state(...)

src/rig/cli.py
  Constructs InteractiveConfirmationIO, InteractiveMidiConnectionIO, FileStateWriter
  Passes them into apply_plan (production path)
```

No new top-level packages. No moved files. All changes are additions within existing modules
plus targeted replacements of direct function calls with interface calls.

---

## Anti-Patterns to Avoid During This Refactor

### Over-abstracting the prompt interface

`ConfirmationIO` has five methods because the five existing prompt functions have distinct
signatures. Do not collapse them into a single generic `prompt(action_type, **kwargs)` dispatch.
Typed method signatures are the point — they make the interface checkable by mypy and greppable
by humans.

### Injecting `StateWriter` into appliers

`ctx.state` (a `RigState` mutable object) is the right place for in-flight state accumulation
during an apply run. Appliers should continue to mutate `ctx.state` via `update_device_state`.
`StateWriter` is only for the final persist step in `apply_plan`. Pushing `StateWriter` into
individual appliers would mean every `_build_preset` call writes to disk, which is wrong.

### Making `FileStateWriter` stateless

`FileStateWriter` must hold `root: str` because `write_state` needs the config path. Do not
try to make it a module-level singleton; each `apply` invocation constructs one with the
correct `config_path`.

---

*Architecture analysis: 2026-06-04. Confidence: HIGH — derived from direct code reading.*
