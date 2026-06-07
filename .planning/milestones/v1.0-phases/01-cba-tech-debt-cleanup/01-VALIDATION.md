---
phase: 01
slug: cba-tech-debt-cleanup
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract. Phase 1 is a behavior-neutral refactor — no new CLI commands, no new data flow. All observable truths are programmatically verifiable.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_base_helpers.py tests/test_appliers.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~0.5 seconds |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_base_helpers.py tests/test_appliers.py -q`
- **After every plan wave:** `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | CBA-01 | — | N/A (refactor) | unit | `uv run pytest tests/test_base_helpers.py::test_mark_preset_saved_sets_preset_id_to_true_in_new_device tests/test_base_helpers.py::test_mark_preset_saved_preserves_existing_entries_when_adding_new_preset tests/test_base_helpers.py::test_mark_preset_saved_does_not_mutate_other_device_state_fields tests/test_base_helpers.py::test_mark_preset_saved_is_the_only_caller_of_update_device_state_for_presets_saved -v` | ✅ | ✅ green |
| 01-01-T2 | 01 | 1 | CBA-02 | — | N/A (refactor) | unit | `uv run pytest tests/test_appliers.py::ChaseBlissApplierTests::test_detect_cba_setup_fresh_device_produces_all_phases -v` | ✅ | ✅ green |
| 01-01-T3 | 01 | 1 | CBA-03 | — | N/A (refactor) | structural | `uv run pytest tests/test_base_helpers.py::test_no_private_symbol_cross_module_reference_in_engine -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 setup needed — pytest was already installed and configured.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no consecutive tasks without automated verify
- [x] Wave 0 not required (existing infrastructure sufficient)
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-06
