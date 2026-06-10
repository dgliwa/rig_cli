---
phase: 17
slug: fix-stale-mood-mkii-catalog-tests
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-10
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog -v` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog -v`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** < 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | CBA-03 | All 3 Mood MkII tests pass | unit | `pytest packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog -v` | ✅ | ✅ green |
| 17-01-02 | 01 | 1 | CBA-03 | Full suite green | integration | `pytest -q` | ✅ | ✅ green |

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
