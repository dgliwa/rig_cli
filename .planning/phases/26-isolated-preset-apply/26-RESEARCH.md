# Phase 26: Isolated Preset Apply — Research

**Researched:** 2026-06-17
**Domain:** Python CLI (Typer) / apply engine extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Bypass the scene-based plan engine entirely. `--device`/`--preset` is a distinct execution mode — no call to `compute_plan`, no `Plan`/`ScenePlan` objects. CLI validates the device+preset exist in the `Rig` model, builds a `DeviceAction` directly, and calls a new `apply_device_preset()` function in `apply.py`.
- **D-02:** The new `apply_device_preset()` reuses `DeviceApplyContext` and `device.apply()` — it does NOT duplicate apply logic. Difference is it starts from a direct `DeviceAction`, not a scene loop.
- **D-03:** Call `setup()` only on the targeted device before `device.apply()`. Do not run setup for other devices.
- **D-04:** `--device` and `--preset` must be used together — providing one without the other is an error. `--scene` alongside `--device`/`--preset` is also an error. The two modes are exclusive.
- **D-05:** `--device` and `--preset` default to `None`. CLI routes to `apply_device_preset()` when both are present, or to existing `apply_plan()` when neither is present.
- **D-06:** Validate device ID and preset ID against the loaded `Rig` model immediately after loading config, before opening any MIDI ports. Use the existing `ConfigError` pattern.
- **D-07:** `apply_device_preset()` updates `state.devices[device_id]` only — not `state.scenes`. Scene state is intentionally left stale.

### Claude's Discretion

None listed.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRESET-01 | User can run `rig apply --device <id> --preset <id>` to apply one device's preset without triggering full scene setup | Covered by D-01/D-02: new `apply_device_preset()` in `apply.py`, routed from CLI |
| PRESET-02 | When `--device` and `--preset` flags are given, apply skips all other devices | Covered by D-03: `setup()` + `apply()` called on targeted device only |
| PRESET-03 | `rig apply --device <id> --preset <id>` updates `state.json` for the targeted device only | Covered by D-07: only `state.devices[device_id]` touched, `state.scenes` untouched |
</phase_requirements>

---

## Summary

This phase adds an isolated execution mode to `rig apply`: when `--device <id>` and `--preset <id>` are both provided, the engine applies exactly one device's preset, skips all others, and updates only that device's slice of `state.json`. The existing scene-based `apply_plan()` path is left unchanged.

The implementation adds one new function `apply_device_preset()` to `packages/rig/src/rig/engine/apply.py` and extends the CLI command in `packages/rig/src/rig/cli/commands/apply.py` with two optional flags. No plugin implementations change — they already satisfy the `Device` Protocol with `setup()` and `apply()`.

**Primary recommendation:** Follow D-01 through D-07 from CONTEXT.md exactly. The new path is a thin wrapper around the existing `DeviceApplyContext`/`device.apply()` pattern — do not invent new abstractions.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flag parsing and mutual-exclusion validation | CLI (`commands/apply.py`) | — | Typer owns option definitions; CLI enforces mode constraints before touching engine |
| Device/preset existence validation | CLI (`commands/apply.py`) | — | Must happen before MIDI ports open, consistent with D-06 and existing `ConfigError` pattern |
| Isolated preset apply logic | Engine (`apply.py`) | — | Keeps engine testable without CLI; mirrors `apply_plan()` placement |
| State persistence | Engine (`apply.py` via `StateWriter`) | — | `apply_device_preset()` calls `state_writer.write()` same as `apply_plan()` |
| Device setup + apply dispatch | Plugin layer (each device's `setup()`/`apply()`) | — | No change to plugins; engine dispatches per existing Protocol |

---

## Implementation Approach (D-01 through D-07)

### D-01/D-02: New `apply_device_preset()` function

Add to `packages/rig/src/rig/engine/apply.py` alongside `apply_plan()`. Accepts the targeted device and preset by ID, builds one `DeviceAction` inline, and calls `setup()` then `apply()` on the single device. Does **not** call `compute_plan`.

### D-03: Single-device setup

Construct `SetupContext` identically to `apply_plan()` but call `device.setup(setup_ctx)` for the targeted device only. If `result.cancelled`, print error and return early.

### D-04/D-05: CLI routing

`--device` and `--preset` both default to `None`. Routing logic:
- Both `None` → `apply_plan()` (existing path, unchanged)
- Both non-`None` → `apply_device_preset()`
- One non-`None`, other `None` → error + exit 1
- `--scene` non-`None` AND (`--device` or `--preset`) non-`None` → error + exit 1

### D-06: Validation order (before MIDI)

Immediately after `load_rig(config)` succeeds, before `MidiManager()` is constructed:
1. Check `device_id in rig.devices` — raise/print error if not
2. Obtain `device = rig.devices[device_id]`
3. Check `any(p.id == preset_id for p in device.presets)` — raise/print error if not

### D-07: State scope

`apply_device_preset()` reads state via `state_writer.read(config_path)`, updates only `state.devices[device_id]`, and writes back. Never touches `state.scenes`.

---

## New Function: `apply_device_preset()`

**Signature** (keyword-only style mirroring `apply_plan()`):

```python
def apply_device_preset(
    device_id: str,
    preset_id: str,
    *,
    state_writer: StateWriter,
    confirmation_io: ConfirmationIO | None = None,
    rig: Rig,
    config_path: str | None = None,
    dry_run: bool = False,
    midi: MidiManager | None = None,
) -> DeviceApplyResult:
```

**Step-by-step logic:**

1. Resolve `device = rig.devices[device_id]` (caller already validated existence).
2. Read current state: `state = state_writer.read(config_path)` if `config_path` else `RigState()`.
3. Build `connected_devices: set[str] = set()`.
4. Resolve `_io = confirmation_io or RichConfirmationIO()`.
5. Construct `SetupContext` identically to `apply_plan()` and call `device.setup(setup_ctx)`. If `result.cancelled`, print cancellation message and return a `DeviceApplyResult(device=device_id, status="skipped", preset=preset_id)`.
6. Resolve `preset_number`: iterate `device.presets`, find `p.id == preset_id`, return `p.preset_number` if it exists (mirrors `_get_preset_number` in `compute.py`).
7. Resolve `midi_channel`: `getattr(device.config, "midi_channel", None)`.
8. Build `DeviceAction`:
   ```python
   from rig.engine.plan.models import ActionStatus, DeviceAction
   action = DeviceAction(
       device=device_id,
       device_type=device.type,
       status=ActionStatus.CONFIGURE,
       preset_name=preset_id,
       preset_number=preset_number,
       midi_channel=midi_channel,
   )
   ```
9. Build `DeviceApplyContext` and call `result = device.apply(device_ctx)`.
10. If `result.status == "confirmed"` and not `dry_run` and `config_path`:
    - Call `state_writer.write(config_path, state)`.
    - Print confirmation.
11. Return `result`.

**Return type:** `DeviceApplyResult` (not `ApplyResult` — no scenes involved).

---

## CLI Changes

**File:** `packages/rig/src/rig/cli/commands/apply.py`

Two new Typer options added to the `apply` function signature:

```python
device: str | None = typer.Option(None, "--device", "-d", help="Device ID to apply"),
preset: str | None = typer.Option(None, "--preset", "-p", help="Preset ID to apply to the device"),
```

**Validation block** (after `load_rig`, before `MidiManager()`):

```python
# Mutual exclusion: --scene and --device/--preset cannot be combined
if scene and (device or preset):
    console.print("[red]✗[/red] --scene cannot be combined with --device/--preset")
    raise typer.Exit(1)

# --device and --preset must be used together
if bool(device) != bool(preset):
    console.print("[red]✗[/red] --device and --preset must be used together")
    raise typer.Exit(1)

# Validate device and preset IDs against the loaded Rig
if device and preset:
    if device not in rig.devices:
        console.print(f"[red]✗[/red] Device '{device}' not found in rig config")
        raise typer.Exit(1)
    target_device = rig.devices[device]
    if not any(p.id == preset for p in target_device.presets):
        console.print(f"[red]✗[/red] Preset '{preset}' not found on device '{device}'")
        raise typer.Exit(1)
```

**Routing block** (replaces current unconditional `compute_plan` + `apply_plan` calls):

```python
midi = MidiManager()
config_path = str(Path(config).resolve())
state_writer = FileStateWriter()
try:
    if device and preset:
        from rig.engine.apply import apply_device_preset
        apply_device_preset(
            device,
            preset,
            state_writer=state_writer,
            rig=rig,
            config_path=config_path,
            dry_run=dry_run,
            midi=midi,
        )
    else:
        result = compute_plan(rig, root_path=config_path)
        apply_plan(
            result,
            state_writer=state_writer,
            rig=rig,
            config_path=config_path,
            dry_run=dry_run,
            scene=scene,
            midi=midi,
        )
finally:
    midi.disconnect_all()
```

---

## DeviceAction Construction

The `DeviceAction` for the isolated path uses:

| Field | Value | Source |
|-------|-------|--------|
| `device` | `device_id` | CLI arg |
| `device_type` | `device.type` | `rig.devices[device_id].type` (a `DeviceType` enum) |
| `status` | `ActionStatus.CONFIGURE` | Always — we always want to apply regardless of current state |
| `preset_name` | `preset_id` | CLI arg |
| `preset_number` | `int | None` | Iterate `device.presets`, find matching `p.id`, return `p.preset_number` if exists |
| `midi_channel` | `int | None` | `getattr(device.config, "midi_channel", None)` |

**Why `ActionStatus.CONFIGURE` always:** The isolated path is explicitly intent-driven — the user asked to apply this preset. Unlike the scene path, there is no "already correct" short-circuit here. The device plugin's `apply()` can still skip internally if it chooses.

---

## State Update

`apply_device_preset()` reads and writes state through the `StateWriter` Protocol:

```python
state = state_writer.read(config_path)
# ... run setup + apply ...
if result.status == "confirmed" and not dry_run and config_path:
    state_writer.write(config_path, state)
```

The device's `apply()` plugin is responsible for updating `state.devices[device_id]` fields via `update_device_state()` (already called inside each plugin's `apply()` implementation — no change needed).

**What is NOT touched:** `state.scenes` — intentionally left stale per D-07. The next full `rig apply` recomputes from scenes as normal.

---

## Error Paths

| Condition | Where caught | Output | Exit |
|-----------|-------------|--------|------|
| `--device` provided without `--preset` | CLI, after `load_rig` | `[red]✗[/red] --device and --preset must be used together` | 1 |
| `--preset` provided without `--device` | CLI, after `load_rig` | `[red]✗[/red] --device and --preset must be used together` | 1 |
| `--scene` + `--device` (or `--preset`) | CLI, after `load_rig` | `[red]✗[/red] --scene cannot be combined with --device/--preset` | 1 |
| Device ID not in `rig.devices` | CLI, after `load_rig` | `[red]✗[/red] Device '{id}' not found in rig config` | 1 |
| Preset ID not in `device.presets` | CLI, after `load_rig` | `[red]✗[/red] Preset '{id}' not found on device '{device}'` | 1 |
| Config load failure | CLI, existing `except ConfigError` block | existing behavior unchanged | 1 |
| User cancels during setup/apply | `apply_device_preset()` | print cancel message, return skipped result | 0 (no Exit) |

All validation happens **before** `MidiManager()` is constructed — no MIDI ports are opened on validation failures.

---

## Test Strategy

**File:** `packages/rig/tests/test_apply_device_preset.py` (new file)

### Happy path

- `test_apply_device_preset_calls_setup_and_apply`: Build a `FakeDevice` with a `FakePreset`, put it in a `Rig`, call `apply_device_preset()`, assert `device.apply` was called once and `state.devices[device_id].last_preset == preset_id`. Use `InMemoryStateAdapter` and `InMemoryPromptAdapter`.
- `test_apply_device_preset_writes_state_on_confirm`: `FakeDevice.apply` returns `DeviceApplyResult(status="confirmed")`, assert `state_writer.write` was called with updated state.
- `test_apply_device_preset_dry_run_does_not_write_state`: `dry_run=True`, assert `state_writer.write` was NOT called.

### Error / skip paths

- `test_apply_device_preset_skip_does_not_write_state`: `FakeDevice.apply` returns `status="skipped"`, assert no state write.
- `test_apply_device_preset_setup_cancelled_returns_skipped`: Override `FakeDevice.setup` to return `SetupResult(cancelled=True)`, assert function returns a skipped result and does not call `apply()`.

### State isolation

- `test_apply_device_preset_does_not_touch_scenes`: Pre-populate `state.scenes` with a value, run `apply_device_preset()`, assert `state.scenes` is unchanged after the call.
- `test_apply_device_preset_does_not_affect_other_devices`: Pre-populate `state.devices` for another device, run `apply_device_preset()` for a different device, assert the other device's state is unchanged.

### CLI validation (add to `tests/test_cli.py` or a new `test_cli_apply.py`)

- `test_device_without_preset_exits_1`: invoke CLI with `--device klon` only, assert exit code 1 and error message.
- `test_preset_without_device_exits_1`: invoke CLI with `--preset clean` only, assert exit code 1 and error message.
- `test_scene_and_device_conflict_exits_1`: invoke CLI with `--scene live --device klon --preset clean`, assert exit code 1.
- `test_unknown_device_exits_1`: invoke CLI with `--device nonexistent --preset clean`, assert exit code 1.
- `test_unknown_preset_exits_1`: invoke CLI with `--device klon --preset nonexistent`, assert exit code 1.

### No regression

- `test_existing_apply_plan_path_unchanged`: Call `apply_plan()` directly with the existing fixture `Rig` — assert behavior is identical to pre-phase tests. (Verify by running existing `TestApplyPlan` and `TestMidiApply` test classes unchanged.)

---

## Files Modified

| File | Change |
|------|--------|
| `packages/rig/src/rig/engine/apply.py` | Add `apply_device_preset()` function |
| `packages/rig/src/rig/cli/commands/apply.py` | Add `--device` and `--preset` options; add validation block; add routing condition |
| `packages/rig/tests/test_apply_device_preset.py` | **New file** — unit tests for `apply_device_preset()` |
| `packages/rig/tests/test_cli.py` or `test_cli_apply.py` | Add CLI-level validation tests |

No changes needed to:
- `packages/rig/src/rig/engine/plugin.py` — `DeviceApplyContext`, `SetupContext`, `DeviceApplyResult` unchanged
- `packages/rig/src/rig/engine/plan/models.py` — `DeviceAction`, `ActionStatus` unchanged
- `packages/rig/src/rig/engine/state.py` — `RigState`, `DeviceState` unchanged
- `packages/rig/src/rig/engine/ports.py` — `StateWriter` unchanged
- Any plugin package (`rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar`) — protocols satisfied, no changes needed

---

## Architecture Patterns

### Pattern: Dual-mode CLI routing with early validation

```python
# Source: existing apply.py + CONTEXT.md D-04/D-05
@app.command()
def apply(
    config: str = _CONFIG_OPTION,
    dry_run: bool = ...,
    scene: str | None = _SCENE_OPTION,
    device: str | None = typer.Option(None, "--device", "-d", ...),
    preset: str | None = typer.Option(None, "--preset", "-p", ...),
    verbose: int = _VERBOSE_OPTION,
):
    rig = load_rig(config)  # ConfigError handled by except below
    # --- Validate before MIDI ---
    if scene and (device or preset): ...   # conflict
    if bool(device) != bool(preset): ...   # partial flags
    if device and preset:                   # existence checks against rig
        ...
    # --- Open MIDI only after validation passes ---
    midi = MidiManager()
    ...
```

### Anti-Patterns to Avoid

- **Calling `compute_plan` in the isolated path:** D-01 is explicit — no `Plan`/`ScenePlan` objects. Building them needlessly runs scene diff logic that is irrelevant to single-device apply.
- **Running `setup()` on all devices:** D-03 prohibits this. Only the targeted device's `setup()` is called.
- **Touching `state.scenes` in `apply_device_preset()`:** D-07 forbids this. Scene state is intentionally left stale.
- **Validating after `MidiManager()`:** Always validate existence before opening ports — consistent with existing error handling pattern in the CLI.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `packages/rig/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/rig/tests/test_apply_device_preset.py -q` |
| Full suite command | `make test` (`uv run pytest tests/ -v`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRESET-01 | `rig apply --device <id> --preset <id>` routes to `apply_device_preset()` | integration (CLI) | `uv run pytest packages/rig/tests/test_cli_apply.py -x` | ❌ Wave 0 |
| PRESET-02 | Only targeted device's `setup()` and `apply()` are called | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::test_apply_device_preset_calls_setup_and_apply -x` | ❌ Wave 0 |
| PRESET-03 | `state.scenes` unchanged; `state.devices[other]` unchanged; `state.devices[target].last_preset` updated | unit | `uv run pytest packages/rig/tests/test_apply_device_preset.py::test_apply_device_preset_does_not_touch_scenes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/rig/tests/test_apply_device_preset.py -q`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `packages/rig/tests/test_apply_device_preset.py` — unit tests for `apply_device_preset()` (PRESET-01, PRESET-02, PRESET-03)
- [ ] `packages/rig/tests/test_cli_apply.py` — CLI-level tests for flag validation and routing (PRESET-01)

---

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Validate device/preset IDs against loaded Rig model before use |
| V6 Cryptography | no | — |

**V5 note:** Device ID and preset ID are user-supplied strings validated against the loaded `Rig` model (in-memory Python dict lookup and list scan). No SQL, no shell exec, no path traversal — risk is low. Validation gates MIDI port opening, preventing hardware operations on unknown identifiers.

---

## Package Legitimacy Audit

No new external packages are installed in this phase. All dependencies (`typer`, `pydantic`, `mido`, `rich`) are already in `pyproject.toml`.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious (SUS):** none

---

## Common Pitfalls

### Pitfall 1: Forgetting to handle `setup()` cancellation

**What goes wrong:** `setup()` returns `SetupResult(cancelled=True)` (e.g., user quits MIDI connection prompt). If `apply_device_preset()` ignores this, it proceeds to call `apply()` on an unconfigured device.

**How to avoid:** Check `result.cancelled` after `device.setup(setup_ctx)` and return early, same as `apply_plan()` does.

### Pitfall 2: Building `DeviceAction` with wrong `ActionStatus`

**What goes wrong:** Using `ActionStatus.VERIFY` instead of `ActionStatus.CONFIGURE` causes some plugins to skip sending the PC message (they treat VERIFY as "check only").

**How to avoid:** Always use `ActionStatus.CONFIGURE` in the isolated path — the user explicitly requested this preset.

### Pitfall 3: Opening MIDI before validation

**What goes wrong:** `MidiManager()` is constructed before validating device/preset IDs, leaving orphaned port connections on validation failure.

**How to avoid:** All validation checks happen immediately after `load_rig()` returns — before `MidiManager()` is instantiated. See routing block in CLI Changes section.

### Pitfall 4: Touching state.scenes

**What goes wrong:** If `apply_device_preset()` writes to `state.scenes`, the next `rig apply` scene diff may behave unexpectedly (seeing a "scene applied" marker without the full scene actually having been applied).

**How to avoid:** Only write `state.devices[device_id]` — leave `state.scenes` entirely untouched per D-07.

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies introduced by this phase. All tooling (`uv`, `pytest`, `typer`) already verified present in the project.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is not a rename/refactor/migration phase.

---

## Assumptions Log

All claims in this research were verified against the codebase directly. No assumed claims.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**Table is empty:** All claims verified by reading source files in this session. [VERIFIED: codebase]

---

## Sources

### Primary (HIGH confidence)
- `packages/rig/src/rig/engine/apply.py` [VERIFIED: codebase] — `apply_plan()` signature, pattern, `SetupContext`/`DeviceApplyContext` construction
- `packages/rig/src/rig/engine/plugin.py` [VERIFIED: codebase] — `DeviceApplyContext`, `SetupContext`, `DeviceApplyResult`, `update_device_state`
- `packages/rig/src/rig/engine/plan/models.py` [VERIFIED: codebase] — `DeviceAction`, `ActionStatus`, `DeviceType`
- `packages/rig/src/rig/cli/commands/apply.py` [VERIFIED: codebase] — CLI structure, option pattern, error handling
- `packages/rig/src/rig/engine/state.py` [VERIFIED: codebase] — `RigState`, `DeviceState` fields
- `packages/rig/src/rig/engine/ports.py` [VERIFIED: codebase] — `StateWriter`, `ConfirmationIO` Protocols
- `packages/rig/src/rig/engine/plan/compute.py` [VERIFIED: codebase] — `_get_preset_number` pattern, `DeviceAction` construction with `preset_number` and `midi_channel`
- `packages/rig/tests/fakes.py` [VERIFIED: codebase] — `InMemoryPromptAdapter`, `InMemoryStateAdapter`
- `packages/rig/tests/conftest.py` [VERIFIED: codebase] — `FakeDevice` structure
- `packages/rig/tests/test_apply.py` [VERIFIED: codebase] — test patterns, fixture structure, class layout

---

## Metadata

**Confidence breakdown:**
- Implementation approach: HIGH — all patterns read directly from source
- CLI changes: HIGH — existing Typer option pattern replicated exactly
- Test strategy: HIGH — `FakeDevice`/`InMemoryStateAdapter` patterns confirmed in existing tests
- State update behavior: HIGH — `update_device_state` and `DeviceState` fields read from source

**Research date:** 2026-06-17
**Valid until:** 2026-07-17 (stable codebase — no external dependencies)
