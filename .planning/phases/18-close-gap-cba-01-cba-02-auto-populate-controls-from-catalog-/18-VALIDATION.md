---
phase: 18
slug: close-gap-cba-01-cba-02-auto-populate-controls-from-catalog-
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-10
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest packages/rig-chasebliss/tests/test_device.py -q` |
| **Full suite command** | `uv run pytest packages/rig-chasebliss/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/rig-chasebliss/tests/test_device.py -q`
- **After every plan wave:** Run `uv run pytest packages/rig-chasebliss/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** < 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | CBA-01, CBA-02 | Known model populates | unit | `pytest test_device.py -k "known_model" -q` | ✅ | ✅ green |
| 18-01-02 | 01 | 1 | CBA-01, CBA-02 | Unknown model empty | unit | `pytest test_device.py -k "unknown_model" -q` | ✅ | ✅ green |
| 18-01-03 | 01 | 1 | CBA-01, CBA-02 | Explicit controls not overwritten | unit | `pytest test_device.py -k "explicit_controls" -q` | ✅ | ✅ green |
| 18-01-04 | 01 | 1 | CBA-01, CBA-02 | No model backward compat | unit | `pytest test_device.py -k "no_model" -q` | ✅ | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-10
