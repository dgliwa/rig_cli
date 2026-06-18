---
phase: 28
slug: editor-plugin-implementations
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-17
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/rig/tests/test_plugin.py packages/rig-chasebliss/tests/test_device.py packages/rig-analog/tests/test_analog_device.py packages/rig-hx/tests/test_hx_device.py -q` |
| **Full suite command** | `uv run pytest packages/ -q` |
| **Estimated runtime** | ~0.5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command above
- **After every plan wave:** Run full suite (`uv run pytest packages/ -q`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-01-T1 | 01 | 1 | D-04 | T-28-01 | `split(None, 1)` limits to two parts; unknown keys and invalid values rejected before CC send; `validate_cc_params` gates range before MIDI | unit | `uv run pytest packages/rig/tests/test_plugin.py packages/rig-hx/tests/test_hx_device.py -q` | ✅ | ✅ green |
| 28-01-T2 | 01 | 1 | EDIT-03 | T-28-01, T-28-02, T-28-03 | `validate_cc_params` rejects values outside `control.min`–`control.max` before `send_control_change`; loop exits on "done" or empty string | unit | `uv run pytest packages/rig-chasebliss/tests/test_device.py -q` | ✅ | ✅ green |
| 28-01-T3 | 01 | 1 | EDIT-06 | — | Analog loop validates keys against `preset.values` only; no MIDI path exists; values stored as raw strings (Pydantic validates on next `rig validate`) | unit | `uv run pytest packages/rig-analog/tests/test_analog_device.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage

| Requirement | Description | Test File(s) | Status |
|-------------|-------------|--------------|--------|
| EDIT-03 | CC-based plugins send live CC values immediately as values are changed interactively | `packages/rig-chasebliss/tests/test_device.py` (`test_chase_bliss_edit_valid_entry_sends_cc`, `test_chase_bliss_edit_unknown_control_re_prompts`, `test_chase_bliss_edit_out_of_range_re_prompts`) | ✅ COVERED |
| EDIT-06 | Analog plugin editor mode presents prompt-per-control flow (no live MIDI); plugin owns this behavior | `packages/rig-analog/tests/test_analog_device.py` (`test_analog_edit_valid_key_updates_dict`, `test_analog_edit_unknown_key_is_rejected`, `test_analog_edit_returns_unchanged_on_done`, `test_analog_edit_raises_for_unknown_preset`, `test_analog_device_implements_editor_protocol`) | ✅ COVERED |
| D-04 | `EditContext` gains `midi: MidiManager \| None = None` field; `edit.py` passes `midi=None` | `packages/rig/tests/test_plugin.py` (`test_edit_context_has_required_fields`, `test_edit_context_can_be_instantiated`) | ✅ COVERED |
| D-09 | HX stub prints "future milestone" message and returns current preset values unchanged | `packages/rig-hx/tests/test_hx_device.py` (`test_hx_stomp_device_edit_returns_preset_dict`) | ✅ COVERED |
| D-07, D-08 | AnalogDevice satisfies `EditorProtocol`; negative protocol test replaced with positive | `packages/rig-analog/tests/test_analog_device.py` (`test_analog_device_implements_editor_protocol` — replaced `test_analog_device_does_not_implement_editor_protocol`) | ✅ COVERED |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* pytest 9.0.3 was already installed; no additional test framework setup was needed for Phase 28.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

CBA and Analog editor loops are verified via `ConfirmationIO` mock injection and `MidiManager` stubs. The interactive happy path (live terminal) is covered by stubs — no human-only verification required.

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: all 3 tasks have automated verify (no gap)
- [x] Wave 0: not needed — existing infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 1s (full suite: 0.54s, quick: ~0.25s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-17

---

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Tests run | 18 (phase-specific) / 367 (full suite) |
| Result | NYQUIST-COMPLIANT |

---

## Verification Cross-Check

*Cross-referenced against Phase 28 VERIFICATION.md, which scored 10/10 must-haves verified:*

| Must-Have | Verification Evidence | VALIDATION Coverage |
|-----------|----------------------|---------------------|
| CBA editor displays controls with name, CC, range, value | `device.py:354` console.print in control loop | `test_chase_bliss_device_edit_done_returns_parameters` |
| CBA accepts `<name> <value>` and sends CC immediately | `device.py:392-398` send_control_change call | `test_chase_bliss_edit_valid_entry_sends_cc` |
| CBA prints error + re-prompts on unknown/out-of-range | `device.py:370-374` unknown, `device.py:385-389` range | `test_chase_bliss_edit_unknown_control_re_prompts`, `test_chase_bliss_edit_out_of_range_re_prompts` |
| CBA returns updated dict after `done` | `device.py:357` updated init, returns at end | `test_chase_bliss_device_edit_done_returns_parameters` |
| Analog displays keys/values, validates keys, no MIDI | `device.py:100-114` print + validate + no MIDI path | `test_analog_edit_valid_key_updates_dict`, `test_analog_edit_unknown_key_is_rejected` |
| Analog satisfies EditorProtocol | `isinstance(analog, EditorProtocol)` confirmed | `test_analog_device_implements_editor_protocol` |
| HX stub prints future milestone message | `rig_hx/device.py:177` text confirmed | `test_hx_stomp_device_edit_returns_preset_dict` |
| EditContext has midi field; edit.py passes midi=None | `plugin.py:196`, `edit.py:54` | `test_edit_context_has_required_fields` |
| All 359 existing tests pass | 367 passed (8 new) | Full suite `uv run pytest packages/ -q` |
