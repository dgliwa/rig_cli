# Phase 32: Per-Parameter Plan Diffs - Research

**Researched:** 2026-06-22
**Domain:** Plan compute engine, Pydantic models, CLI output
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `ParamDiff` Pydantic model with fields `name: str`, `before: float | str | bool | None`, `after: float | str | bool`
- `DeviceAction` gains `param_diff: list[ParamDiff] = []`
- Analog: extract `AnalogPreset.values`, Digital (CBA): extract `DigitalPreset.parameters`, HX/MIDI-generic: empty diff
- Display sub-lines under action line: `  gain: 5.0 → 8.0`; `before=None` shown as `? → 8.0`
- If `before_preset` ID from state.json no longer exists in presets list, treat all after-params as `before=None`
- JSON output (`--format json`) includes param_diff automatically via `model_dump_json()`
- No changes to `apply`, `state.py`, or plugin protocols — display-only change

### Claude's Discretion
- Helper function name and location for `_compute_param_diff`
- Exact indentation depth of sub-lines in CLI output
- Whether `VERIFY` status actions also show a param diff when same preset (recommendation: no)

### Deferred Ideas (OUT OF SCOPE)
- Parsing HX `.hlx` binary file to extract block-level parameters
- Writing parameter diffs back to state.json
- Showing CC numbers alongside parameter names
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAN-01 | `rig plan` per device-action lists each parameter with `before:` and `after:` values when changed | `_compute_param_diff` helper in compute.py, new `ParamDiff` model, display loop in plan.py |
| PLAN-02 | Parameters unchanged within a "changed" scene are not listed; JSON format includes parameter diff structure | Diff algorithm filters to changed-only; Pydantic `model_dump_json()` auto-includes new field |
</phase_requirements>

## Summary

Phase 32 adds parameter-level diff detail to `rig plan` output. The plan engine currently tracks only preset IDs (`before: str | None`, `after: str`); the new work extends `DeviceAction` with a `param_diff: list[ParamDiff]` list that captures which knob positions or CC values are changing and their old/new values.

The data already exists in the right shape: `AnalogPreset.values` is a `dict[str, float | str | bool]` of human-readable knob names to positions; `DigitalPreset.parameters` is the same structure for CBA CC parameters. The `compute.py` function already has access to both preset objects and the `Rig` model — it just needs to look up the before/after preset objects and diff their parameter dicts. The CLI `plan.py` renders from `DeviceAction` fields, so adding the sub-line display is a self-contained change to the rendering loop.

`HXStompPreset` and `MidiPreset` carry no per-parameter data (only `preset_number` / `hlx_file`), so their `param_diff` is always an empty list. The `VERIFY` status actions (unchanged preset) should not show a diff. `CONFIGURE` and `ANALOG` status actions are the targets.

**Primary recommendation:** Add `ParamDiff` to `models.py`, add the lookup helper `_compute_param_diff` to `compute.py`, and extend the per-action rendering block in `plan.py`. All three files are in `packages/rig/src/rig/engine/plan/` and `packages/rig/src/rig/cli/commands/`. No new dependencies, no schema changes to state.json. [VERIFIED: codebase grep]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ParamDiff model definition | Engine / models.py | — | Plan models live in `rig/engine/plan/models.py` next to `DeviceAction` |
| Parameter diff computation | Engine / compute.py | — | `compute_plan` already accesses `rig.devices`, preset lists, and state |
| Parameter diff display | CLI / plan.py | — | All rendering from `DeviceAction` fields is already in this file |
| JSON output | CLI / plan.py (via Pydantic) | — | `model_dump_json()` auto-includes new field — no CLI change needed |

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0 | `ParamDiff` model definition | Project standard for all domain models [VERIFIED: codebase grep / pyproject.toml] |
| Python typing (`Literal`, union syntax) | 3.12+ | Field types | Project uses `|` union syntax throughout [VERIFIED: codebase grep] |

### No new packages needed

This phase is entirely within the existing Python/Pydantic/Typer/Rich stack. No new `pip install` calls.

## Package Legitimacy Audit

> No new packages are installed in this phase. This section is intentionally empty.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
rig plan (CLI)
      |
      v
load_rig(config)  ->  Rig (devices + presets in memory)
      |
      v
compute_plan(rig, root_path)
      |
      +-- read_state(root_path)  ->  RigState (last_preset per device)
      |
      +-- for each scene / device:
      |       actual_preset_id = state.devices[device].last_preset  (str | None)
      |       before_preset = lookup(device.presets, actual_preset_id)  (NEW)
      |       after_preset  = lookup(device.presets, preset_id)         (NEW)
      |       param_diff    = _compute_param_diff(before_preset, after_preset) (NEW)
      |
      +-- DeviceAction(... param_diff=param_diff)
      |
      v
ScenePlan / Plan  (Pydantic model — auto-serializes param_diff in model_dump_json)
      |
      v
plan.py  (CLI render)
      |
      +-- for each action with param_diff:
              print action line
              for each ParamDiff entry:
                  print "  name: before → after"
```

### Recommended Project Structure (unchanged)

```
packages/rig/src/rig/
  engine/plan/
    models.py          ← add ParamDiff class + param_diff field to DeviceAction
    compute.py         ← add _compute_param_diff helper, call it in compute_plan
  cli/commands/
    plan.py            ← extend rendering loop to print param_diff sub-lines
packages/rig/tests/
  test_plan.py         ← unit tests for param_diff computation
  test_cli_plan.py     ← integration tests for param_diff CLI output
```

### Pattern 1: ParamDiff Model

Place `ParamDiff` above `DeviceAction` in `models.py`. Follow existing style: `from __future__ import annotations`, Pydantic `BaseModel`, union with `|` syntax.

```python
# Source: existing models.py pattern (codebase)
class ParamDiff(BaseModel):
    name: str
    before: float | str | bool | None  # None when no prior state known
    after: float | str | bool
```

Add to `DeviceAction`:
```python
param_diff: list[ParamDiff] = []
```

### Pattern 2: _compute_param_diff Helper

Location: top-level function in `compute.py`, placed alongside `_get_preset_number`. The function is a pure function — no side effects, takes two optional preset objects (from `rig.models.preset.Preset` or its subclasses).

```python
# Source: codebase analysis of AnalogPreset.values / DigitalPreset.parameters
def _compute_param_diff(
    before_preset: object | None,
    after_preset: object,
) -> list[ParamDiff]:
    """Compare parameter dicts of two preset objects.

    Returns only entries that changed (or all after-params if before is None).
    Devices with no parameter dict (HX, MidiPreset) return [].
    """
    after_params: dict[str, float | str | bool] = {}
    if hasattr(after_preset, "values"):
        after_params = after_preset.values          # AnalogPreset
    elif hasattr(after_preset, "parameters"):
        after_params = after_preset.parameters      # DigitalPreset (CBA)
    # else: HXStompPreset / MidiPreset → no params, return []

    if not after_params:
        return []

    before_params: dict[str, float | str | bool] = {}
    if before_preset is not None:
        if hasattr(before_preset, "values"):
            before_params = before_preset.values
        elif hasattr(before_preset, "parameters"):
            before_params = before_preset.parameters

    diffs: list[ParamDiff] = []
    for key, after_val in after_params.items():
        before_val = before_params.get(key)  # None if no before_preset or key absent
        if before_preset is None or before_val != after_val:
            diffs.append(ParamDiff(name=key, before=before_val, after=after_val))
    return diffs
```

### Pattern 3: Preset Lookup Helper

`compute.py` already has `_get_preset_number` which iterates `device.presets`. Follow the same pattern for the before/after preset object lookup:

```python
def _find_preset(rig: Rig, pedal_id: str, preset_id: str | None) -> object | None:
    if preset_id is None:
        return None
    device = rig.devices.get(pedal_id)
    if device is None:
        return None
    return next((p for p in device.presets if p.id == preset_id), None)
```

### Pattern 4: Calling Site in compute_plan

The calling site in `compute.py` builds `DeviceAction` on two code paths: the analog branch (lines 89-104) and the digital/modeler branch (lines 116-127). Both need `param_diff`. Extract the before/after preset objects before the branch, then pass `param_diff` to `DeviceAction`.

```python
# In the per-pedal loop, before the analog/digital branch:
before_preset = _find_preset(rig, pedal_id, actual_preset)
after_preset  = _find_preset(rig, pedal_id, preset_id)
param_diff    = _compute_param_diff(before_preset, after_preset)

# Then pass to DeviceAction in both branches:
DeviceAction(
    ...,
    param_diff=param_diff,
)
```

### Pattern 5: CLI Display Extension

The rendering loop in `plan.py` (lines 97-114) already handles three `ActionStatus` cases. Extend ANALOG and CONFIGURE cases with sub-line output:

```python
# After the action line is printed, in both ANALOG and CONFIGURE branches:
for diff in action.param_diff:
    before_str = "?" if diff.before is None else str(diff.before)
    console.print(f"      {diff.name}: {before_str} -> {diff.after}")
```

The indentation depth: action lines use 4 spaces (`"    "`). Sub-lines should use 6 spaces (`"      "`) to nest visually beneath the action line. This matches the display sketch in CONTEXT.md.

`VERIFY` status actions do NOT show param_diff (the preset is unchanged — no diff is meaningful even if one were computed).

### Pattern 6: JSON Output

The JSON path in `plan.py` (line 60):
```python
_emit_json(result.model_dump_json(indent=2))
```

Because `Plan -> ScenePlan -> DeviceAction -> list[ParamDiff]` are all Pydantic `BaseModel`, adding `param_diff` to `DeviceAction` causes it to appear in the JSON output automatically. No changes needed in `plan.py` for the JSON path.

### Anti-Patterns to Avoid

- **Storing param_diff in state.json:** This phase is display-only. Do not add `param_diff` to `DeviceState` or `RigState`. The diff is computed fresh each time from the preset objects in the Rig model.
- **Coupling param extraction to CBA catalog:** Do not import or call `get_controls()` in `compute.py`. The `DigitalPreset.parameters` dict already uses human-readable names (`gain_1`, `mix`, etc.) — the catalog is for CC lookup during apply, not for plan display.
- **Showing param_diff on VERIFY actions:** A VERIFY action means the preset is already correct. A param_diff on a VERIFY action would be misleading (it would show no changes, or incorrectly show "all params match"). Skip it.
- **Using `isinstance` checks in _compute_param_diff:** Use `hasattr` instead, consistent with how `_detect_unused_presets` in `compute.py` checks `hasattr(preset, "values")`. This keeps the function decoupled from plugin-specific import paths.
- **Putting ParamDiff in the wrong package:** `ParamDiff` belongs in `packages/rig/src/rig/engine/plan/models.py` — the same module as `DeviceAction`. It is a plan-layer concern, not a preset-layer concern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization of nested models | Custom `__dict__` or `to_json()` method | Pydantic `model_dump_json()` | Already called on `Plan` in `plan.py` line 60; nested models serialize automatically |
| Optional field defaults | Manual `None` guard in every constructor call | Pydantic `= []` default on `param_diff` | Existing `DeviceAction` fields use the same pattern (e.g. `instructions: list[str] = []`) |

## Common Pitfalls

### Pitfall 1: before_preset None vs before_preset with empty parameters

**What goes wrong:** A `DigitalPreset` with `parameters: {}` (empty dict) and `before_preset=None` both produce an empty `param_diff`. If the caller checks `if before_preset is None` to decide "show all after-params as new", an empty-parameter digital preset will output nothing — which is correct, but the code path looks the same as the HX case.

**Why it happens:** `DigitalPreset.parameters = {}` is the default. Most CBA presets in the wild have no parameters if the user only set the preset number. The diff algorithm will correctly produce `[]` in both cases.

**How to avoid:** The algorithm "iterate `after_params` keys" naturally handles it: if `after_params` is empty, the loop body never executes.

**Warning signs:** Tests with `DigitalPreset(parameters={})` will have `param_diff == []` even when `before_preset is None`. This is correct behavior.

### Pitfall 2: before_preset ID present in state.json but deleted from presets list

**What goes wrong:** User removes a preset from their YAML after applying. `actual_preset_id` in state.json refers to a preset that no longer exists in `device.presets`. `_find_preset` returns `None`, meaning `before_preset=None`.

**Why it happens:** State is a historical snapshot; config can diverge from it.

**How to avoid:** `_find_preset` returning `None` when preset ID is not found is the correct behavior. The CONTEXT.md explicitly requires this: "treat all after-params as having `before=None`." The diff will show `? → value` for every after-param. [VERIFIED: CONTEXT.md]

**Warning signs:** If you see `? →` for every parameter, the before-preset was deleted from config.

### Pitfall 3: Confusing DigitalPreset with MidiPreset

**What goes wrong:** `MidiPreset` (in `packages/rig/src/rig/models/preset.py`) is the generic MIDI preset used by `HXStompDevice` when `device.type != MODELER`. It has only `preset_number`, no `parameters`. `DigitalPreset` (in `packages/rig-chasebliss/`) is CBA-specific and has `parameters`.

**Why it happens:** Both have `preset_number`. The `hasattr(preset, "parameters")` check correctly distinguishes them.

**How to avoid:** Use `hasattr` duck typing, not `isinstance`. `MidiPreset` has no `parameters` attribute, so `hasattr(preset, "parameters")` returns `False` — the diff correctly returns `[]`.

**Warning signs:** If a non-CBA MIDI device shows parameter diffs, check `hasattr` logic.

### Pitfall 4: Rich markup in parameter names or values

**What goes wrong:** If a preset parameter value contains square brackets (e.g. `"[loop]"` as a toggle position), Rich will attempt to parse it as markup.

**Why it happens:** `console.print(f"... {diff.after}")` passes raw strings to Rich.

**How to avoid:** Use Rich's escape mechanism or plain string formatting: wrap values in `[default]{diff.after}[/default]` or use `console.print(..., markup=False)` if values are user-supplied strings. Check catalog: most CBA toggle `positions` are snake_case strings without brackets (e.g. `"reverb"`, `"tape"`, `"full_sun"`), so this is low risk in practice. Still worth being defensive.

**Warning signs:** RuntimeError or garbled output for toggle-type parameters.

### Pitfall 5: Param diff on ANALOG VERIFY actions is meaningless

**What goes wrong:** An analog device that matches state gets `ActionStatus.VERIFY`. Displaying `param_diff` sub-lines for a VERIFY action implies something is changing, which it isn't.

**Why it happens:** `_compute_param_diff` runs on all actions including VERIFY ones if wired naively.

**How to avoid:** Only render `param_diff` sub-lines for `ANALOG` and `CONFIGURE` status actions. Skip for `VERIFY`. Alternatively, skip computing `param_diff` entirely for VERIFY actions in `compute.py` (set to `[]`). The latter is cleaner — it avoids storing unnecessary data on the model.

## Code Examples

### Test Builder Pattern (existing, for reference)

```python
# Source: packages/rig/tests/test_plan.py _make_rig()
tum = FakeDevice(
    id="tumnus",
    type=DeviceType.ANALOG,
    config={"type": "manual"},
    presets=[
        AnalogPreset(
            id="edge-of-breakup",
            pedal="tumnus",
            name="Edge of Breakup",
            values={"gain": 5.0, "tone": 3},
        )
    ],
)
```

### New Test Pattern (param_diff)

```python
# Unit test in test_plan.py — no CLI involved, tests compute_plan directly
def test_analog_param_diff_shows_changed_knobs(self, tmp_path):
    tum = FakeDevice(
        id="tumnus",
        type=DeviceType.ANALOG,
        config={"type": "manual"},
        presets=[
            AnalogPreset(id="crunch",  values={"gain": 8.0, "tone": 7}),
            AnalogPreset(id="edge",    values={"gain": 5.0, "tone": 7}),
        ],
    )
    ctrl = FakeDevice(
        id="mc6", type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"s": {"presets": {"tumnus": "crunch"}}},
            type="controller", midi_channel=1, banks=[],
        ),
    )
    rig = Rig(name="t", signal_chain=[], devices={"tumnus": tum, "mc6": ctrl})
    state = tmp_path / ".rig" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}}))
    plan = compute_plan(rig, root_path=str(tmp_path))
    action = plan.scenes["s"].device_actions[0]
    assert len(action.param_diff) == 1   # only "gain" changed
    assert action.param_diff[0].name == "gain"
    assert action.param_diff[0].before == 5.0
    assert action.param_diff[0].after == 8.0
```

### CLI Sub-line Display Pattern

```python
# Extension to the ANALOG / CONFIGURE rendering in plan.py
for diff in action.param_diff:
    before_str = "?" if diff.before is None else str(diff.before)
    console.print(f"      {diff.name}: {before_str} -> {diff.after}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Preset-level only: `before: "edge"`, `after: "crunch"` | + `param_diff: [ParamDiff(name="gain", before=5.0, after=8.0)]` | Phase 32 | Plan output now shows what specifically to change on the hardware |

**Deprecated/outdated:**
- None — this is purely additive.

## Open Questions

1. **Should VERIFY actions compute param_diff?**
   - What we know: VERIFY means the preset is already correct (before == after).
   - What's unclear: A user might still find it useful to see current values for a "verify" device.
   - Recommendation: Skip computing `param_diff` for VERIFY actions in `compute.py` (set to `[]`). Showing diffs on unchanged actions is confusing. This is an easy change later if needed.

2. **Should unchanged-but-new-scene analog actions show all params as `? → value`?**
   - What we know: CONTEXT.md says "if `before_preset` is None, show all after-params". A brand-new scene (no state.json entry) has `before_preset=None`.
   - What's unclear: For a new scene with no state, ALL parameters will show `? → value`. This may be verbose.
   - Recommendation: Follow the spec as written — show all params as `? → value` for new scenes. The verbosity is intentional and helps the user know what they're setting.

## Environment Availability

> Step 2.6 SKIPPED — this phase is purely code changes with no external tool dependencies. All tests run via `uv run pytest`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (dev dependency in pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/rig/tests/test_plan.py -q` |
| Full suite command | `uv run pytest packages/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAN-01 | Analog action `param_diff` shows changed knob positions | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-01 | Digital (CBA) action `param_diff` shows changed CC params | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-01 | `before=None` when no prior state | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-01 | HX Stomp action has `param_diff == []` | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-01 | VERIFY actions have `param_diff == []` | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-01 | CLI prints parameter sub-lines under action line | integration | `uv run pytest packages/rig/tests/test_cli_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-02 | Unchanged params not included in `param_diff` | unit | `uv run pytest packages/rig/tests/test_plan.py -q -k param_diff` | ❌ Wave 0 |
| PLAN-02 | JSON output includes `param_diff` field | integration | `uv run pytest packages/rig/tests/test_cli_plan.py -q -k json` | ❌ Wave 0 |
| PLAN-02 | CLI hides unchanged-params sub-lines (no noise) | integration | `uv run pytest packages/rig/tests/test_cli_plan.py -q -k param_diff` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/rig/tests/test_plan.py -q`
- **Per wave merge:** `uv run pytest packages/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `packages/rig/tests/test_plan.py` — add `TestParamDiff` class (unit tests for `_compute_param_diff` logic)
- [ ] `packages/rig/tests/test_cli_plan.py` — add tests for `--format text` sub-line output and `--format json` field presence

*(Existing test infrastructure and conftest.py `FakeDevice` pattern covers all test fixtures needed — no new conftest required)*

## Security Domain

> `security_enforcement` is enabled. ASVS Level 1 applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | Parameter values come from the user's own YAML config, not external input. Pydantic validates types at load time. |
| V6 Cryptography | no | — |

### Known Threat Patterns

No external input surfaces. Parameter values originate from user-controlled YAML parsed by `yaml.safe_load()` and validated by Pydantic models. The plan command is read-only and writes nothing to disk. No security-relevant changes in this phase.

## Runtime State Inventory

> Not a rename/refactor/migration phase. SKIPPED.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `VERIFY` actions should NOT show `param_diff` | Design Sketch / Pitfalls | Low — easy to reverse. Only affects verbosity, not correctness. |
| A2 | Rich `console.print` with plain `str()` conversion of bool/float values will not cause markup errors for current CBA parameter values | Pitfall 4 | Low — CBA catalog positions are snake_case strings. But toggle values like `"in"` or `"loop"` are safe. |

**If this table is empty:** Not applicable — two low-risk assumptions noted above.

## Sources

### Primary (HIGH confidence)
- `packages/rig/src/rig/engine/plan/models.py` — exact `DeviceAction` fields [VERIFIED: codebase grep]
- `packages/rig/src/rig/engine/plan/compute.py` — `compute_plan` data flow [VERIFIED: codebase grep]
- `packages/rig/src/rig/cli/commands/plan.py` — rendering loop [VERIFIED: codebase grep]
- `packages/rig-analog/src/rig_analog/preset.py` — `AnalogPreset.values` type [VERIFIED: codebase grep]
- `packages/rig-chasebliss/src/rig_chasebliss/preset.py` — `DigitalPreset.parameters` type [VERIFIED: codebase grep]
- `packages/rig-hx/src/rig_hx/preset.py` — `HXStompPreset` has no parameters [VERIFIED: codebase grep]
- `packages/rig/src/rig/models/preset.py` — `MidiPreset` has no parameters [VERIFIED: codebase grep]
- `packages/rig/tests/test_plan.py` — existing test patterns [VERIFIED: codebase grep]
- `packages/rig/tests/conftest.py` — `FakeDevice` fixture definition [VERIFIED: codebase grep]
- `.planning/phases/32-per-parameter-plan-diffs/CONTEXT.md` — locked design decisions [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` — CBA parameter names are human-readable (`gain_1`, `mix`, `wet_channel`) — confirms display value is the right field [VERIFIED: codebase grep]
- `packages/rig/src/rig/engine/state.py` — `DeviceState.last_preset: str | None` confirmed [VERIFIED: codebase grep]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed; no new packages needed
- Architecture: HIGH — all code paths read directly from source; no assumptions about framework behavior
- Pitfalls: HIGH — derived from actual codebase analysis of types, existing patterns, and CONTEXT.md constraints

**Research date:** 2026-06-22
**Valid until:** Stable — internal refactoring phase with no external dependencies
