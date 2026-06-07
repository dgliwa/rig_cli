---
phase: 5
plan: P6
type: gap-closure
wave: 4
depends_on: [P5]
files_modified:
  - src/rig/engine/plan/compute.py
  - src/rig/engine/appliers/chase_bliss.py
  - tests/test_appliers.py
requirements: [PLAN-10, D-10]
must_haves:
  - detect_cba_setup is NOT imported or called in chase_bliss.py
  - _enqueue_new_actions() function is removed from ChaseBlissApplier
  - apply_setup() executes only the actions list passed to it; no dynamic re-queuing
  - detect_cba_setup() produces establish_channel + all build_preset + register_scenes in a single call for a fresh device (channel_established=False)
  - detect_cba_setup() does NOT include establish_channel when channel_established=True
  - detect_cba_setup() does NOT include build_preset for already-saved presets
  - detect_cba_setup() does NOT include register_scenes when registration_done=True
  - A single rig apply run converges a fresh CBA device through all 3 phases without re-running the command
  - Existing 8 applier tests continue to pass
  - New test confirms a fresh device (channel_established=False) with 2 presets produces establish_channel + 2x build_preset + register_scenes from a single detect_cba_setup() call
  - New test confirms no actions are dynamically appended after a confirmed establish_channel in apply_setup()
---

# Phase 5 P6: Fix CBA single-apply convergence (PLAN-10 gap)

## Context

The phase 5 VERIFICATION.md identified 1 blocker: PLAN-10 is not satisfied.

PLAN-10 requires that `apply_plan()` consumes the pre-computed `Plan` as the canonical action list.
Decision D-10 states: "`detect_cba_setup` is removed from the apply path — the plan is authoritative."

Currently, `ChaseBlissApplier._enqueue_new_actions()` in `src/rig/engine/appliers/chase_bliss.py`
(lines 33–39) re-calls `detect_cba_setup(ctx.rig, ctx.state)` during apply execution, each time
an `establish_channel` or `build_preset` action is confirmed. This is necessary today because
`detect_cba_setup()` is incremental: when `channel_established=False`, it returns only
`establish_channel` and skips phases 2 and 3 (the `continue` at line 48). So the plan only
ever contains one phase at a time.

The fix has two parts:

**Part 1 — Make `detect_cba_setup()` forward-looking.** Remove the `continue` at line 48 and
drop the `not has_unsaved` guard on `register_scenes`. A fresh device should produce all 3
phases in one call: `establish_channel` + all `build_preset` actions + `register_scenes`. The
plan is then complete and authoritative.

**Part 2 — Remove `_enqueue_new_actions` from `chase_bliss.py`.** Once the plan is complete
upfront, apply_setup() just executes the passed actions list in order. No runtime re-detection.

### Correct behavior after this fix

A single `rig apply` run on a fresh CBA device:
1. Executes `establish_channel` (state: `channel_established=True`)
2. Executes `build_preset` for each unsaved preset (state: presets marked saved one by one)
3. Executes `register_scenes` (state: `registration_done=True`)

All in one invocation. Subsequent runs produce no CBA setup actions (all phases already done).

---

## Task P6-T1: Fix detect_cba_setup() in compute.py

**File:** `src/rig/engine/plan/compute.py`

Read the file before editing. Make two changes inside `detect_cba_setup()`:

**1. Remove the `continue` at line 48:**

Change:
```python
        # Channel not established → skip rest until it is
        continue
```
to nothing — delete those two lines entirely. Phases 2 and 3 should be computed regardless.

**2. Drop the `not has_unsaved` guard on register_scenes (line 69):**

Change:
```python
        if not ds.registration_done and not has_unsaved:
```
to:
```python
        if not ds.registration_done:
```

No other changes to `detect_cba_setup()`. The phase 1, 2, and 3 logic blocks themselves are
correct; only the early-exit and the registration guard need removing.

---

## Task P6-T2: Remove _enqueue_new_actions from chase_bliss.py

**File:** `src/rig/engine/appliers/chase_bliss.py`

Read the file before editing. Make the following changes:

**1. Update import (line 13):**

Remove `detect_cba_setup` from the import. Change:
```python
from rig.engine.plan import CbaSetupAction, detect_cba_setup
```
to:
```python
from rig.engine.plan import CbaSetupAction
```

**2. Remove the `_enqueue_new_actions` nested function (lines 33–39) and its two call sites:**

Remove the entire `_enqueue_new_actions` definition:
```python
        def _enqueue_new_actions() -> None:
            if ctx.rig is None:
                return
            for a in detect_cba_setup(ctx.rig, ctx.state):
                key = (a.device, a.type, a.preset_id)
                if key not in seen:
                    pending.append(a)
```

Remove the `if result.status == "confirmed": _enqueue_new_actions()` block after
`establish_channel` and the same after `build_preset`.

The final `apply_setup` while-loop body should look like:

```python
        while pending:
            action = pending.pop(0)
            action_key = (action.device, action.type, action.preset_id)
            if action_key in seen:
                continue
            seen.add(action_key)

            if action.type == "establish_channel":
                result = self._establish_channel(action, ctx)
                if result is None:
                    return None
                results.append(result)

            elif action.type == "build_preset":
                result = self._build_preset(action, ctx)
                if result is None:
                    return None
                results.append(result)

            elif action.type == "register_scenes":
                result = self._register_scenes(action, ctx)
                if result is None:
                    return None
                results.append(result)

        return results
```

No other changes to `chase_bliss.py`. The `_establish_channel`, `_build_preset`, and
`_register_scenes` methods are unchanged.

---

## Task P6-T3: Update tests in test_appliers.py

**File:** `tests/test_appliers.py`

Add two tests to `TestChaseBlissApplierSetup`:

**Test 1 — detect_cba_setup produces all phases for a fresh device:**

```python
    def test_detect_cba_setup_fresh_device_produces_all_phases(self):
        from rig.engine.plan.compute import detect_cba_setup
        from rig.engine.state import RigState

        rig = _make_rig()  # use existing _make_rig() helper or create a minimal one inline
        state = RigState()  # empty state — channel_established=False for all devices

        actions = detect_cba_setup(rig, state)
        types = [a.type for a in actions]

        assert "establish_channel" in types
        assert "build_preset" in types
        assert "register_scenes" in types
        # establish_channel comes first
        assert types.index("establish_channel") < types.index("build_preset")
        assert types.index("build_preset") < types.index("register_scenes")
```

If no CBA device is present in the rig fixture used by existing tests, check the existing
`_make_ctx` and related helpers to find or build a minimal CBA-device rig. If a suitable fixture
isn't available, build one inline — a `Rig` with one `Device` that has a `ChaseBlissConfig` and
at least one `DigitalPreset`, and one `Scene` that references that device.

**Test 2 — apply_setup does not enqueue dynamically on confirm:**

```python
    def test_apply_setup_does_not_enqueue_actions_dynamically_on_confirm(self):
        ctx = _make_ctx(
            connected={"cba-mood"},
            confirmation_io=InMemoryPromptAdapter(side_effect=["confirm", "confirm"]),
        )
        actions = [self._ec_action(device="cba-mood", midi_channel=3)]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert len(results) == 1  # only the passed-in action; no dynamic additions
        assert results[0].status == "confirmed"
```

---

## Verification

```
uv run pytest tests/test_appliers.py -v
```

All existing 8 tests must pass. Both new tests must pass. Zero failures.

```
uv run pytest tests/ -q
```

Full suite must pass (266 + 2 = 268 or more). No regressions.

```
grep -n "detect_cba_setup" src/rig/engine/appliers/chase_bliss.py
```

Must return no output — no import, no call.

```
grep -n "_enqueue_new_actions" src/rig/engine/appliers/chase_bliss.py
```

Must return no output.

```python
# Smoke-check: fresh device produces all 3 phases in one detect_cba_setup call
uv run python -c "
from rig.engine.plan.compute import detect_cba_setup
from rig.engine.state import RigState
print('detect_cba_setup import ok')
"
```
