---
phase: 27
slug: editor-protocol-cli-yaml-writer
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-17
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/rig/tests/test_plugin.py packages/rig/tests/test_yaml_writer.py packages/rig/tests/test_cli_edit.py packages/rig-chasebliss/tests/test_device.py packages/rig-hx/tests/test_hx_device.py packages/rig-analog/tests/test_analog_device.py -q` |
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
| 27-01-01 | 01 | 1 | D-01, D-06 | — | N/A | unit | `uv run pytest packages/rig/tests/test_plugin.py -q` | ✅ | ✅ green |
| 27-01-02 | 01 | 1 | EDIT-02, EDIT-05 | T-27-01 | write_preset only called on save confirm; dry_run skips file write | unit | `uv run pytest packages/rig/tests/test_yaml_writer.py -q` | ✅ | ✅ green |
| 27-01-03 | 01 | 1 | EDIT-01, EDIT-02, EDIT-04, D-02, D-03, D-05 | T-27-01, T-27-02 | Device/preset IDs validated before dispatch; write only on "y"/"yes" | unit | `uv run pytest packages/rig/tests/test_cli_edit.py -q` | ✅ | ✅ green |
| 27-01-04 | 01 | 1 | D-07, D-08, D-09 | — | N/A | unit | `uv run pytest packages/rig-chasebliss/tests/test_device.py packages/rig-hx/tests/test_hx_device.py packages/rig-analog/tests/test_analog_device.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage

| Requirement | Description | Test File | Status |
|-------------|-------------|-----------|--------|
| EDIT-01 | `rig edit` command with device_id + preset_id positional args | `test_cli_edit.py` | ✅ COVERED |
| EDIT-02 | Save/discard with write-back only on user confirm ("y"/"yes") | `test_cli_edit.py`, `test_yaml_writer.py` | ✅ COVERED |
| EDIT-04 | `--dry-run` prints what would change, skips file write | `test_cli_edit.py`, `test_yaml_writer.py` | ✅ COVERED |
| EDIT-05 | ruamel.yaml round-trip preserves hand-authored YAML comments | `test_yaml_writer.py` | ✅ COVERED |
| D-01 | EditorProtocol defined alongside Device in plugin.py; Device Protocol unchanged | `test_plugin.py` | ✅ COVERED |
| D-02 | Dispatch via `isinstance(device, EditorProtocol)` — no registry | `test_cli_edit.py` | ✅ COVERED |
| D-03 | Non-editor device prints warning and exits 0 | `test_cli_edit.py` | ✅ COVERED |
| D-05 | Discard response skips `write_preset()` call | `test_cli_edit.py` | ✅ COVERED |
| D-06 | EditContext is @dataclass with fields: config_path, dry_run, confirmation_io, rig | `test_plugin.py` | ✅ COVERED |
| D-07 | ChaseBlissDevice.edit() skeleton stub — returns preset.model_dump() | `test_device.py` | ✅ COVERED |
| D-08 | HXStompDevice.edit() skeleton stub — returns preset.model_dump() | `test_hx_device.py` | ✅ COVERED |
| D-09 | AnalogDevice does NOT implement EditorProtocol | `test_analog_device.py` | ✅ COVERED |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* pytest 9.0.3 was already installed; no additional test framework setup was needed for Phase 27.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

The only exception is the interactive `rig edit` happy path (live terminal prompt), but this is covered by unit tests via `ConfirmationIO` mock injection. No human-only verification required.

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: all 4 tasks have automated verify (no gap)
- [x] Wave 0: not needed — existing infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 1s (full suite: 0.51s, quick: 0.18s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-17

---

## Validation Audit 2026-06-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Tests run | 94 (phase-specific) / 359 (full suite) |
| Result | NYQUIST-COMPLIANT |
