# Plan 1: Core Protocol & Engine Cleanup

**Wave:** 1 (parallel with Plan 2)
**Depends on:** None
**Files modified:**
- `packages/rig/src/rig/engine/plugin.py` — Formalize Device Protocol
- `packages/rig/src/rig/engine/apply.py` — Remove Phase -1 MIDI connection loop
- `packages/rig/src/rig/engine/devices.py` — Delete entire file
- `packages/rig/src/rig/engine/__init__.py` — Remove devices.py re-export if present
- `packages/rig/src/rig/engine/plan/compute.py` — Remove references to devices.py if any
- `packages/rig/tests/test_devices.py` — Update imports (deleted file import removal)
**Files created:** None
**Requirements:** CORE-02, CORE-03 (continued from Phase 6)

---

## Task 1.1: Formalize the Device Protocol

Add explicit `get_scene_pc_command()` to the `Device` Protocol and add comprehensive docstrings.

<read_first>
- `packages/rig/src/rig/engine/plugin.py` — Current Protocol definition
</read_first>

<action>
1. In `packages/rig/src/rig/engine/plugin.py`, add `get_scene_pc_command` method to the `Device` Protocol:
   `def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None: ...`
2. Add a comprehensive docstring to the `Device` Protocol explaining the structural contract for plugin authors: what each method does, when it's called, expected return types, and the PluginContext/SetupContext/DeviceApplyContext semantics.
3. Ensure the Protocol also includes `presets` property that returns `list[Any]`.
</action>

<acceptance_criteria>
- `Device` Protocol in `plugin.py` has 6 methods: `id`, `name`, `config`, `presets`, `plan`, `diff`, `setup`, `apply`, `get_scene_pc_command`
- Protocol has a docstring explaining the plugin author contract
- All existing Device classes still implement the Protocol structurally (no type errors)
</acceptance_criteria>

---

## Task 1.2: Remove Phase -1 MIDI Connection Loop from apply.py

Remove the entire "Phase -1: MIDI connection per unique device" section from `apply_plan()`.

<read_first>
- `packages/rig/src/rig/engine/apply.py` — Current apply_plan function
</read_first>

<action>
1. In `packages/rig/src/rig/engine/apply.py`, remove the code block starting with `# --- Phase -1: MIDI connection per unique device ---` through the comment `# If skipped → device not in connected_devices, falls back to manual prompts`.
2. Remove imports that become unused after removal: `collect_midi_devices` from `rig.interaction.midi`, and any import that was only used by Phase -1.
3. Keep the Phase -2 block (device setup loop) — this is the correct mechanism going forward.
4. Remove the `midi_connection_io` parameter from `apply_plan()` signature and the `SetupContext` constructor call.
</action>

<acceptance_criteria>
- `apply_plan()` no longer has `midi_connection_io` parameter
- No `collect_midi_devices(plan)` call in `apply.py`
- Phase -2 (device setup) is the sole MIDI connection mechanism
- `collect_midi_devices()` in `interaction/midi.py` can be deprecated (mark with TODO, not removed — it may be used elsewhere)
- All tests that call `apply_plan()` pass without `midi_connection_io` argument
</acceptance_criteria>

---

## Task 1.3: Delete `rig.engine.devices.py`

Remove the whole-file module that no longer holds any Device classes — all 4 classes live in their plugin packages.

<read_first>
- `packages/rig/src/rig/engine/devices.py` — File to delete
- `packages/rig/src/rig/engine/__init__.py` — Check for re-exports
</read_first>

<action>
1. Delete `packages/rig/src/rig/engine/devices.py`.
2. If `packages/rig/src/rig/engine/__init__.py` has any import of `devices` or re-export from it, remove it.
</action>

<acceptance_criteria>
- `packages/rig/src/rig/engine/devices.py` no longer exists
- Core package imports cleanly (`import rig.engine` does not raise ImportError)
- No core tests reference `rig.engine.devices` (test_devices.py imports updated in Plan 3)
</acceptance_criteria>

---

## Task 1.4: Remove `midi_connection_io` Wiring from CLI

Remove the `midi_connection_io` argument construction and passing in the CLI apply command.

<read_first>
- `packages/rig/src/rig/cli/commands/apply.py` — CLI apply command wiring
</read_first>

<action>
1. Find where `InteractiveMidiConnectionIO` or `midi_connection_io` is constructed/imported in the CLI apply command chain.
2. Remove construction of `midi_connection_io` and its passing to `apply_plan()`.
3. Stop importing `InteractiveMidiConnectionIO` (or `InMemoryMidiConnectionIO` if used elsewhere).
</action>

<acceptance_criteria>
- CLI `rig apply` command no longer creates or passes `midi_connection_io`
- `rig apply` still works in dry-run mode
- `InteractiveMidiConnectionIO` can remain in `ports.py` for backward compat (don't delete — may have other consumers)
</acceptance_criteria>

---

## Verification

```bash
cd packages/rig && uv run pytest tests/ -q --timeout=30 2>&1 | tail -20
```

## Artifacts this phase produces

- Updated `Device` Protocol in `rig.engine.plugin` with `get_scene_pc_command()` method and docstring
- Deleted file: `rig.engine.devices`
- Updated function signature: `apply_plan()` in `rig.engine.apply` — no `midi_connection_io` parameter
- Updated function signature: CLI `apply` command — no `midi_connection_io` construction
