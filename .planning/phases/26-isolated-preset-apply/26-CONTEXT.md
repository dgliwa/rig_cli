# Phase 26: Isolated Preset Apply - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--device <id>` and `--preset <id>` flags to `rig apply`. When both flags are given, apply only that device's preset to the physical device — no scene-based plan, no other devices touched. After this phase, `rig apply --device klon --preset clean` sends the preset to the device, updates only that device's entry in `state.json`, and exits cleanly.

</domain>

<decisions>
## Implementation Decisions

### Plan integration approach
- **D-01:** Bypass the scene-based plan engine entirely. `--device`/`--preset` is a distinct execution mode — no call to `compute_plan`, no `Plan`/`ScenePlan` objects. Instead, CLI validates the device+preset exist in the `Rig` model, builds a `DeviceAction` directly, and calls a new `apply_device_preset()` function in `apply.py`.
- **D-02:** The new `apply_device_preset()` function reuses `DeviceApplyContext` and `device.apply()` — it does NOT duplicate the apply logic. The key difference is it starts from a direct `DeviceAction`, not from a scene loop.

### Device setup scope
- **D-03:** Call `setup()` only on the targeted device before `device.apply()`. Do not run setup for other devices — this is an isolated operation. The `SetupContext` is constructed the same way as in `apply_plan`, but passed only to the one device.

### Flag conflict handling
- **D-04:** `--device` and `--preset` must be used together — providing one without the other is an error. If `--scene` is also passed alongside `--device`/`--preset`, print a clear error and exit. The two modes are exclusive.
- **D-05:** `--device` and `--preset` default to `None`. The CLI routes to `apply_device_preset()` when both are present, or to the existing `apply_plan()` when neither is present.

### Error handling
- **D-06:** Validate device ID and preset ID against the loaded `Rig` model immediately after loading config, before opening any MIDI ports. Use the existing `ConfigError` pattern: `console.print(f"[red]✗[/red] {e}")` and `raise typer.Exit(1)`. Two specific checks: device not in `rig.devices`, and preset not in `device.presets`.

### State update
- **D-07:** `apply_device_preset()` updates `state.devices[device_id]` only (last_preset, etc.). It does not touch `state.scenes`. The scene state is intentionally left stale — the next full `rig apply` will recompute from scenes as normal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Apply engine
- `packages/rig/src/rig/engine/apply.py` — `apply_plan()` — the existing apply entry point; new `apply_device_preset()` lives here alongside it
- `packages/rig/src/rig/engine/plugin.py` — `DeviceApplyContext`, `SetupContext`, `DeviceApplyResult` — context types used by both old and new code paths

### Plan models
- `packages/rig/src/rig/engine/plan/models.py` — `DeviceAction`, `ActionStatus`, `DeviceType` — the action type constructed directly in the isolated path

### CLI
- `packages/rig/src/rig/cli/commands/apply.py` — the `apply` Typer command to extend with `--device` and `--preset` options

### State management
- `packages/rig/src/rig/engine/state.py` — `RigState`, `DeviceState` — how device state is read and written
- `packages/rig/src/rig/engine/ports.py` — `StateWriter`, `FileStateWriter` — state write abstraction used by apply engine

### Rig model
- `packages/rig/src/rig/models/rig.py` — `Rig.devices` — source of truth for device and preset lookup

### Requirements
- `.planning/REQUIREMENTS.md` — PRESET-01, PRESET-02, PRESET-03 (the three requirements mapped to this phase)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeviceApplyContext` (`packages/rig/src/rig/engine/plugin.py`): Already carries `action`, `state`, `rig`, `dry_run`, `confirmation_io`, `midi`, `connected_devices`, `config_path`. New `apply_device_preset()` constructs one of these directly.
- `SetupContext` (`packages/rig/src/rig/engine/plugin.py`): Same constructor pattern — used to call `device.setup()` for the targeted device only.
- `FileStateWriter` and `RigState` (`ports.py`, `state.py`): Read/write state — reuse unchanged.
- `_make_apply_ctx()` helper in tests — already parameterized, usable for new tests.

### Established Patterns
- `device.setup()` → `device.apply()` is the canonical two-phase pattern for each device plugin. `apply_device_preset()` follows the same order: call setup on target, then apply.
- CLI error handling: load config → catch `ConfigError` → print red error → `raise typer.Exit(1)`. Validation before MIDI follows this exact pattern.
- All I/O goes through `ConfirmationIO` (Phase 25 decision, now enforced across all plugins).

### Integration Points
- New function `apply_device_preset(device_id, preset_id, ...)` added to `packages/rig/src/rig/engine/apply.py` alongside `apply_plan`.
- `packages/rig/src/rig/cli/commands/apply.py` gains `--device` and `--preset` options; routes to the new function when both are present.
- No changes needed to plugin implementations (`rig-analog`, `rig-chasebliss`, `rig-hx`, `rig-morningstar`) — they already implement `setup()` and `apply()`.

</code_context>

<specifics>
## Specific Ideas

- `apply_device_preset()` signature should mirror `apply_plan()` in style: keyword-only args, `state_writer`, `confirmation_io`, `rig`, `config_path`, `dry_run`, `midi`.
- The `DeviceAction` built inline should use `ActionStatus.CONFIGURE` as the status (same as what `compute_plan` produces for a changed preset).
- For the device_type field on `DeviceAction`, look it up from the loaded device plugin (each plugin exposes its `DeviceType`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 26-Isolated Preset Apply*
*Context gathered: 2026-06-17*
