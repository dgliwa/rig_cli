# Phase 28: Editor Plugin Implementations - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Each device plugin fills in real interactive editing behavior behind the `EditorProtocol.edit()` method scaffolded in Phase 27:

- **CBA plugin**: Named control entry loop with live CC send on each valid entry
- **MIDI plugin**: Same named control entry loop with live CC send on each valid entry
- **Analog plugin**: Same named control entry loop — no MIDI sent, validates against existing keys only; `AnalogDevice` gains `EditorProtocol` implementation in this phase
- **HX Stomp plugin**: Skeleton `edit()` stub only (no live behavior) — consistent with what CBA/MIDI received in Phase 27

Phase 27's save/discard lifecycle, YAML writer, and `EditContext` are unchanged. Plugins return the updated `dict[str, Any]` and the CLI layer handles persistence.

Out of scope: HX live CC/SysEx editing, any new CLI surface, changes to `EditorProtocol` or `EditContext`.

</domain>

<decisions>
## Implementation Decisions

### CC control navigation UX (CBA + MIDI)
- **D-01:** Named control entry loop — on editor start, print all controls with name, CC number, range, and current preset value. User types `<control-name> <value>` to change a control (e.g. `wet 64`). Loop repeats until user types `done`.
- **D-02:** On unknown control name or out-of-range value: print a clear error message, then re-prompt the same input (do not advance, do not skip). Example: `'wet': 200 is out of range (0–127)`.
- **D-03:** Case-insensitive or exact match for control name is Claude's discretion — whatever matches the catalog key format.

### Live CC send timing (CBA + MIDI)
- **D-04:** Send the CC message **immediately** on each valid value entry — before the user types `done`. The user hears the change live on the device.
- **D-05:** On discard, **do not re-send original values**. `rig.yaml` stays clean (Phase 27 guarantee); device CC state reflects whatever the user dialed in last. No MIDI rollback.

### Analog editor flow
- **D-06:** Same named-entry loop UX as CC plugins — consistent across all device types. Show all control keys with current values upfront. User types `<key> <value>`. Loop until `done`.
- **D-07:** Validation: accept only keys that already exist in the preset's `values` dict. Unknown keys → error + re-prompt. No range validation (no catalog for analog). Value types accepted freely — Pydantic will validate on next `rig validate`.
- **D-08:** `AnalogDevice` gains `EditorProtocol` implementation in Phase 28 (Phase 27 decision D-09 deferred this). The test `test_analog_device_does_not_implement_editor_protocol` must be deleted/replaced with a positive test.

### HX Stomp scope
- **D-09:** `HXStompDevice` gets a skeleton `edit()` stub — same pattern as CBA/MIDI received in Phase 27. Prints a placeholder, returns current values unchanged. Does NOT implement live CC/SysEx behavior. A future phase owns HX live editing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 27 scaffold (direct foundation)
- `packages/rig/src/rig/engine/plugin.py` — `EditorProtocol`, `EditContext` — the protocol and context this phase fills in; also `DevicePlugin`, `DeviceApplyContext` for pattern reference
- `packages/rig/src/rig/cli/commands/edit.py` — CLI command that calls `device.edit()` and routes save/discard; unchanged in Phase 28
- `packages/rig/src/rig/config/yaml_writer.py` — `write_preset()` — how updated values flow back to `rig.yaml`; Phase 28 plugins just return the dict

### Plugin implementations to extend
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — `ChaseBlissDevice.edit()` skeleton stub to replace with live implementation
- `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` (or `get_controls()`) — control names, CC numbers, ranges, defaults — source of truth for display and validation
- `packages/rig-hx/src/rig_hx/device.py` — `HXStompDevice` — receives skeleton `edit()` stub in Phase 28
- `packages/rig-analog/src/rig_analog/device.py` — `AnalogDevice` — gains full `EditorProtocol` implementation; currently does NOT implement it
- `packages/rig-analog/src/rig_analog/preset.py` — `AnalogPreset.values: dict[str, float | str | bool]` — source of control keys for analog editing

### IO abstraction
- `packages/rig/src/rig/engine/ports.py` — `ConfirmationIO.prompt()` — used for reading user input in the control entry loop (if routed through it); also `RichConfirmationIO` for the production adapter

### MIDI sending
- `packages/rig/src/rig/midi/adapter.py` — `MidiManager` — how CC messages are sent; `EditContext` provides `midi` if needed (check `plugin.py` for current `EditContext` fields)

### Requirements
- `.planning/REQUIREMENTS.md` — EDIT-03 (CC live send), EDIT-06 (analog prompt-per-control)
- `.planning/phases/27-editor-protocol-cli-yaml-writer/27-CONTEXT.md` — Phase 27 decisions D-01 through D-09

### Test files (must update)
- `packages/rig-analog/tests/test_analog_device.py` — `test_analog_device_does_not_implement_editor_protocol` must be replaced with a positive EditorProtocol test
- `packages/rig-chasebliss/tests/test_device.py` — CBA editor tests; stubs replaced
- `packages/rig-hx/tests/test_hx_device.py` — HX device tests; stub added

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChaseBlissDevice.edit()` stub in `rig_chasebliss/device.py` — the method signature and return type are already correct; Phase 28 replaces the body
- `rig_chasebliss.catalog.get_controls()` — returns `list[Control]` with `name`, `cc`, `min`, `max`, `positions`, `default` — feeds the display list and validation in D-01/D-02
- `ConfirmationIO.prompt(text: str) -> str` — already defined in `ports.py`; can drive the control entry loop's `input()` abstraction
- `AnalogPreset.values: dict[str, float | str | bool]` — keys are the valid control names for analog; current values shown upfront and returned as updated dict

### Established Patterns
- Named-entry loop UX: consistent across CBA, MIDI, and analog (D-01, D-06) — same display/input pattern, different backend behavior (CC send vs no-op)
- `edit()` returns `dict[str, Any]` — the CLI layer handles persistence; plugins must not write `rig.yaml` directly
- `@dataclass` for context objects — `EditContext` is already a dataclass; no changes needed
- Phase 27 skeleton stub pattern — `HXStompDevice.edit()` follows exactly what CBA/MIDI got in Phase 27

### Integration Points
- `MidiManager` in `EditContext` — check if `EditContext` exposes a `midi` field; if not, the CBA/MIDI plugin may need to obtain a MIDI connection via `setup()` state or a new `EditContext` field (decide in planning)
- `AnalogDevice` must import and implement `EditorProtocol` — currently guarded behind `TYPE_CHECKING`

</code_context>

<specifics>
## Specific Ideas

- Display format for control list: `  <name> (CC<num>, <min>–<max>, currently: <value>)` — one line per control
- Entry format: `> wet 64` — control name, space, value. Invalid input re-prompts the same `> ` prompt.
- Typing `done` (or empty Enter?) exits the loop and returns the accumulated dict to the CLI for save/discard
- For analog: display `  <key>: <current-value>` (no CC number or range since no catalog)
- HX stub message: same pattern as Phase 27 CBA stub — `"Editor mode: <id>/<preset> (no interactive editing available — Phase 28 adds this for CC-based devices only)"`

</specifics>

<deferred>
## Deferred Ideas

- HX live CC/SysEx editing — out of scope for Phase 28; HX gets a skeleton stub only
- Re-sending original CC values on discard (MIDI rollback) — not needed for a personal rig; could be a future hardening option
- Fuzzy/case-insensitive control name matching — Claude's discretion; not a stated requirement

</deferred>

---

*Phase: 28-editor-plugin-implementations*
*Context gathered: 2026-06-17*
