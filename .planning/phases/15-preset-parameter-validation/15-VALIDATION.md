---
phase: 15
slug: preset-parameter-validation
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-10
---

# Phase 15 — Validation Strategy

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
| 15-01-01 | 01 | 1 | CBA-05 | Unknown param name → error | unit | `pytest test_device.py -k "unknown" -q` | ✅ | ✅ green |
| 15-01-02 | 01 | 1 | CBA-05 | Out-of-range value → error | unit | `pytest test_device.py -k "out_of_range" -q` | ✅ | ✅ green |
| 15-01-03 | 01 | 1 | CBA-05 | Toggle position validation | unit | `pytest test_device.py -k "toggle" -q` | ✅ | ✅ green |
| 15-01-04 | 01 | 1 | CBA-05 | Empty params valid | unit | `pytest test_device.py -k "empty" -q` | ✅ | ✅ green |
| 15-01-05 | 01 | 1 | CBA-05 | Multiple errors grouped | unit | `pytest test_device.py -k "multiple" -q` | ✅ | ✅ green |

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
