# Phase 33.1 Context: Apply-01/02 Completions

## Phase Goal

Apply skips analog prompts for devices already in the desired state; `--device <id>` applies a single device across all scenes without a `--preset` flag.

## Requirements

- **APPLY-01**: `rig apply` with an analog device whose state matches the scene preset skips the manual prompt
- **APPLY-02**: `rig apply --device <id>` applies that device's preset for every scene in the plan without touching other devices

## Success Criteria

1. `rig apply` with an analog device whose state matches the scene preset skips the manual prompt
2. `rig apply --device <id>` applies that device's preset for every scene in the plan without touching other devices
3. Both behaviors have tests using `InMemoryPromptAdapter`

## Dependencies

- Phase 30 (State Tracking Completeness) — `ActionStatus.VERIFY` is assigned by compute.py when analog state already matches; apply.py has a guard for it

## Codebase Status: What Already Exists

### APPLY-01 — Mechanism already works, but no E2E test + silent display

`compute.py:122` sets `analog_status = ActionStatus.ANALOG if analog_needs_change else ActionStatus.VERIFY`

`apply.py:115-119` already handles VERIFY silently:
```python
if action.status == ActionStatus.VERIFY:
    logger.debug("Device '%s': preset already correct — skipping apply", action.device)
    action_result = DeviceApplyResult(device=action.device, status="skipped", preset=action.preset_name)
```

**Gap 1**: No E2E test confirms the full path: state matches → VERIFY status → no prompt fired.
**Gap 2**: VERIFY case is completely silent (no console.print). Should show something like `[green]  ✓[/green] <device>: already set to '<preset>'`.

### APPLY-02 — Not implemented at all

`cli/commands/apply.py:44-46` has D-05 guard:
```python
if bool(device) != bool(preset):
    console.print("[red]✗[/red] --device and --preset must be used together")
    raise typer.Exit(1)
```

`apply_device_preset()` in `engine/apply.py` requires both `device_id` and `preset_id` — no cross-scene variant exists.

## Key Files

| File | Role |
|------|------|
| `packages/rig/src/rig/engine/apply.py` | `apply_plan()` + `apply_device_preset()` — main engine functions |
| `packages/rig/src/rig/cli/commands/apply.py` | CLI entry point; D-05 guard to change |
| `packages/rig/src/rig/engine/plan/compute.py` | `ActionStatus.VERIFY` assigned at line 122 |
| `packages/rig/src/rig/engine/plan/models.py` | `ActionStatus` enum (CONFIGURE, VERIFY, ANALOG) |
| `packages/rig-analog/src/rig_analog/device.py` | `AnalogDevice.apply()` — fires the prompt |
| `packages/rig/tests/test_apply.py` | Existing apply tests (InMemoryPromptAdapter, InMemoryStateAdapter) |
| `packages/rig/tests/test_apply_device_preset.py` | Existing isolated apply tests |
| `packages/rig/tests/fakes.py` | InMemoryPromptAdapter, InMemoryStateAdapter |

## Proposed Implementation Approach

### APPLY-01

1. Add a `console.print` in `apply.py` VERIFY branch: `f"  [green]✓[/green] {action.device}: already set to '{action.preset_name}'"`
2. Add E2E test in `test_apply.py`: rig with analog device + state showing preset already matches → apply_plan → assert InMemoryPromptAdapter was never called, assert "already set" in output

### APPLY-02

1. Add `apply_device_scenes()` to `engine/apply.py` — takes `device_id` + plan, filters each scene's `device_actions` to only the named device, then applies using existing `apply_plan`-style logic
   - OR add `device_filter: str | None` param to `apply_plan()` which filters actions inside the loop
2. In `cli/commands/apply.py`:
   - Remove the D-05 "must be used together" guard
   - Add branch: `if device and not preset:` → call new cross-scene function
   - Keep `if device and preset:` → call existing `apply_device_preset()`
3. Add tests: rig with 2+ devices across multiple scenes → `apply` with device filter → only named device actions run, other devices untouched, state updated only for named device

## Constraints

- Tests must use `InMemoryPromptAdapter` and `InMemoryStateAdapter` (no real MIDI, no disk I/O)
- No new CLI flags or options beyond what's required
- APPLY-02 must NOT touch other devices' state
- Python 3.12+, Pydantic BaseModel, conventional commits format

## Integration Notes (from v1.6 Milestone Audit)

- The MC6 state write-back bug (`controller.apply()` result discarded in `apply_plan:184`) is a separate issue; do not fix it here
- The catalog-constants-in-tests-only warning is out of scope for this phase
