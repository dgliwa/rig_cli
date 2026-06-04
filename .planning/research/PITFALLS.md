# Domain Pitfalls

**Domain:** Guitar rig IaC CLI — Protocol-based decoupling, CBA tech-debt, plan command
**Researched:** 2026-06-04
**Scope:** Milestone issues #1 (I/O decoupling), #11 (ctx.state mutation), #12 (private symbol), #13 (plan command)

---

## Critical Pitfalls

### Pitfall 1: Protocol That Tests Can Satisfy But Production Code Cannot

**What goes wrong:** A `Protocol` for I/O (prompts, state writes, MIDI) looks clean in the abstract but forces the engine to pass a single monolithic context object rather than isolating each concern. Tests pass because `MagicMock` satisfies any protocol, but the real implementation can't be constructed without triggering side effects — so tests and prod use different call paths.

**Why it happens:** The current `ApplyContext` dataclass already has this shape: it bundles `midi`, `state`, `config_path`, and `rig` in one object. When adding Protocol abstractions, there is pressure to just wrap the context in a protocol rather than split the concerns.

**Consequences:** Tests that mock a fat protocol give false confidence. The engine logic still has implicit dependencies on prompt ordering, state mutation side effects, and MIDI connection state. Refactoring is not actually complete — it just moved the coupling.

**Prevention:** Define narrow, single-responsibility protocols:
- One protocol for prompt I/O (returns typed `Literal["confirm", "retry", "skip", "quit"]`)
- One protocol for state reads/writes (wraps `read_state`/`write_state`)
- MIDI is already close to a protocol boundary — keep it there

Do not add a "mega-protocol" that re-exposes the whole `ApplyContext`.

**Warning signs:**
- A protocol method takes `ApplyContext` as a parameter
- A `MagicMock()` satisfies a protocol but the real implementation requires 4+ constructor args
- Test helpers like `_make_ctx()` grow more than 3 fields

**Applies to:** Issue #1 (engine I/O decoupling)

---

### Pitfall 2: State Written Before User Confirms — Silent Data Corruption

**What goes wrong:** `apply.py:174` writes `state.scenes[sp.scene_name] = {}` unconditionally after the device loop, even when all devices were skipped. This means a scene with zero confirmed devices is recorded as "applied" in state. On the next `plan` run, those scenes appear `unchanged` and the user never sees them again.

**Why it happens:** The scene-level state write is outside the per-device loop. The intent is to mark the scene as "visited," but the guard on `state_modified` only covers whether to flush state to disk — not whether the scene write itself is appropriate.

**Consequences:** A user who skips all devices in a scene (power was off, MIDI disconnected) will find the next `plan` shows no changes. The real device state is unknown, but state.json says it's fine. On a rig with analog pedals, this means silently lost instructions.

**Prevention:** Only write a scene entry to state when at least one device in that scene returned `status == "confirmed"`. Add a test for the "all-skip" path that asserts the scene is absent from the written state.

**Warning signs:**
- `state.scenes[name] = {}` appears before the per-device result check
- Integration test for "skip all" checks state file exists but not scene contents

**Applies to:** Issue #1 (decoupling), Issue #13 (plan command depends on scene state accuracy)

---

### Pitfall 3: `_detect_cba_setup` Called Twice — Plan and Apply Diverge

**What goes wrong:** `_detect_cba_setup` is called in `compute_plan` (to build the plan) and then called again inside `ChaseBlissApplier.apply_setup` via `_enqueue_new_actions`. If any state mutation happens between plan time and apply time — including mid-apply mutations inside the setup loop — the re-detection produces a different action list than what the plan showed. The plan is no longer the canonical description of what will happen.

**Why it happens:** The CBA setup is stateful (channel → presets → registration must happen in order), and the original design re-detects to handle the case where confirming "establish_channel" unlocks the "build_preset" step. This was a pragmatic shortcut, acknowledged with a TODO in plan.py:219.

**Consequences:**
- `plan` output is not trustworthy — it can't fully enumerate what `apply` will do
- Tests of the plan in isolation pass, but the actual apply does more work than the plan describes
- New phases added to CBA setup (e.g., SysEx-based preset verification) will silently appear in apply without being visible in plan output

**Prevention:** When refactoring for issue #1 or #12, make plan output fully self-contained: if the plan shows `establish_channel` only, apply should not inject `build_preset` mid-run. Instead, after a confirmed `establish_channel`, the apply result should signal "re-plan needed" or the plan should precompute the full action sequence with conditional ordering already resolved.

**Warning signs:**
- `_detect_cba_setup` is imported in `appliers/chase_bliss.py` (line 9 already shows this)
- Any `apply_setup` method calls a function that reads from `rig` — that's plan-time logic leaking into apply-time

**Applies to:** Issue #12 (private symbol promotion), Issue #13 (plan command correctness)

---

### Pitfall 4: `compute_plan` Silently Treats Missing `root_path` as Fresh State

**What goes wrong:** `compute_plan(rig)` with no `root_path` starts from an empty `RigState`. Every scene appears as `new`, every CBA device needs full setup. There is no warning. If a caller omits `root_path` by accident — say, wiring up the new `plan` CLI command without threading the config path through — the plan looks valid but is maximally noisy.

**Why it happens:** The signature `root_path: str | None = None` with `RigState()` fallback was originally there for tests. There is no `# TODO` or warning — CONCERNS.md documents it but the code has only a bare `TODO: issue #13` comment.

**Consequences:** A user running `rig plan` in a rig repo with a fully-applied state sees a plan showing 8 actions because the CLI forgot to pass the repo path. This is indistinguishable from a genuinely fresh state. The user might run `rig apply` and overwrite a working setup.

**Prevention:** When implementing the `plan` CLI command, emit a log warning (or console note) when `root_path` is None: "No state file found — treating as fresh rig." Alternatively, make `root_path` required in `compute_plan` and let callers explicitly pass `None` as `fresh=True`.

**Warning signs:**
- CLI command handler for `plan` does not assert or log when no `.rig/state.json` is found
- Test for `plan` command passes without a state file fixture

**Applies to:** Issue #13 (plan command)

---

### Pitfall 5: `compute_diff` Labels Every Existing Scene as "Changed"

**What goes wrong:** `diff.py:35` sets `_status: "changed"` unconditionally for any scene that exists in state. If all presets are already correct, the preset loop produces an empty dict, but the scene is still labeled `[~] changed`. The `format_diff` output is therefore misleading: it shows a scene header with no preset changes underneath.

**Why it happens:** The "changed vs. unchanged" discrimination lives in `compute_plan` but was not ported to `compute_diff`. CONCERNS.md documents this at the "changed" scene status bug entry.

**Consequences:** If `plan` and `diff` are surfaced together in the same milestone (issue #13 adds a `plan` command; the existing `diff` command lives alongside it), users see contradictory output: `diff` says scene X changed, `plan` says scene X is unchanged. Trust in the tooling erodes.

**Prevention:** Fix `compute_diff` before or alongside the `plan` command work. A scene should only appear in diff output if at least one preset actually changed. Add a regression test: scene exists in state with matching presets → diff output is `(no changes)`.

**Warning signs:**
- `test_diff.py` has no test for "scene in state, all presets match" → diff is empty
- CONCERNS.md calls this out explicitly

**Applies to:** Issue #13 (plan accuracy), general milestone quality

---

## Moderate Pitfalls

### Pitfall 6: `_build_preset` Mutates `presets_saved` by Direct Dict Construction

**What goes wrong:** `chase_bliss.py:209-212` updates `presets_saved` by extracting the dict, adding a key, and calling `model_copy`. This bypasses the `update_device_state` helper used everywhere else. If a second location also mutates `presets_saved` — e.g., during a retry or if the same device appears twice in a plan — the dict is silently overwritten rather than merged.

**Why it happens:** `update_device_state` accepts `**fields` kwargs which overwrite whole fields; it cannot do partial updates on a nested dict. Issue #11 documents `ctx.state` mutation inconsistency, but the `presets_saved` path was not fully standardized.

**Prevention:** When fixing issue #11, extend `update_device_state` or add a dedicated `save_preset_in_state(state, device, preset_id)` helper that handles the partial-dict update in one place. Assert in tests that calling the helper twice for two different preset IDs on the same device does not drop the first.

**Warning signs:**
- Any code that does `ps = dict(ds.presets_saved); ps[key] = True` outside the helper
- Test for `build_preset` only covers a single preset; no test covers two presets on the same device

**Applies to:** Issue #11 (ctx.state mutation)

---

### Pitfall 7: Protocol Structural Checking Does Not Catch Runtime Method Signature Drift

**What goes wrong:** Python `Protocol` uses structural subtyping checked only by type checkers (mypy/pyright), not at runtime. An implementor can have a method with a compatible name but different parameter order or an extra required argument. `isinstance(obj, MyProtocol)` returns `True` in all cases unless `runtime_checkable` is used — and even then, only method existence is checked, not signatures.

**Why it happens:** New protocols defined for issue #1 may look correct in test fixtures (which use `MagicMock`) but drift when the real applier adds a parameter. Without a type checker enforced in CI, the drift is invisible until runtime.

**Prevention:** Run `mypy` or `pyright` in CI with `strict` protocol checking. Do not rely on `isinstance` checks against Protocol types in production code. If the protocol is used as a type annotation only, that is correct — but add at least one test that instantiates the real implementor (not a mock) and calls through the protocol method.

**Warning signs:**
- `isinstance(obj, SomeProtocol)` in engine code
- No real-implementor integration test alongside unit tests that use mocks

**Applies to:** Issue #1 (engine I/O decoupling)

---

### Pitfall 8: `apply_plan` Reads State Again After `compute_plan` Already Read It

**What goes wrong:** `compute_plan` reads `state.json` once. `apply_plan` then calls `read_state` again from scratch. If the file is modified between the two calls (unlikely in interactive single-user usage, but possible on a fast machine or in tests that write state mid-run), the two views are inconsistent. The plan was computed against stale state, but apply executes against fresh state — or vice versa.

**Why it happens:** The plan and apply are designed as separate commands with no shared state object. The apply function defensively re-reads state rather than accepting the state the plan was computed against.

**Prevention:** The decoupling work in issue #1 is an opportunity to thread a single `RigState` snapshot through plan → apply. The `apply_plan` signature already accepts `plan: Plan` — extending it to also accept an optional `state: RigState` that bypasses the re-read is a minimal change. For the plan command specifically (issue #13), make the read a single I/O operation and document the snapshot contract.

**Warning signs:**
- `read_state` called in both `compute_plan` and `apply_plan` for the same config path
- Integration test passes a config path to both and doesn't assert they used the same snapshot

**Applies to:** Issue #1 (decoupling), Issue #13 (plan command)

---

## Minor Pitfalls

### Pitfall 9: `DeviceAction.status` Field Accepts "no_change" But `apply_plan` Skips It Inline

**What goes wrong:** `DeviceAction.status` has `"no_change"` as a valid literal. `apply_plan` checks `if action.status == "no_change": continue` inline in the scene loop. If a future code path forgets this guard (e.g., in a parallel applier or batch executor), `no_change` actions get passed to appliers that don't handle them, causing a silent no-op or worse, an unexpected prompt.

**Prevention:** Enforce the skip at the applier boundary, not only at the loop level. Each applier's `apply_scene` should return an early `DeviceApplyResult(status="skipped")` for `no_change` actions. This is defense in depth.

**Applies to:** Issue #1 (decoupling)

---

### Pitfall 10: Scene State Stored as Empty Dict Blocks Future Plan Accuracy

**What goes wrong:** `state.scenes[name] = {}` (apply.py:174) stores no useful information about what was actually applied to that scene. The plan command (issue #13) currently checks only `scene_name not in actual.scenes` to detect new scenes. Future plan improvements that want to track "which preset was active per-scene" have no data to work from.

**Prevention:** Even a minimal schema now prevents future migration pain. Write at minimum `{"applied_at": <timestamp>, "preset_versions": {device_id: preset_id}}` when a scene is confirmed. This is a low-cost change that makes issue #13's plan output more precise and avoids a state.json migration later.

**Applies to:** Issue #13 (plan command)

---

## Phase-Specific Warnings

| Phase / Issue | Likely Pitfall | Mitigation |
|---------------|---------------|------------|
| #1 — Protocol extraction | Fat protocol wrapping ApplyContext (Pitfall 1) | Define 3 narrow protocols; test with real implementors |
| #1 — I/O decoupling | State written for skipped scenes (Pitfall 2) | Guard scene state write behind confirmed-device count |
| #11 — ctx.state mutation | Direct dict mutation bypasses helper (Pitfall 6) | Add `save_preset_in_state` helper; test two-preset case |
| #12 — private symbol | Re-detection during apply diverges from plan (Pitfall 3) | Move all plan logic to plan-time; apply only executes |
| #13 — plan command | Missing root_path silently shows full plan (Pitfall 4) | Warn explicitly when no state file found |
| #13 — plan command | diff shows "changed" for clean scenes (Pitfall 5) | Fix compute_diff before surfacing plan alongside diff |
| #13 — plan command | apply re-reads state independently (Pitfall 8) | Thread RigState snapshot from plan into apply |
| Any Protocol work | Runtime signature drift undetected (Pitfall 7) | Enforce mypy/pyright in CI with one real-implementor test |

---

*Pitfall analysis based on direct codebase inspection: 2026-06-04*
