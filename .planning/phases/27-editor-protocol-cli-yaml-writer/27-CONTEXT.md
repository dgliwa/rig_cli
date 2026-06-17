# Phase 27: Editor Protocol, CLI Surface & YAML Writer - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `rig edit <device-id> <preset-id>` — the CLI routes to editor mode, a companion `EditorProtocol` declares the `edit(preset_id, ctx)` contract, and the YAML writer saves updated preset values back to `rig.yaml` on confirm. Discarding leaves the file bit-for-bit unchanged.

Phase 27 scope is the scaffold: protocol, CLI, YAML writer, and skeleton plugin stubs for CBA and MIDI devices. Phase 28 owns the live interactive behavior (CC streaming, analog prompt-per-control).

Out of scope: live CC MIDI during editing (EDIT-03), analog prompt-per-control flow (EDIT-06), HX Stomp editor mode.

</domain>

<decisions>
## Implementation Decisions

### EditorProtocol shape
- **D-01:** Define a separate companion `EditorProtocol` — NOT added to the existing `Device` Protocol. `Device` Protocol stays unchanged. Plugins that support editing implement both.
- **D-02:** Engine dispatches via `isinstance(device, EditorProtocol)` check — no registry or try/except.
- **D-03:** When a device does not implement `EditorProtocol`, print a warning and exit cleanly (non-error exit code). Example message: `"Device '{id}' does not support editing."` — informational, not fatal.

### YAML round-trip strategy
- **D-04:** Use `ruamel.yaml` for write-back — preserves comments, field ordering, and blank lines in hand-authored `rig.yaml`. Add `ruamel.yaml` as a dependency.
- **D-05:** Write atomicity: hold the updated YAML in memory; write to `rig.yaml` only when the user confirms save. No temp file in Phase 27. On discard, the file is never written.

### EditContext design
- **D-06:** Define a new `EditContext` dataclass (not reusing `DeviceApplyContext`). Fields:
  - `config_path: Path` — path to `rig.yaml` for write-back
  - `dry_run: bool` — if true, skip the actual file write, print what would change
  - `confirmation_io: ConfirmationIO` — Phase 25 IO abstraction for save/discard prompt
  - `rig: Rig` — loaded rig model for preset lookup and validation

### Phase 27 editor interaction (skeleton)
- **D-07:** Phase 27 editor interaction is a skeleton — prints "edit mode entered for `<device-id>:<preset-id>`", then immediately offers save/discard via `ConfirmationIO`. No value-change prompts in Phase 27 (those come from Phase 28 plugin implementations).
- **D-08:** Phase 27 adds skeleton `edit()` stubs to CBA and MIDI plugins. Each stub returns the current preset values unchanged. Phase 28 replaces these stubs with real interactive behavior (live CC for CBA/MIDI, prompt-per-control for analog).
- **D-09:** Analog plugin does NOT receive a stub in Phase 27 — it does not implement `EditorProtocol` until Phase 28.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Device Protocol and plugin system
- `packages/rig/src/rig/engine/plugin.py` — `DevicePlugin` Protocol, `DeviceApplyContext`, `SetupContext`, `DeviceApplyResult` — existing Protocol to understand before defining `EditorProtocol` alongside it

### CLI surface
- `packages/rig/src/rig/cli/commands/apply.py` — pattern for adding a new CLI command (Typer app, config loading, error handling)
- `packages/rig/src/rig/cli/_shared.py` — shared Typer app instance and common options

### Config loader
- `packages/rig/src/rig/config/loader.py` — `load_rig()` — how `rig.yaml` is parsed; ruamel.yaml integration point

### YAML model
- `packages/rig/src/rig/models/preset.py` — `Preset`, `MidiPreset` — field names to serialize back on save
- `packages/rig/src/rig/models/rig.py` — `Rig.devices` — device and preset lookup

### IO abstraction (Phase 25)
- `packages/rig/src/rig/engine/ports.py` — `ConfirmationIO` Protocol — the IO abstraction `EditContext.confirmation_io` must use

### Plugin implementations to extend
- `packages/rig/src/rig/plugins/chase_bliss/` — CBA plugin — receives skeleton `edit()` stub in Phase 27
- `packages/rig/src/rig/plugins/midi_device/` — MIDI plugin — receives skeleton `edit()` stub in Phase 27

### Requirements
- `.planning/REQUIREMENTS.md` — EDIT-01, EDIT-02, EDIT-04, EDIT-05 (Phase 27 requirements)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeviceApplyContext` in `plugin.py` — reference pattern for designing `EditContext`; note the fields that are NOT needed (midi, state, connected_devices, scene_id)
- `ConfirmationIO` / `InMemoryPromptAdapter` — already thread-safe and tested via Phase 25; reuse directly in `EditContext`
- Typer app in `cli/_shared.py` — the `@app.command()` pattern used by apply/plan/validate commands is the right template for `rig edit`

### Established Patterns
- `Protocol` + `isinstance` dispatch — already used for `DeviceApplier` registry; `EditorProtocol` follows the same pattern
- `@dataclass` for context objects — `ApplyContext` and `DeviceApplyContext` both use `@dataclass`; `EditContext` should too
- `ConfigError` pattern in CLI commands — validate device ID and preset ID immediately after `load_rig()`; print `[red]✗[/red]` and `raise typer.Exit(1)` on validation failure

### Integration Points
- `rig edit` command lives in a new file `packages/rig/src/rig/cli/commands/edit.py`, registered in `cli/__init__.py` alongside other commands
- `EditorProtocol` defined in `engine/plugin.py` alongside `DevicePlugin`
- `EditContext` defined in `engine/plugin.py` (same file as other context dataclasses)
- YAML writer is a new module or function in `config/` — reads `rig.yaml` with ruamel.yaml, updates the preset block, writes back on save

</code_context>

<specifics>
## Specific Ideas

- On discard, zero file writes — memory-only until confirmed save guarantees bit-for-bit identity without needing to compare before/after
- Skeleton stub message format: `"Editor mode: <device-id>/<preset-id> (no interactive editing available — Phase 28 will add this)"` — sets clear expectations
- ruamel.yaml round-trip: use `ruamel.yaml.YAML(typ='rt')` (round-trip mode) for loading and saving — this is the standard pattern for comment-preserving YAML mutation

</specifics>

<deferred>
## Deferred Ideas

- Crash-safe write (temp file + `os.rename()`) — memory-only write is sufficient for Phase 27; atomic rename is a future hardening step
- HX Stomp editor mode — out of scope for both Phase 27 and Phase 28 (referenced in roadmap as future)
- Analog plugin editor stub — analog device does not implement `EditorProtocol` until Phase 28 (EDIT-06)

</deferred>

---

*Phase: 27-editor-protocol-cli-yaml-writer*
*Context gathered: 2026-06-17*
