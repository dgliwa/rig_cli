---
phase: 16
slug: reset-to-defaults
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-10
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest packages/rig-chasebliss/tests/test_applier.py -q` |
| **Full suite command** | `uv run pytest packages/rig-chasebliss/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/rig-chasebliss/tests/test_applier.py -q`
- **After every plan wave:** Run `uv run pytest packages/rig-chasebliss/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** < 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CBA-06 | Reset sent before preset CC params | unit | `pytest test_applier.py -k "reset" -q` | ✅ | ✅ green |
| 16-01-02 | 01 | 1 | CBA-06 | Reset excludes `default=None` | unit | `pytest test_applier.py -k "exclude" -q` | ✅ | ✅ green |
| 16-01-03 | 01 | 1 | CBA-06 | Dry-run skips MIDI | unit | `pytest test_applier.py -k "dry" -q` | ✅ | ✅ green |
| 16-01-04 | 01 | 1 | CBA-06 | Failure non-blocking | unit | `pytest test_applier.py -k "failure" -q` | ✅ | ✅ green |
| 16-01-05 | 01 | 1 | CBA-06 | Empty controls handled | unit | `pytest test_applier.py -k "empty" -q` | ✅ | ✅ green |

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
