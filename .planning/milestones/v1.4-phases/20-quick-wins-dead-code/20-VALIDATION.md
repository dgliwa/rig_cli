---
phase: 20
slug: quick-wins-dead-code
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for quick-wins-dead-code.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | `pyproject.toml` (`testpaths = ["packages"]`) |
| **Quick run command** | `uv run pytest packages/ -q` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/ -q`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-TYPE-04 | 01 | 1 | TYPE-04 | — | N/A | unit | `uv run pytest packages/rig/tests/test_plugin.py packages/rig/tests/test_devices.py -q` | ✅ | ✅ green |
| 20-01-TEST-01 | 01 | 1 | TEST-01 | — | N/A | integration | `make test` | ✅ | ✅ green |
| 20-01-QUAL-01 | 01 | 1 | QUAL-01 | — | N/A | unit | `uv run pytest packages/rig/tests/test_plan.py packages/rig/tests/test_cli_plan.py -q` | ✅ | ✅ green |
| 20-01-QUAL-02 | 01 | 1 | QUAL-02 | — | N/A | manual | — | — | 📋 manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · 📋 manual*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `Enums-vs-Literals` TODO comment replaced with inline explanation | QUAL-02 | Pure documentation change; no assertion can be written for comment content | `grep -n "StrEnum\|Literals" packages/rig/src/rig/engine/plugin.py` — confirm no TODO remains |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are declared manual-only
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0: existing infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-16
