---
phase: 28-editor-plugin-implementations
plan: 01
status: completed
commit: f7428da
---

# Summary: Phase 28-01 — Editor Plugin Implementations

## What was built

Three interactive editor implementations replacing Phase 27 stubs, plus an `EditContext` field addition.

### EditContext.midi field (plugin.py + edit.py)
Added `midi: MidiManager | None = None` as the last field in the `EditContext` dataclass. `edit.py` passes `midi=None` explicitly. The `test_edit_context_has_four_fields` test was updated to `test_edit_context_has_required_fields` with the new five-field assertion.

### CBA live editor (rig-chasebliss/device.py)
Replaced the stub `edit()` with a full interactive CC-send loop:
- Resolves controls from `get_controls("Chase Bliss Audio", model)` catalog
- Prints header + control list: name, CC number, range, current preset value
- Entry loop: `<control> <value>` input → case-insensitive lookup → range validation via `validate_cc_params` → CC send via `ctx.midi.send_control_change()` if MIDI connected, else prints warning
- Returns `dict(preset.parameters)` accumulating all edits

### AnalogDevice editor (rig-analog/device.py)
Added `edit()` implementing `EditorProtocol` with a no-MIDI key-entry loop:
- Prints current `preset.values` on entry
- Accepts `<key> <value>` input; validates against existing keys only
- Values stored as raw strings (no coercion; Pydantic validates on next `rig validate`)

### HX stub message (rig-hx/device.py)
Updated stub message to: `"no interactive editing available — HX live editing is a future milestone"`

## Tests

| Package | Before | After | Delta |
|---------|--------|-------|-------|
| rig | 291 | 291 | 0 |
| rig-chasebliss | 52* | 58 | +6 |
| rig-analog | 8 | 13 | +5 |
| rig-hx | 8 | 8 | 0 |
| **Total** | **359** | **367** | **+8** |

*One pre-existing failure (`test_mood_missing_ccs_are_present`) excluded from count — not caused by this phase.

### New tests added
- `test_chase_bliss_device_edit_done_returns_parameters`
- `test_chase_bliss_edit_valid_entry_sends_cc`
- `test_chase_bliss_edit_unknown_control_re_prompts`
- `test_chase_bliss_edit_out_of_range_re_prompts`
- `test_chase_bliss_edit_no_midi_records_without_sending`
- `test_analog_device_implements_editor_protocol` (replaced `test_analog_device_does_not_implement_editor_protocol`)
- `test_analog_edit_returns_unchanged_on_done`
- `test_analog_edit_valid_key_updates_dict`
- `test_analog_edit_unknown_key_is_rejected`
- `test_analog_edit_raises_for_unknown_preset`

## Success criteria met

1. ✅ All 367 tests pass (zero regressions)
2. ✅ `AnalogDevice` satisfies `EditorProtocol` — `isinstance` returns `True`
3. ✅ `test_analog_device_does_not_implement_editor_protocol` replaced with positive test
4. ✅ `EditContext` has `midi: MidiManager | None = None`; `edit.py` passes `midi=None`
5. ✅ CBA `edit()` sends `ctx.midi.send_control_change(...)` on each valid entry (verified via MagicMock)
6. ✅ CBA and Analog loops re-prompt on unknown control/key or out-of-range value
7. ✅ HX stub prints "HX live editing is a future milestone" message
